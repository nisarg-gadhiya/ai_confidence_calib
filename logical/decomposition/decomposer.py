from __future__ import annotations

from logical.rules.extractor import Atom, Rule
from logical.rules.rule_engine import RuleEngineResult


def build_reasoning_steps(
    engine_result: RuleEngineResult,
    target: Atom | None,
    target_verification: dict | None,
    rules: list[Rule],
) -> list[dict]:
    steps: list[dict] = []
    for derivation in engine_result.derivations:
        steps.append(
            {
                "step_id": len(steps) + 1,
                "text": derivation.atom.to_text() + ".",
                "reasoning_operation": derivation.operation,
                "premises_used": sorted(derivation.premise_ids),
                "rules_used": sorted(derivation.rule_ids),
                "atom": derivation.atom,
            }
        )

    if target is not None and not any(step["atom"].key == target.key for step in steps):
        verification = target_verification or {}
        steps.append(
            {
                "step_id": len(steps) + 1,
                "text": target.to_text() + ".",
                "reasoning_operation": verification.get("reasoning_operation", "query_check"),
                "premises_used": verification.get("premises_used", []),
                "rules_used": verification.get("rules_used", []),
                "atom": target,
            }
        )

    if not steps and engine_result.inconsistent:
        for subject, predicate, object_ in engine_result.inconsistent_atoms:
            atom = Atom(subject, predicate, object_)
            steps.append(
                {
                    "step_id": len(steps) + 1,
                    "text": f"{atom.to_text()} and {atom.opposite().to_text()} are both given.",
                    "reasoning_operation": "contradiction_detection",
                    "premises_used": [],
                    "rules_used": [],
                    "atom": atom,
                }
            )
        if not steps:
            steps.append(
                {
                    "step_id": 1,
                    "text": "The supplied premises and rules are jointly inconsistent.",
                    "reasoning_operation": "solver_inconsistency_check",
                    "premises_used": engine_result.logic_solver.inconsistency_provenance["premises_used"],
                    "rules_used": engine_result.logic_solver.inconsistency_provenance["rules_used"],
                    "atom": Atom("$prop", "the premises are consistent", negated=True),
                }
            )

    known_rule_ids = {rule.rule_id for rule in rules}
    implicit_rules = sorted(
        {
            rule_id
            for derivation in engine_result.derivations
            for rule_id in derivation.rule_ids
            if rule_id not in known_rule_ids
        }
    )
    for rule_id in implicit_rules:
        relation = rule_id.removeprefix("r_transitivity_").replace("_", " ")
        rules.append(
            Rule(
                rule_id,
                f"The relation '{relation}' is transitive.",
                (),
                (),
            )
        )
    return steps