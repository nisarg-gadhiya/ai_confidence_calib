from __future__ import annotations

from logical.rules.rule_engine import RuleEngineResult


def detect_contradictions(result: RuleEngineResult) -> list[dict]:
    explicit = [
        {"subject": subject, "predicate": predicate, "object": object_}
        for subject, predicate, object_ in result.inconsistent_atoms
    ]
    if explicit or not result.logic_solver.inconsistent:
        return explicit
    return [
        {
            "kind": "solver_unsat_core",
            "premises_used": result.logic_solver.inconsistency_provenance["premises_used"],
            "rules_used": result.logic_solver.inconsistency_provenance["rules_used"],
        }
    ]