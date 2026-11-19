"""Compute every number used in the report from files in the repository.

Run with the PROJECT venv (it imports the pipelines for the offline logical
re-check and reuses the project's own calibration metrics):

    PYTHONPATH=".;backend" venv/Scripts/python.exe report/scripts/compute_metrics.py

Outputs:
    report/results/metrics.json      all metrics, nested by pipeline
    report/results/*.csv             question- and step-level tables
No LLM or network calls are made.
"""
from __future__ import annotations

import csv
import json
import math
import re
import statistics
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]

from arithmetic.evaluation.metrics import (  # noqa: E402
    binary_auroc,
    binary_nll,
    brier_score,
    expected_calibration_error,
    maximum_calibration_error,
    reliability_bins,
)
from factual.retrieval.source_reliability import classify_source  # noqa: E402
from logical.decomposition.decomposer import build_reasoning_steps  # noqa: E402
from logical.premises.extractor import extract_premises, extract_target_statement  # noqa: E402
from logical.rules.extractor import extract_rules, parse_atom  # noqa: E402
from logical.rules.rule_engine import run_rule_engine  # noqa: E402
from logical.verification.logical_verifier import verify_claim  # noqa: E402

OUT = ROOT / "report" / "results"
OUT.mkdir(parents=True, exist_ok=True)

FILES = {
    "logical": ROOT / "logical/experiments/results/logical_pilot.json",
    "factual": ROOT / "factual/experiments/results/factual_test.json",
    "arithmetic": ROOT / "arithmetic/experiments/results/gsm8k_pilot_5.json",
    "runs": ROOT / "backend/data/calibration_runs.json",
}


# ---------------------------------------------------------------- helpers
def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def mean(values):
    values = [v for v in values if v is not None]
    return statistics.fmean(values) if values else None


def describe(values):
    values = [float(v) for v in values if v is not None]
    if not values:
        return {"n": 0}
    ordered = sorted(values)
    return {
        "n": len(values),
        "mean": statistics.fmean(values),
        "std": statistics.pstdev(values) if len(values) > 1 else 0.0,
        "min": ordered[0],
        "median": statistics.median(ordered),
        "max": ordered[-1],
    }


def point_biserial(values, labels):
    """Pearson correlation between a score and a 0/1 label."""
    pairs = [(float(v), int(y)) for v, y in zip(values, labels) if v is not None]
    if len(pairs) < 3 or len({y for _, y in pairs}) < 2:
        return None
    xs, ys = zip(*pairs)
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in pairs) / (sx * sy)


def pearson(xs, ys):
    pairs = [(a, b) for a, b in zip(xs, ys) if a is not None and b is not None]
    if len(pairs) < 3:
        return None
    a, b = zip(*pairs)
    ma, mb = statistics.fmean(a), statistics.fmean(b)
    sa = math.sqrt(sum((x - ma) ** 2 for x in a))
    sb = math.sqrt(sum((y - mb) ** 2 for y in b))
    if sa == 0 or sb == 0:
        return None
    return sum((x - ma) * (y - mb) for x, y in pairs) / (sa * sb)


def calibration(probabilities, labels):
    """Answer-level calibration metrics; None where a metric is undefined."""
    pairs = [(p, y) for p, y in zip(probabilities, labels) if p is not None]
    if not pairs:
        return {"n": 0}
    ps, ys = [p for p, _ in pairs], [int(y) for _, y in pairs]
    out = {
        "n": len(ps),
        "positives": sum(ys),
        "negatives": len(ys) - sum(ys),
        "accuracy": sum(ys) / len(ys),
        "mean_confidence": statistics.fmean(ps),
        "mean_conf_correct": mean([p for p, y in zip(ps, ys) if y == 1]),
        "mean_conf_wrong": mean([p for p, y in zip(ps, ys) if y == 0]),
        "ece_10bin": expected_calibration_error(ps, ys, 10),
        "mce_10bin": maximum_calibration_error(ps, ys, 10),
        "brier": statistics.fmean(brier_score(p, y) for p, y in zip(ps, ys)),
        "nll": statistics.fmean(binary_nll(p, y) for p, y in zip(ps, ys)),
        "reliability_bins": reliability_bins(ps, ys),
    }
    out["auroc"] = binary_auroc(ps, ys) if 0 < sum(ys) < len(ys) else None
    if out["auroc"] is None:
        out["auroc_note"] = "undefined: only one correctness class present"
    return out


def write_csv(name, rows):
    if not rows:
        return
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with open(OUT / name, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def norm_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\b(a|an|the)\b", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


# ---------------------------------------------------------------- logical
def logical_metrics():
    data = load(FILES["logical"])
    results = data["results"]
    q_rows, step_rows = [], []
    labels, confs, before, after = [], [], [], []
    confusion_before = Counter()
    confusion_after = Counter()
    proof_lengths_before, proof_lengths_after = [], []
    signals = {"self_verification": [], "consistency": [], "logical_validity": [], "semantic_entropy": []}
    remaining_misses = []
    inconsistent = 0

    for item in results:
        response = item["inference_response"]
        gold = item["reference_label"]
        correct = bool(item["is_correct"])
        conf = response.get("answer_confidence")
        labels.append(int(correct))
        confs.append(conf)
        before.append(correct)
        confusion_before[(gold, item["predicted_verdict"])] += 1
        proof_lengths_before.append(len(response["steps"]))
        inconsistent += bool(response.get("inconsistency_detected"))

        essential = [c for s in response["steps"] for c in s["claims"] if c.get("essential")]
        claim = essential[-1] if essential else None
        for step in response["steps"]:
            for c in step["claims"]:
                step_rows.append({
                    "pipeline": "logical",
                    "question_id": item["question_id"],
                    "step_id": step["step_id"],
                    "position": step["step_id"],
                    "verdict": c["verification"]["verdict"],
                    "self_verification": c.get("self_verification_score"),
                    "consistency": c.get("consistency_score"),
                    "domain_evidence": c["verification"].get("logical_validity_score"),
                    "semantic_entropy": step.get("semantic_entropy"),
                    "calibrated": c.get("calibrated_probability"),
                    "answer_correct": int(correct),
                })
        if claim:
            signals["self_verification"].append(claim.get("self_verification_score"))
            signals["consistency"].append(claim.get("consistency_score"))
            signals["logical_validity"].append(claim["verification"].get("logical_validity_score"))
        signals["semantic_entropy"].append(response["steps"][0].get("semantic_entropy") if response["steps"] else None)

        # Offline re-check with the current (fixed) rule parser; solver needs no LLM.
        question = item["model_input"]
        premises = extract_premises(question)
        rules = extract_rules(premises)
        engine = run_rule_engine(premises, rules)
        target_text = extract_target_statement(question)
        target = parse_atom(target_text) if target_text else None
        verification = verify_claim(target, engine) if target else None
        verdict = verification["verdict"] if verification else "UNKNOWN"
        steps = build_reasoning_steps(engine, target, verification, rules)
        predicted = "entailment" if verdict == "ENTAILED" else "not entailment"
        ok_after = predicted == gold
        after.append(ok_after)
        confusion_after[(gold, verdict)] += 1
        proof_lengths_after.append(len(steps))
        if not ok_after:
            remaining_misses.append({
                "question_id": item["question_id"],
                "question": item["question"],
                "gold": gold,
                "verdict_after_fix": verdict,
                "negated_query": item["question"].lower().startswith("is ") and " not " in item["question"].lower(),
            })
        q_rows.append({
            "question_id": item["question_id"],
            "question": item["question"],
            "gold": gold,
            "verdict_pilot": item["predicted_verdict"],
            "correct_pilot": int(correct),
            "verdict_after_fix": verdict,
            "correct_after_fix": int(ok_after),
            "answer_confidence": conf,
            "steps_pilot": len(response["steps"]),
            "steps_after_fix": len(steps),
            "rules_extracted_after_fix": len(rules),
            "self_verification": claim.get("self_verification_score") if claim else None,
            "consistency": claim.get("consistency_score") if claim else None,
            "logical_validity": claim["verification"].get("logical_validity_score") if claim else None,
        })

    write_csv("logical_questions.csv", q_rows)
    gold_labels = ["entailment", "not entailment"]
    verdicts = ["ENTAILED", "CONTRADICTED", "UNKNOWN"]
    to_matrix = lambda c: {g: {v: c.get((g, v), 0) for v in verdicts} for g in gold_labels}
    by_verdict_conf = {
        v: describe([row["answer_confidence"] for row in q_rows if row["verdict_pilot"] == v]) for v in verdicts
    }
    return {
        "dataset": data["dataset"],
        "split": data["split"],
        "selection": data["selection"],
        "questions_selected": data["questions_selected"],
        "questions_completed": len(results),
        "consistency_samples_per_step": data.get("consistency_samples_per_step"),
        "accuracy_pilot": {"correct": sum(before), "n": len(before), "rate": sum(before) / len(before)},
        "accuracy_after_parser_fix_offline": {"correct": sum(after), "n": len(after), "rate": sum(after) / len(after)},
        "confusion_pilot": to_matrix(confusion_before),
        "confusion_after_fix": to_matrix(confusion_after),
        "calibration_pilot": calibration(confs, labels),
        "confidence_by_pilot_verdict": by_verdict_conf,
        "calibration_within_unknown_answers": calibration(
            [row["answer_confidence"] for row in q_rows if row["verdict_pilot"] == "UNKNOWN"],
            [row["correct_pilot"] for row in q_rows if row["verdict_pilot"] == "UNKNOWN"],
        ),
        "correct_by_pilot_verdict": {
            v: {"correct": sum(r["correct_pilot"] for r in q_rows if r["verdict_pilot"] == v),
                "n": sum(1 for r in q_rows if r["verdict_pilot"] == v)} for v in verdicts
        },
        "signals_essential_claim": {k: describe(v) for k, v in signals.items()},
        "signal_correlation_with_correctness": {
            k: point_biserial(v, labels) for k, v in signals.items() if k != "semantic_entropy"
        },
        "proof_length_pilot": dict(Counter(proof_lengths_before)),
        "proof_length_after_fix": dict(Counter(proof_lengths_after)),
        "inconsistency_detections": inconsistent,
        "remaining_misses_after_fix": remaining_misses,
        "remaining_misses_negated_query": sum(m["negated_query"] for m in remaining_misses),
        "remaining_misses_note": "All misses after the fix require the closed-world assumption: negated queries are unprovable under open-world semantics, and the two positive queries depend on rules with negated conditions (e.g. \"If something is not young then it is green\"). Verified manually.",
    }, step_rows


# ---------------------------------------------------------------- factual
def factual_metrics():
    data = load(FILES["factual"])
    results = data["results"]
    q_rows, step_rows, source_rows = [], [], []
    labels, confs = [], []
    verdicts, statuses_recorded, statuses_policy, tiers = Counter(), Counter(), Counter(), Counter()
    origins, domains, conf_status = Counter(), Counter(), Counter()
    reliability_recorded, reliability_policy = [], []
    claims_per_answer, steps_per_answer, sources_per_claim = [], [], []
    sig = {"self_verification": [], "consistency": [], "evidence": [], "calibrated": []}
    sig_labels = []

    for item in results:
        response = item["pipeline_response"]
        aliases = [norm_text(a) for a in item.get("reference_aliases") or [item["reference_answer"]]]
        reasoning = norm_text(item.get("generated_reasoning") or "")
        correct = any(alias and re.search(rf"\b{re.escape(alias)}\b", reasoning) for alias in aliases)
        conf = response.get("answer_confidence")
        labels.append(int(correct))
        confs.append(conf)
        conf_status[response.get("answer_confidence_status")] += 1
        claims = [c for s in response["steps"] for c in s["claims"]]
        claims_per_answer.append(len(claims))
        steps_per_answer.append(len(response["steps"]))
        for step in response["steps"]:
            for c in step["claims"]:
                verdict = c["verification"]["verdict"]
                verdicts[verdict] += 1
                sources = c.get("sources") or []
                sources_per_claim.append(len(sources))
                for key, field in (("self_verification", "self_verification_score"), ("consistency", "consistency_score"), ("calibrated", "calibrated_probability")):
                    sig[key].append(c.get(field))
                sig["evidence"].append(c["verification"].get("evidence_score"))
                sig_labels.append(int(correct))
                step_rows.append({
                    "pipeline": "factual",
                    "question_id": item["question_id"],
                    "step_id": step["step_id"],
                    "position": step["step_id"],
                    "verdict": verdict,
                    "self_verification": c.get("self_verification_score"),
                    "consistency": c.get("consistency_score"),
                    "domain_evidence": c["verification"].get("evidence_score"),
                    "calibrated": c.get("calibrated_probability"),
                    "essential": int(bool(c.get("essential"))),
                    "sources": len(sources),
                    "answer_correct": int(correct),
                })
                for src in sources:
                    statuses_recorded[src.get("status")] += 1
                    origins[src.get("text_origin")] += 1
                    domains[src.get("domain")] += 1
                    reliability_recorded.append(src.get("reliability_score"))
                    tier, score = classify_source({"domain": src.get("domain"), "source_type": "general"})
                    tiers[tier] += 1
                    reliability_policy.append(score)
                    statuses_policy["KEEP" if score >= 0.75 else "DOWN_WEIGHT" if score >= 0.45 else "REJECT"] += 1
                    source_rows.append({
                        "question_id": item["question_id"],
                        "domain": src.get("domain"),
                        "recorded_reliability": src.get("reliability_score"),
                        "recorded_status": src.get("status"),
                        "current_policy_tier": tier,
                        "current_policy_score": score,
                        "text_origin": src.get("text_origin"),
                    })
        q_rows.append({
            "question_id": item["question_id"],
            "question": item["question"],
            "reference_answer": item["reference_answer"],
            "alias_in_reasoning": int(correct),
            "answer_confidence": conf,
            "answer_confidence_status": response.get("answer_confidence_status"),
            "steps": len(response["steps"]),
            "claims": len(claims),
            "predicted_error_step": response.get("predicted_error_step"),
        })

    write_csv("factual_questions.csv", q_rows)
    write_csv("factual_sources.csv", source_rows)
    instruction = re.compile(r"^(identify|recall|determine|find|verify|check|confirm|look up|research|consider|search)\b", re.I)
    inst_claims = [c for item in results for s in item["pipeline_response"]["steps"] for c in s["claims"]
                   if instruction.match(c["text"].strip())]
    inst_questions = sum(
        any(instruction.match(c["text"].strip()) for s in item["pipeline_response"]["steps"] for c in s["claims"])
        for item in results
    )
    return {
        "instruction_like_claims": {
            "pattern": instruction.pattern,
            "claims": len(inst_claims),
            "of_claims": sum(claims_per_answer),
            "questions_with_any": inst_questions,
            "verdicts": dict(Counter(c["verification"]["verdict"] for c in inst_claims)),
        },
        "dataset": data["dataset"],
        "config": data["config"],
        "split": data["split"],
        "selection": data["selection"],
        "questions_selected": data["questions_selected"],
        "questions_completed": len(results),
        "correctness_label": "lenient proxy: a normalised TriviaQA alias occurs in the generated reasoning text (the run did not store a separate final answer)",
        "calibration": calibration(confs, labels),
        "answer_confidence_status": dict(conf_status),
        "steps_per_answer": describe(steps_per_answer),
        "claims_per_answer": describe(claims_per_answer),
        "claims_total": sum(claims_per_answer),
        "sources_per_claim": describe(sources_per_claim),
        "claim_verdicts": dict(verdicts),
        "source_status_recorded": dict(statuses_recorded),
        "source_status_under_current_policy": dict(statuses_policy),
        "source_tiers_under_current_policy": dict(tiers.most_common()),
        "reliability_recorded": describe(reliability_recorded),
        "reliability_current_policy": describe(reliability_policy),
        "text_origin": dict(origins),
        "unique_domains": len(domains),
        "top_domains": domains.most_common(15),
        "signals_claim_level": {k: describe(v) for k, v in sig.items()},
        "signal_correlation_with_answer_correctness": {k: point_biserial(v, sig_labels) for k, v in sig.items()},
    }, step_rows


# ---------------------------------------------------------------- arithmetic
def last_number(text):
    numbers = re.findall(r"-?\d[\d,]*(?:\.\d+)?", text or "")
    return float(numbers[-1].replace(",", "")) if numbers else None


def arithmetic_metrics():
    data = load(FILES["arithmetic"])
    results = data["results"]
    q_rows, step_rows = [], []
    labels, confs = [], []
    types, methods = Counter(), Counter()
    sig = {k: [] for k in ("verification", "consistency", "sample_agreement", "semantic_entropy", "token_prob", "token_entropy", "fused")}
    flagged_relative = []
    for item in results:
        gold = last_number(item["reference_answer"].split("####")[-1])
        pred = last_number(item["final_answer"])
        correct = gold is not None and pred is not None and abs(gold - pred) < 1e-6
        labels.append(int(correct))
        confs.append(item.get("final_answer_confidence"))
        steps = item["reasoning_steps"]
        if item.get("predicted_error_step") and steps:
            flagged_relative.append(item["predicted_error_step"] / len(steps))
        for step in steps:
            types[step["step_type"]] += 1
            methods[step.get("consistency_method")] += 1
            lp = step.get("mean_token_logprob")
            values = {
                "verification": step.get("verification_score"),
                "consistency": step.get("consistency_score"),
                "sample_agreement": step.get("sample_agreement_score"),
                "semantic_entropy": step.get("semantic_entropy"),
                "token_prob": math.exp(lp) if lp is not None else None,
                "token_entropy": step.get("token_entropy"),
                "fused": step.get("fused_confidence"),
            }
            for k, v in values.items():
                sig[k].append(v)
            step_rows.append({
                "pipeline": "arithmetic",
                "question_id": item["question_id"],
                "step_id": step["step_number"],
                "position": step["step_number"],
                "step_type": step["step_type"],
                "self_verification": values["verification"],
                "consistency": values["consistency"],
                "domain_evidence": values["token_prob"],
                "semantic_entropy": values["semantic_entropy"],
                "token_entropy": values["token_entropy"],
                "calibrated": values["fused"],
                "answer_correct": int(correct),
            })
        q_rows.append({
            "question_id": item["question_id"],
            "gold_answer": gold,
            "predicted_answer": pred,
            "correct": int(correct),
            "final_answer_confidence": item.get("final_answer_confidence"),
            "steps": len(steps),
            "predicted_error_step": item.get("predicted_error_step"),
            "confidence_method": item.get("confidence_method"),
        })
    write_csv("arithmetic_questions.csv", q_rows)
    by_type = {
        t: describe([r["calibrated"] for r in step_rows if r["step_type"] == t]) for t in types
    }
    return {
        "dataset": data["dataset"],
        "split": data["split"],
        "questions_selected": data["questions_selected"],
        "questions_completed": len(results),
        "consistency_samples_per_step": data.get("consistency_samples_per_step"),
        "calibration": calibration(confs, labels),
        "steps_per_question": describe([r["steps"] for r in q_rows]),
        "step_types": dict(types),
        "fused_confidence_by_step_type": by_type,
        "consistency_method": dict(methods),
        "signals_step_level": {k: describe(v) for k, v in sig.items()},
        "signal_correlations_step_level": {
            f"{a}~{b}": pearson(sig[a], sig[b])
            for a, b in [("verification", "consistency"), ("consistency", "semantic_entropy"), ("token_prob", "token_entropy"), ("consistency", "sample_agreement"), ("fused", "consistency")]
        },
        "flagged_step_relative_position": describe(flagged_relative),
    }, step_rows


# ---------------------------------------------------------------- stored runs
def runs_metrics():
    runs = load(FILES["runs"])
    by_cat = Counter(r["category"] for r in runs)
    out = {
        "runs": len(runs),
        "by_category": dict(by_cat),
        "first": runs[0]["created_at"] if runs else None,
        "last": runs[-1]["created_at"] if runs else None,
        "with_pipeline_output": sum("pipeline_output" in r for r in runs),
        "calibration_status": dict(Counter(r.get("calibration_status") for r in runs)),
        "confidence_by_category": {c: describe([r.get("confidence") for r in runs if r["category"] == c]) for c in by_cat},
        "steps_by_category": {c: describe([len(r.get("steps") or []) for r in runs if r["category"] == c]) for c in by_cat},
        "verdicts": dict(Counter(s.get("verification_verdict") for r in runs for s in r.get("steps") or [] if s.get("verification_verdict"))),
    }
    rows = [{
        "run_id": r["run_id"], "created_at": r["created_at"], "category": r["category"],
        "confidence": r.get("confidence"), "steps": len(r.get("steps") or []),
        "question": r["question"][:120],
    } for r in runs]
    write_csv("stored_runs.csv", rows)
    return out


# ---------------------------------------------------------------- tests
def test_metrics():
    python = ROOT / "venv" / "Scripts" / "python.exe"
    started = time.perf_counter()
    proc = subprocess.run(
        [str(python), "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"],
        cwd=ROOT, capture_output=True, text=True,
    )
    elapsed = time.perf_counter() - started
    collect = subprocess.run(
        [str(python), "-m", "pytest", "tests", "-q", "--co", "-p", "no:cacheprovider"],
        cwd=ROOT, capture_output=True, text=True,
    )
    per_file = Counter(line.split("::")[0] for line in collect.stdout.splitlines() if "::" in line)
    summary = next((line for line in reversed(proc.stdout.splitlines()) if "passed" in line or "failed" in line), "")
    return {
        "summary": summary.strip(" ="),
        "exit_code": proc.returncode,
        "wall_seconds": elapsed,
        "per_file": dict(sorted(per_file.items())),
        "total": sum(per_file.values()),
    }


def main():
    logical, logical_steps = logical_metrics()
    factual, factual_steps = factual_metrics()
    arithmetic, arithmetic_steps = arithmetic_metrics()
    step_rows = arithmetic_steps + factual_steps + logical_steps
    write_csv("steps_all_pipelines.csv", step_rows)

    signal_keys = ["self_verification", "consistency", "domain_evidence", "calibrated"]
    correlation = {
        a: {b: pearson([r.get(a) for r in step_rows], [r.get(b) for r in step_rows]) for b in signal_keys}
        for a in signal_keys
    }
    position = {}
    for row in step_rows:
        position.setdefault(row["pipeline"], {}).setdefault(int(row["position"]), []).append(row["calibrated"])
    metrics = {
        "generated_by": "report/scripts/compute_metrics.py",
        "sources": {k: str(v.relative_to(ROOT)) for k, v in FILES.items()},
        "arithmetic": arithmetic,
        "factual": factual,
        "logical": logical,
        "stored_runs": runs_metrics(),
        "cross_pipeline": {
            "step_signal_correlation": correlation,
            "confidence_by_step_position": {
                p: {pos: describe(v) for pos, v in sorted(d.items())} for p, d in position.items()
            },
        },
        "error_localisation": {
            "measured": False,
            "reason": "No run records a ground-truth error step: GSM8K pilot answers were all correct, the error-injection utility (arithmetic/data/error_injection.py) has not been executed against the pipeline, and RuleTaker/TriviaQA provide answer-level labels only.",
        },
        "runtime_and_llm_calls": {
            "measured": False,
            "reason": "The pilot scripts do not log wall-clock time or call counts per question.",
        },
        "tests": test_metrics(),
    }
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2, default=str), encoding="utf-8")
    print("wrote", OUT / "metrics.json")


if __name__ == "__main__":
    main()
