from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from z3 import And, Bool, BoolSort, BoolVal, Const, DeclareSort, ForAll, Function, Implies, Not, Or, Solver, sat, unsat

from logical.rules.extractor import Atom, Rule, TRANSITIVE_RELATIONS, parse_atom
from logical.signals.logical_validity import logical_validity_score


ENTITY = DeclareSort("LogicalEntity")
RULE_SENTENCE_PATTERN = re.compile(
    r"^(?:all\b|every\b|each\b|some\b|any\b|no\b|most\b|few\b|if\b|.+?(?:->|=>|\bimplies\b))",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SolverCheck:
    verdict: str
    logical_validity_score: float
    premises_used: list[str]
    rules_used: list[str]
    reason: str | None = None


class LogicalSolver:
    def __init__(self, premises: list[dict[str, str]], rules: list[Rule]) -> None:
        self.solver = Solver()
        self.solver.set(timeout=5000)
        self.unsupported_premises: list[str] = []
        self.label_metadata: dict[str, dict] = {}
        self._entities: dict[str, object] = {}
        self._unary_predicates: dict[str, object] = {}
        self._binary_predicates: dict[str, object] = {}
        self._propositions: dict[str, object] = {}
        self._tracking_index = 0

        rules_by_premise: dict[str, list[Rule]] = {}
        for rule in rules:
            for premise_id in rule.source_premise_ids:
                rules_by_premise.setdefault(premise_id, []).append(rule)

        for premise in premises:
            premise_id = premise["premise_id"]
            source_rules = rules_by_premise.get(premise_id, [])
            if source_rules:
                disjunction_facts = [
                    rule for rule in source_rules
                    if rule.disjunctive and not rule.antecedents
                ]
                if disjunction_facts:
                    self._add_premise_disjunction(premise_id, disjunction_facts[0])
                continue

            if (
                RULE_SENTENCE_PATTERN.match(premise["text"].strip())
                or re.search(r"\s+and\s+|\s+or\s+", premise["text"], flags=re.IGNORECASE)
            ):
                self.unsupported_premises.append(premise_id)
                continue
            atom = parse_atom(premise["text"])
            if atom is None:
                self.unsupported_premises.append(premise_id)
                continue
            self._track(
                self._atom_expression(atom),
                {"kind": "premise", "id": premise_id},
            )

        for rule in rules:
            if rule.disjunctive and not rule.antecedents and rule.source_premise_ids:
                continue
            expression = self._rule_expression(rule)
            source_ids = list(rule.source_premise_ids)
            self._track(
                expression,
                {"kind": "rule", "id": rule.rule_id, "source_premise_ids": source_ids},
            )

        for relation in self._transitive_relations(premises, rules):
            self._add_transitivity_rule(relation)

        self.base_status = self.solver.check()
        self.inconsistency_provenance = self._provenance(self.solver.unsat_core()) if self.base_status == unsat else {
            "premises_used": [],
            "rules_used": [],
        }

    @property
    def inconsistent(self) -> bool:
        return self.base_status == unsat

    def check_claim(self, claim: Atom) -> SolverCheck:
        if self.inconsistent:
            return SolverCheck(
                "UNKNOWN",
                logical_validity_score(0, 1),
                self.inconsistency_provenance["premises_used"],
                self.inconsistency_provenance["rules_used"],
                "The supplied premises and rules are inconsistent.",
            )
        if str(self.base_status) == "unknown":
            return SolverCheck("UNKNOWN", logical_validity_score(0, 1), [], [], self.solver.reason_unknown())
        if self.unsupported_premises:
            return SolverCheck(
                "UNKNOWN",
                logical_validity_score(0, 1),
                [],
                [],
                "Some premise syntax could not be represented safely.",
            )

        expression = self._atom_expression(claim)
        negated_status, negated_core = self._check_with_query(Not(expression), "negated_claim")
        if negated_status == unsat:
            provenance = self._provenance(negated_core)
            entailment_checks = [negated_status == unsat]
            return SolverCheck(
                "ENTAILED",
                logical_validity_score(sum(entailment_checks), len(entailment_checks)),
                provenance["premises_used"],
                provenance["rules_used"],
            )
        if str(negated_status) == "unknown":
            return SolverCheck("UNKNOWN", logical_validity_score(0, 1), [], [], self.solver.reason_unknown())

        claim_status, claim_core = self._check_with_query(expression, "claim")
        if claim_status == unsat:
            provenance = self._provenance(claim_core)
            return SolverCheck(
                "CONTRADICTED",
                logical_validity_score(0, 1),
                provenance["premises_used"],
                provenance["rules_used"],
            )
        if str(claim_status) == "unknown":
            return SolverCheck("UNKNOWN", logical_validity_score(0, 1), [], [], self.solver.reason_unknown())
        return SolverCheck("UNKNOWN", logical_validity_score(0, 1), [], [])

    def _check_with_query(self, query, query_kind: str):
        self.solver.push()
        tracking_label = self._new_label(query_kind)
        self.solver.assert_and_track(query, Bool(tracking_label))
        status = self.solver.check()
        core = list(self.solver.unsat_core()) if status == unsat else []
        self.solver.pop()
        return status, core

    def _atom_expression(self, atom: Atom, variables: dict[str, object] | None = None):
        variables = variables or {}
        if atom.subject == "$prop":
            expression = self._formula_expression(atom.predicate, variables)
        elif atom.object is not None:
            predicate = self._binary_predicates.setdefault(
                atom.predicate,
                Function(self._symbol("relation", atom.predicate), ENTITY, ENTITY, BoolSort()),
            )
            expression = predicate(
                self._entity(atom.subject, variables),
                self._entity(atom.object, variables),
            )
        else:
            predicate = self._unary_predicates.setdefault(
                atom.predicate,
                Function(self._symbol("predicate", atom.predicate), ENTITY, BoolSort()),
            )
            expression = predicate(self._entity(atom.subject, variables))
        return Not(expression) if atom.negated else expression

    def _formula_expression(self, formula: str, variables: dict[str, object]):
        disjunction = re.split(r"\s+or\s+", formula, flags=re.IGNORECASE)
        if len(disjunction) > 1:
            atoms = [parse_atom(part) for part in disjunction]
            if all(atoms):
                return Or(*(self._atom_expression(atom, variables) for atom in atoms))
        conjunction = re.split(r"\s+and\s+", formula, flags=re.IGNORECASE)
        if len(conjunction) > 1:
            atoms = [parse_atom(part) for part in conjunction]
            if all(atoms):
                return And(*(self._atom_expression(atom, variables) for atom in atoms))
        return self._propositions.setdefault(
            formula,
            Bool(self._symbol("proposition", formula)),
        )

    def _rule_expression(self, rule: Rule):
        variables: dict[str, object] = {}
        if any(
            atom.subject == "$x" or atom.object == "$x"
            for atom in (*rule.antecedents, *rule.consequents)
        ):
            variables["$x"] = Const(self._symbol("variable", rule.rule_id), ENTITY)

        antecedents = [self._atom_expression(atom, variables) for atom in rule.antecedents]
        antecedent = And(*antecedents) if antecedents else BoolVal(True)
        consequents = [self._atom_expression(atom, variables) for atom in rule.consequents]
        consequent = (
            Or(*consequents)
            if rule.disjunctive
            else And(*consequents)
        )
        formula = Implies(antecedent, consequent) if rule.antecedents else consequent
        if variables:
            return ForAll(list(variables.values()), formula)
        return formula

    def _add_premise_disjunction(self, premise_id: str, rule: Rule) -> None:
        alternatives = [self._atom_expression(atom) for atom in rule.consequents]
        self._track(
            Or(*alternatives),
            {"kind": "premise", "id": premise_id},
        )

    def _add_transitivity_rule(self, relation: str) -> None:
        left, middle, right = (
            Const(self._symbol("transitivity", f"{relation}_{name}"), ENTITY)
            for name in ("left", "middle", "right")
        )
        predicate = self._binary_predicates.setdefault(
            relation,
            Function(self._symbol("relation", relation), ENTITY, ENTITY, BoolSort()),
        )
        transitive = ForAll(
            [left, middle, right],
            Implies(
                And(predicate(left, middle), predicate(middle, right)),
                predicate(left, right),
            ),
        )
        self._track(
            transitive,
            {"kind": "rule", "id": f"r_transitivity_{relation}", "source_premise_ids": []},
        )

    def _transitive_relations(self, premises: list[dict[str, str]], rules: list[Rule]) -> set[str]:
        relations = set()
        for premise in premises:
            atom = parse_atom(premise["text"])
            if atom and atom.object and atom.predicate in TRANSITIVE_RELATIONS:
                relations.add(atom.predicate)
        for rule in rules:
            relations.update(
                atom.predicate
                for atom in (*rule.antecedents, *rule.consequents)
                if atom.object and atom.predicate in TRANSITIVE_RELATIONS
            )
        return relations

    def _entity(self, name: str, variables: dict[str, object]):
        if name in variables:
            return variables[name]
        return self._entities.setdefault(name, Const(self._symbol("entity", name), ENTITY))

    def _track(self, expression, metadata: dict) -> None:
        label = self._new_label(str(metadata["id"]))
        self.label_metadata[label] = metadata
        self.solver.assert_and_track(expression, Bool(label))

    def _new_label(self, label: str) -> str:
        self._tracking_index += 1
        safe = re.sub(r"\W+", "_", label)
        return f"logical_assertion_{self._tracking_index}_{safe}"

    def _provenance(self, core: list) -> dict[str, list[str]]:
        premises: set[str] = set()
        rules: set[str] = set()
        for label in core:
            metadata = self.label_metadata.get(str(label))
            if not metadata:
                continue
            if metadata["kind"] == "premise":
                premises.add(metadata["id"])
            else:
                rules.add(metadata["id"])
                premises.update(metadata.get("source_premise_ids", []))
        return {"premises_used": sorted(premises), "rules_used": sorted(rules)}

    @staticmethod
    def _symbol(kind: str, value: str) -> str:
        digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]
        return f"{kind}_{digest}"