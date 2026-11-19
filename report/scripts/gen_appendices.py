"""Generate appendices that reproduce code or data verbatim (report venv).

    report/.venv/Scripts/python.exe report/scripts/gen_appendices.py

Writes report/md/AC_prompts.md, AD_sample_outputs.md, AE_reliability_policy.md,
AF_project_record.md. Prompts are extracted from the source with `ast`, the
policy is imported from its module, samples come from stored runs, and the
project record from git.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import subprocess
import textwrap
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MD = ROOT / "report" / "md"


def wrap_block(text: str, width: int = 92) -> str:
    out = []
    for line in text.strip("\n").splitlines():
        out.extend(textwrap.wrap(line, width) or [""])
    return "\n".join(out)


# --------------------------------------------------------------- prompts
def module_constant(path: Path, name: str) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)


def system_prompts_in(path: Path, function: str) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function:
            for sub in ast.walk(node):
                if isinstance(sub, ast.Dict):
                    keys = [getattr(k, "value", None) for k in sub.keys]
                    if "role" in keys and "content" in keys:
                        role = sub.values[keys.index("role")]
                        content = sub.values[keys.index("content")]
                        if getattr(role, "value", None) == "system":
                            if isinstance(content, ast.Constant):
                                found.append(content.value)
                            elif isinstance(content, ast.BoolOp):  # system_prompt or (...)
                                for value in content.values:
                                    if isinstance(value, ast.Constant):
                                        found.append(value.value)
    return found


def prompts():
    llm = ROOT / "backend/app/services/llm_service.py"
    items = [
        ("Gateway classifier", "gateway/prompts.py · CLASSIFICATION_SYSTEM_PROMPT",
         module_constant(ROOT / "gateway/prompts.py", "CLASSIFICATION_SYSTEM_PROMPT")),
        ("Arithmetic step generation (default system prompt)", "llm_service.py · _generate",
         system_prompts_in(llm, "_generate")[0]),
        ("Next-step continuation sampling", "llm_service.py · generate_step_continuations",
         system_prompts_in(llm, "generate_step_continuations")[0]),
        ("Step verifier", "llm_service.py · verify_step", system_prompts_in(llm, "verify_step")[0]),
        ("Factual answer generation", "factual/prompts.py · FACTUAL_REASONING_PROMPT",
         module_constant(ROOT / "factual/prompts.py", "FACTUAL_REASONING_PROMPT")),
        ("Factual web search", "llm_service.py · search_web", system_prompts_in(llm, "search_web")[0]),
        ("Factual claim assessment", "llm_service.py · assess_factual_claim",
         system_prompts_in(llm, "assess_factual_claim")[0]),
        ("Logical reasoning generation", "logical/prompts.py · LOGICAL_REASONING_SYSTEM_PROMPT",
         module_constant(ROOT / "logical/prompts.py", "LOGICAL_REASONING_SYSTEM_PROMPT")),
    ]
    lines = ["# Prompts", "",
             "This appendix reproduces, verbatim, the system prompts sent to the language model. They were extracted "
             "from the source files by `report/scripts/gen_appendices.py`, so they match the code exactly. The user "
             "message of each call is a JSON object containing the question and, where relevant, the preceding steps, "
             "the proposed step, the candidate continuations or the evidence items (Chapters 6–9).", ""]
    for title, where, text in items:
        lines += [f"## {title}", "", f"Source: `{where}`.", "", "```", wrap_block(text), "```", ""]
    (MD / "AC_prompts.md").write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------- sample outputs
def trim(obj, depth=0):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in ("text",) and isinstance(v, str) and len(v) > 100:
                v = v[:97] + "..."
            out[k] = trim(v, depth + 1)
        return out
    if isinstance(obj, list):
        if len(obj) > 2:
            return [trim(x, depth + 1) for x in obj[:2]] + [f"... {len(obj) - 2} more"]
        return [trim(x, depth + 1) for x in obj]
    if isinstance(obj, float):
        return round(obj, 4)
    if isinstance(obj, str) and len(obj) > 140:
        return obj[:137] + "..."
    return obj


def sample_outputs():
    runs = json.loads((ROOT / "backend/data/calibration_runs.json").read_text(encoding="utf-8"))
    picks = [(20, "Arithmetic"), (15, "Factual"), (28, "Logical")]
    lines = ["# Sample Run Outputs", "",
             "This appendix shows the complete pipeline response for one stored run of each pipeline, as returned by "
             "`POST /api/ask` and stored under `pipeline_output` in `backend/data/calibration_runs.json`. To fit the "
             "page, numbers are rounded to four decimals, long strings are shortened (marked “...”), and lists with "
             "more than two items show the first two. Run numbers count from 1 in the order stored.", ""]
    for index, label in picks:
        run = runs[index]
        body = json.dumps(trim(run["pipeline_output"]), indent=1, ensure_ascii=False)
        lines += [f"## {label} run", "",
                  f"Run {index + 1}, stored {run['created_at'][:19].replace('T', ' ')} UTC, answer confidence "
                  f"{run['confidence']:.3f}.", "", "```json", body, "```", ""]
    (MD / "AD_sample_outputs.md").write_text("\n".join(lines), encoding="utf-8")


# ------------------------------------------------------- reliability policy
def policy():
    spec = importlib.util.spec_from_file_location("sr", ROOT / "factual/retrieval/source_reliability.py")
    sr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sr)
    weights = sr.SOURCE_RELIABILITY_WEIGHTS
    band = lambda w: "KEEP" if w >= 0.75 else "DOWN_WEIGHT" if w >= 0.45 else "REJECT"
    lines = ["# Source-Reliability Policy", "",
             "This appendix lists the complete source-reliability policy of the factual pipeline, generated from "
             "`factual/retrieval/source_reliability.py`. A host matches a listed domain if it equals the domain or ends "
             "with “.” followed by the domain; the longest matching domain wins. Hosts that match no listed domain are "
             "classified by the suffix rules in Chapter 8, then by the source type supplied upstream, and otherwise "
             "receive the *general* weight. @tab:policy-weights gives the weight, band and number of named domains of every tier, "
             "and @tab:policy-aliases the source-type labels accepted from other components.", "",
             "Table: Tier weights and bands. {#tab:policy-weights}", "",
             "| Tier | Weight | Band | Named domains |", "|---|---|---|---|"]
    for tier, w in sorted(weights.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {tier.replace('_', ' ')} | {w:.2f} | {band(w)} | {len(sr.DOMAIN_TIERS.get(tier, ()))} |")
    lines += ["", "Table: Source-type aliases accepted from upstream components. {#tab:policy-aliases}", "",
              "| Alias | Tier |", "|---|---|"]
    for alias, tier in sr.SOURCE_TYPE_ALIASES.items():
        lines.append(f"| `{alias}` | {tier.replace('_', ' ')} |")
    lines += ["", "## Named Domains by Tier", ""]
    for tier, w in sorted(weights.items(), key=lambda kv: -kv[1]):
        domains = sr.DOMAIN_TIERS.get(tier)
        if not domains:
            continue
        lines += [f"**{tier.replace('_', ' ').capitalize()} ({w:.2f}, {band(w)}).** "
                  + ", ".join(f"`{d}`" for d in domains) + ".", ""]
    lines += ["## Suffix Rules", "",
              f"- Government top-level domains: {', '.join('`.' + t + '`' for t in sorted(sr._GOV_TLDS))}; government "
              f"second-level labels under a two-letter country code: {', '.join('`' + t + '`' for t in sorted(sr._GOV_SECOND_LEVEL))}.",
              f"- Intergovernmental top-level domain: {', '.join('`.' + t + '`' for t in sorted(sr._INTERGOV_TLDS))}.",
              f"- Academic top-level domain: {', '.join('`.' + t + '`' for t in sorted(sr._ACADEMIC_TLDS))}; academic second-level "
              f"labels under a country code: {', '.join('`' + t + '`' for t in sorted(sr._ACADEMIC_SECOND_LEVEL))}.",
              "- Blog: host beginning with `blog.` or `blog-`.",
              f"- Low-trust top-level domains: {', '.join('`.' + t + '`' for t in sorted(sr._LOW_TRUST_TLDS))}.",
              f"- General organisation: other {', '.join('`.' + t + '`' for t in sorted(sr._ORG_TLDS))} hosts.", ""]
    (MD / "AE_reliability_policy.md").write_text("\n".join(lines), encoding="utf-8")


# ------------------------------------------------------------ project record
def project_record():
    log = subprocess.run(["git", "log", "--format=%h|%ad|%s", "--date=short"], cwd=ROOT, capture_output=True, text=True).stdout
    commits = [line.split("|", 2) for line in log.strip().splitlines()][::-1]
    status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout
    modified = sum(1 for l in status.splitlines() if l.startswith(" M") or l.startswith("M"))
    untracked = sum(1 for l in status.splitlines() if l.startswith("??"))
    files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    groups = {
        "Python (pipelines, backend, gateway)": lambda p: p.endswith(".py") and not p.startswith("tests/"),
        "Python (tests)": lambda p: p.endswith(".py") and p.startswith("tests/"),
        "JavaScript / JSX (frontend)": lambda p: p.startswith("frontend/src/") and p.endswith((".js", ".jsx")),
        "CSS (frontend)": lambda p: p.startswith("frontend/src/") and p.endswith(".css"),
        "Markdown documentation": lambda p: p.endswith(".md") and not p.startswith("report/"),
    }
    rows = []
    tracked_and_new = set(files) | {l[3:] for l in status.splitlines() if l.startswith("??")}
    for name, test in groups.items():
        paths = [p for p in tracked_and_new if test(p) and (ROOT / p).is_file()]
        line_count = sum(len((ROOT / p).read_text(encoding="utf-8", errors="ignore").splitlines()) for p in paths)
        rows.append((name, len(paths), line_count))
    lines = ["# Project Record", "",
             "## Timeline", "",
             "The proposal document (FYP-1) is dated 18 August 2026. @tab:commits lists the commits in the project "
             "repository; changes made after the last commit (the dashboard, the run-history endpoint, the revised "
             "source-reliability policy, the rule-parser fix and its tests, and this report) are in the working tree at "
             f"the time of writing ({modified} modified and {untracked} new paths).", "",
             "Table: Commit history. {#tab:commits}", "", "| Commit | Date | Message |", "|---|---|---|"]
    for h, d, s in commits:
        lines.append(f"| `{h}` | {d} | {s} |")
    lines += ["", "## Milestones", "",
              "- Problem definition, literature review and proposal (August 2026).",
              "- Base project with the arithmetic pipeline (27 September 2026).",
              "- Factual pipeline and gateway (3 October 2026).",
              "- Logical pipeline with the Z3 solver (4 October 2026).",
              "- Pilot experiments on GSM8K, TriviaQA and RuleTaker (19 November 2026).",
              "- Dashboard, revised reliability policy, rule-parser fix, analysis and report (19 November 2026).", "",
              "## Repository Statistics", "",
              "Counted over files tracked by Git plus new files not yet committed, excluding the report itself and "
              "third-party dependencies; @tab:repo-stats gives the counts.", "",
              "Table: Repository size by kind of file. {#tab:repo-stats}", "",
              "| Kind | Files | Lines |", "|---|---|---|"]
    for name, n, lc in rows:
        lines.append(f"| {name} | {n} | {lc:,} |")
    lines += ["", "## Deliverables", "",
              "- Source code: frontend, backend, gateway, three pipelines, tests.",
              "- Pilot result files for the three benchmarks and the run store.",
              "- This report, its Markdown sources, figures, metric scripts and computed results under `report/`.", ""]
    (MD / "AF_project_record.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    prompts()
    sample_outputs()
    policy()
    project_record()
    print("appendices written")
