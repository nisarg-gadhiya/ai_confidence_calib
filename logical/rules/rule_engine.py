from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from logical.rules.extractor import Atom, Rule, TRANSITIVE_RELATIONS, parse_atom
from logical.rules.solver import LogicalSolver


@dataclass(frozen=True)
class Derivation:
    atom: Atom
    premise_ids: frozenset[str]
    rule_ids: frozenset[str]
    operation: str
    depth: int

    @property
    def checks(self) -> int:
        return len(self.premise_ids) + len(self.rule_ids)


@dataclass
class RuleEngineResult:
    facts: dict[tuple[str, str, str | None, bool], Derivation]
    derivations: list[Derivation]
    inconsistent_atoms: list[tuple[str, str, str | None]]
    disjunctions: list["DisjunctionDerivation"]
    logic_solver: LogicalSolver

    @property
    def inconsistent(self) -> bool:
        return self.logic_solver.inconsistent or bool(self.inconsistent_atoms)


@dataclass(frozen=True)
class DisjunctionDerivation:
    atoms: tuple[Atom, ...]
    premise_ids: frozenset[str]
    rule_ids: frozenset[str]


def _add_disjunction(
    disjunctions: list[DisjunctionDerivation],
    atoms: tuple[Atom, ...],
    sources: list[Derivation],
    rule: Rule,
) -> None:
    atom_keys = frozenset(atom.key for atom in atoms)
    if any(frozenset(atom.key for atom in existing.atoms) == atom_keys for existing in disjunctions):
        return
    premise_ids = frozenset(rule.source_premise_ids).union(
        *(item.premise_ids for item in sources)
    )
    rule_ids = frozenset({rule.rule_id} if rule.antecedents else ()).union(
        *(item.rule_ids for item in sources)
    )
    disjunctions.append(DisjunctionDerivation(atoms, premise_ids, rule_ids))


def _unify(pattern: Atom, fact: Atom, substitutions: dict[str, str]) -> dict[str, str] | None:
    if pattern.predicate != fact.predicate or pattern.object != fact.object or pattern.negated != fact.negated:
        return None
    if pattern.subject == "$x":
        bound = substitutions.get("$x")
        if bound is not None and bound != fact.subject:
            return None
        return {**substitutions, "$x": fact.subject}
    return substitutions if pattern.subject == fact.subject else None


def _match_antecedents(
    antecedents: tuple[Atom, ...],
    facts: dict[tuple[str, str, str | None, bool], Derivation],
) -> list[tuple[dict[str, str], list[Derivation]]]:
    matches: list[tuple[dict[str, str], list[Derivation]]] = [({}, [])]
    for antecedent in antecedents:
        next_matches = []
        for substitutions, derivations in matches:
            for known in facts.values():
                updated = _unify(antecedent, known.atom, substitutions)
                if updated is not None:
                    next_matches.append((updated, [*derivations, known]))
        matches = next_matches
        if not matches:
            break
    return matches


def _instantiate(atom: Atom, substitutions: dict[str, str]) -> Atom:
    subject = substitutions.get(atom.subject, atom.subject)
    obj = substitutions.get(atom.object, atom.object) if atom.object else None
    return Atom(subject, atom.predicate, obj, atom.negated)


def _combine_derivations(
    atom: Atom,
    sources: list[Derivation],
    rule_id: str | None,
    operation: str,
) -> Derivation:
    premise_ids = frozenset().union(*(item.premise_ids for item in sources))
    rule_ids = frozenset().union(*(item.rule_ids for item in sources))
    if rule_id:
        rule_ids = rule_ids | {rule_id}
    return Derivation(
        atom,
        premise_ids,
        rule_ids,
        operation,
        max((item.depth for item in sources), default=0) + 1,
    )


def _find_inconsistencies(
    facts: dict[tuple[str, str, str | None, bool], Derivation],
) -> list[tuple[str, str, str | None]]:
    bases = {item.atom.base_key for item in facts.values()}
    return sorted(
        (
            base
            for base in bases
            if Atom(*base, False).key in facts and Atom(*base, True).key in facts
        ),
        key=lambda item: (item[0], item[1], item[2] or ""),
    )


def run_rule_engine(
    premises: list[dict[str, str]],
    rules: list[Rule],
) -> RuleEngineResult:
    """Build an explanatory trace; LogicalSolver is authoritative for verdicts."""
    facts: dict[tuple[str, str, str | None, bool], Derivation] = {}
    rule_premise_ids = {
        premise_id
        for rule in rules
        for premise_id in rule.source_premise_ids
    }
    for premise in premises:
        if premise["premise_id"] in rule_premise_ids:
            continue
        atom = parse_atom(premise["text"])
        if atom is not None:
            facts.setdefault(
                atom.key,
                Derivation(atom, frozenset({premise["premise_id"]}), frozenset(), "premise", 0),
            )

    derivations: list[Derivation] = []
    disjunctions: list[DisjunctionDerivation] = []
    max_passes = max(1, len(premises) * (len(rules) + 1) + 1)
    for _ in range(max_passes):
        additions: list[Derivation] = []
        for rule in rules:
            for substitutions, matched in _match_antecedents(rule.antecedents, facts):
                if rule.disjunctive:
                    alternatives = tuple(_instantiate(item, substitutions) for item in rule.consequents)
                    _add_disjunction(disjunctions, alternatives, matched, rule)
                    continue
                for consequent in rule.consequents:
                    atom = _instantiate(consequent, substitutions)
                    if atom.key not in facts:
                        additions.append(
                            _combine_derivations(atom, matched, rule.rule_id, "modus_ponens")
                        )

        relational = [item for item in facts.values() if item.atom.predicate in TRANSITIVE_RELATIONS and item.atom.object]
        for left, right in product(relational, repeat=2):
            if left.atom.predicate != right.atom.predicate or left.atom.object != right.atom.subject:
                continue
            atom = Atom(left.atom.subject, left.atom.predicate, right.atom.object)
            if atom.key not in facts:
                transitivity_id = f"r_transitivity_{atom.predicate}"
                additions.append(
                    _combine_derivations(
                        atom,
                        [left, right],
                        transitivity_id,
                        "transitivity",
                    )
                )

        unique_additions = {item.atom.key: item for item in additions if item.atom.key not in facts}
        if not unique_additions:
            break
        facts.update(unique_additions)
        derivations.extend(unique_additions.values())

    logic_solver = LogicalSolver(premises, rules)
    return RuleEngineResult(
        facts,
        derivations,
        _find_inconsistencies(facts),
        disjunctions,
        logic_solver,
    )