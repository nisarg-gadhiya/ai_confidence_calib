from __future__ import annotations

import re

from app.core.config import settings
from app.services.llm_service import GeneratedStep
from factual.answer_confidence import calculate_answer_confidence
from factual.calibration.calibrator import calibrate_probability
from factual.calibration.fusion import fuse_step_signals
from factual.evaluation.localization import localize_riskiest_step
from logical.decomposition.decomposer import build_reasoning_steps
from logical.generation.reasoning import generate_logical_reasoning, get_logical_llm_service
from logical.premises.extractor import extract_premises, extract_target_statement
from logical.rules.extractor import extract_rules, parse_atom
from logical.rules.rule_engine import run_rule_engine
from logical.signals.consistency import assess_consistency
from logical.signals.logical_validity import logical_validity_score
from logical.signals.self_verification import self_verify_step
from logical.verification.contradiction import detect_contradictions
from logical.verification.logical_verifier import verify_claim


def _checks_for_verification(verification: dict) -> tuple[int, int]:
    total = len(verification["premises_used"]) + len(verification["rules_used"])
    if verification["verdict"] != "ENTAILED":
        return 0, total or 1
    return total, total


def _inconsistent_result(question: str, premises: list[dict], rules: list, engine_result, target):
    target_verification = verify_claim(target, engine_result) if target else None
    steps = build_reasoning_steps(engine_result, target, target_verification, rules)
    result_steps = []
    claims = []
    for step in steps:
        atom = step["atom"]
        verification = verify_claim(atom, engine_result)
        claim = {
            "claim_id": f"c{step['step_id']}_1",
            "text": atom.to_text() + ".",
            "essential": bool(target and atom.key == target.key),
            "verification": {
                "verdict": verification["verdict"],
                "logical_validity_score": verification["logical_validity_score"],
                "premises_used": verification["premises_used"],
                "rules_used": verification["rules_used"],
                "reasoning_operation": verification["reasoning_operation"],
            },
            "self_verification_score": None,
            "consistency_score": 0.0,
            "calibrated_probability": None,
        }
        claims.append(claim)
        result_steps.append(
            {
                "step_id": step["step_id"],
                "text": step["text"],
                "reasoning_operation": step["reasoning_operation"],
                "premises_used": step["premises_used"],
                "rules_used": step["rules_used"],
                "claims": [claim],
                "consistency_method": "solver_inconsistency",
                "semantic_entropy": None,
                "sample_count": 0,
            }
        )
    return {
        "question": question,
        "final_answer": "The supplied premises are inconsistent.",
        "premises": premises,
        "rules": [rule.to_dict() for rule in rules],
        "steps": result_steps,
        "inconsistency_detected": True,
        "contradictions": detect_contradictions(engine_result),
        "unsupported_premises": engine_result.logic_solver.unsupported_premises,
        "predicted_error_step": None,
        "answer_confidence": None,
        "answer_confidence_status": "inconsistent_premises",
        "calibration_status": "not_applicable_inconsistent_premises",
    }


def process_logical(question: str, num_consistency_samples: int | None = None) -> dict:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question must be a non-empty string.")

    premises = extract_premises(question)
    rules = extract_rules(premises)
    engine_result = run_rule_engine(premises, rules)
    target_text = extract_target_statement(question)
    target = parse_atom(target_text) if target_text else None
    if engine_result.inconsistent:
        return _inconsistent_result(question, premises, rules, engine_result, target)

    generated = generate_logical_reasoning(question)
    if target_text is None and generated.final_answer:
        candidate = re.sub(r"^(?:yes|no)[,.:\s]+", "", generated.final_answer.strip(), flags=re.IGNORECASE)
        target_text = re.split(r"(?<=[.!?])\s+", candidate, maxsplit=1)[0]
        target = parse_atom(target_text)
    target_verification = verify_claim(target, engine_result) if target else None
    steps = build_reasoning_steps(engine_result, target, target_verification, rules)
    llm = get_logical_llm_service()
    if llm is None:
        raise ValueError("LLM_API_KEY is required for logical verification.")

    generated_by_number = {step.step_number: step for step in generated.steps}
    result_steps = []
    claims = []
    preceding: list[GeneratedStep] = []
    for step in steps:
        step_id = step["step_id"]
        atom = step["atom"]
        verification = verify_claim(atom, engine_result)
        checks_passed, checks_total = _checks_for_verification(verification)
        validity = logical_validity_score(checks_passed, checks_total)
        proposed = generated_by_number.get(step_id)
        proposed_atom = parse_atom(proposed.text) if proposed else None
        step_text = (
            proposed.text
            if proposed_atom is not None and proposed_atom.key == atom.key
            else step["text"]
        )
        llm_step = GeneratedStep(
            step_id,
            step_text,
            "logical_inference",
        )
        samples, assessment = self_verify_step(
            llm,
            question,
            llm_step,
            preceding,
            num_consistency_samples or settings.consistency_samples,
        )
        consistency, semantic_entropy, consistency_method = assess_consistency(
            [sample.text for sample in samples],
            assessment.sample_cluster_ids,
            fact_count=len(engine_result.facts),
            contradiction_count=max(
                len(engine_result.inconsistent_atoms),
                int(engine_result.logic_solver.inconsistent),
            ),
        )
        fused = fuse_step_signals(
            self_verification_score=assessment.p_true,
            consistency_score=consistency,
            evidence_score=validity,
        )
        calibrated = calibrate_probability(
            self_verification_score=assessment.p_true,
            consistency_score=consistency,
            evidence_score=validity,
            fused_confidence=fused,
        )
        claim = {
            "claim_id": f"c{step_id}_1",
            "text": atom.to_text() + ".",
            "essential": bool(target and atom.key == target.key),
            "verification": {
                "verdict": verification["verdict"],
                "logical_validity_score": validity,
                "premises_used": verification["premises_used"],
                "rules_used": verification["rules_used"],
                "reasoning_operation": verification["reasoning_operation"],
            },
            "self_verification_score": assessment.p_true,
            "consistency_score": consistency,
            "calibrated_probability": calibrated,
        }
        claims.append(claim)
        result_steps.append(
            {
                "step_id": step_id,
                "text": step["text"],
                "reasoning_operation": step["reasoning_operation"],
                "premises_used": step["premises_used"],
                "rules_used": step["rules_used"],
                "claims": [claim],
                "consistency_method": consistency_method,
                "semantic_entropy": semantic_entropy,
                "sample_count": len(samples),
            }
        )
        preceding.append(llm_step)

    predicted_error_step = localize_riskiest_step(
        [
            {"step_id": step["step_id"], "calibrated_probability": step["claims"][0]["calibrated_probability"]}
            for step in result_steps
            if step["claims"][0]["calibrated_probability"] is not None
        ]
    )
    answer_confidence = calculate_answer_confidence(claims)
    final_answer = None
    if target_verification:
        if target_verification["verdict"] == "ENTAILED":
            final_answer = f"Yes. {target.to_text()}."
        elif target_verification["verdict"] == "CONTRADICTED":
            final_answer = f"No. {target.to_text()} does not follow."
        else:
            final_answer = "It cannot be determined from the supplied premises."
    return {
        "question": question,
        "final_answer": final_answer,
        "premises": premises,
        "rules": [rule.to_dict() for rule in rules],
        "steps": result_steps,
        "inconsistency_detected": engine_result.inconsistent,
        "contradictions": detect_contradictions(engine_result),
        "unsupported_premises": engine_result.logic_solver.unsupported_premises,
        "predicted_error_step": predicted_error_step,
        "answer_confidence": answer_confidence,
        "answer_confidence_status": "ok" if answer_confidence is not None else "no_essential_claims",
        "calibration_status": "fixed_sigmoid_not_empirically_calibrated",
    }