from __future__ import annotations

from logical.rules.extractor import Atom
from logical.rules.rule_engine import RuleEngineResult


def verify_claim(claim: Atom, engine_result: RuleEngineResult) -> dict:
    solver_check = engine_result.logic_solver.check_claim(claim)
    return {
        "verdict": solver_check.verdict,
        "logical_validity_score": solver_check.logical_validity_score,
        "premises_used": solver_check.premises_used,
        "rules_used": solver_check.rules_used,
        "reasoning_operation": "solver_entailment_check",
        "solver_reason": solver_check.reason,
    }