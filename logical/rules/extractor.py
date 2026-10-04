from __future__ import annotations

import re
from dataclasses import dataclass


ARTICLES = {"a", "an", "the"}
VARIABLE_SUBJECTS = {"someone", "somebody", "anyone", "anybody", "they", "he", "she"}
RELATIONS = {
    "taller than": "taller_than",
    "shorter than": "shorter_than",
    "older than": "older_than",
    "younger than": "younger_than",
    "greater than": "greater_than",
    "less than": "less_than",
    "larger than": "larger_than",
    "smaller than": "smaller_than",
    "before": "before",
    "after": "after",
    "above": "above",
    "below": "below",
}
TRANSITIVE_RELATIONS = {
    "taller_than",
    "shorter_than",
    "older_than",
    "younger_than",
    "greater_than",
    "less_than",
    "larger_than",
    "smaller_than",
    "before",
    "after",
    "above",
    "below",
}
COUNTABLE_PREDICATES = {
    "animal",
    "cat",
    "dog",
    "mammal",
    "person",
    "student",
    "teacher",
}
IRREGULAR_FORMS = {
    "raining": "rain",
    "rains": "rain",
    "studies": "study",
    "studying": "study",
    "passes": "pass",
    "passing": "pass",
    "becomes": "become",
    "became": "become",
    "is": "be",
    "are": "be",
    "was": "be",
    "were": "be",
    "mammals": "mammal",
    "cats": "cat",
    "dogs": "dog",
    "animals": "animal",
    "boxes": "box",
}


@dataclass(frozen=True)
class Atom:
    subject: str
    predicate: str
    object: str | None = None
    negated: bool = False

    @property
    def key(self) -> tuple[str, str, str | None, bool]:
        return self.subject, self.predicate, self.object, self.negated

    @property
    def base_key(self) -> tuple[str, str, str | None]:
        return self.subject, self.predicate, self.object

    def opposite(self) -> Atom:
        return Atom(self.subject, self.predicate, self.object, not self.negated)

    def to_text(self) -> str:
        if self.subject == "$prop":
            text = self.predicate[:1].upper() + self.predicate[1:]
        elif self.object is not None:
            text = (
                f"{self.subject.title()} is {self.predicate.replace('_', ' ')} "
                f"{self.object.title()}"
            )
        else:
            article = "an " if self.predicate[:1] in "aeiou" else "a "
            predicate = (
                f"{article}{self.predicate}"
                if self.predicate in COUNTABLE_PREDICATES
                else self.predicate
            )
            negation = "not " if self.negated else ""
            text = f"{self.subject.title()} is {negation}{predicate}"
        if self.negated and self.object is not None:
            return f"{self.subject.title()} is not {self.predicate.replace('_', ' ')} {self.object.title()}"
        return f"not {text}" if self.negated and self.subject == "$prop" else text


@dataclass(frozen=True)
class Rule:
    rule_id: str
    text: str
    antecedents: tuple[Atom, ...]
    consequents: tuple[Atom, ...]
    disjunctive: bool = False
    source_premise_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "text": self.text,
            "antecedents": [atom.to_text() for atom in self.antecedents],
            "consequents": [atom.to_text() for atom in self.consequents],
            "disjunctive": self.disjunctive,
        }


def _normalize_words(text: str) -> str:
    words = re.findall(r"[\w'-]+", text.lower())
    normalized = []
    for word in words:
        if word in ARTICLES:
            continue
        value = IRREGULAR_FORMS.get(word, word)
        if value == word and len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
            value = word[:-1]
        normalized.append(value)
    return " ".join(normalized)


def parse_atom(text: str) -> Atom | None:
    cleaned = re.sub(r"^[\s\-*•]+", "", text).strip().rstrip(".!?;,")
    cleaned = re.sub(r"^(?:it follows that|therefore|thus|hence)\s+", "", cleaned, flags=re.IGNORECASE)
    if not cleaned:
        return None
    if re.search(r"\s+or\s+", cleaned, flags=re.IGNORECASE):
        formula = " ".join(re.findall(r"[\w'-]+", cleaned.lower()))
        return Atom("$prop", formula) if formula else None
    negated_proposition = re.match(r"^not\s+([A-Z])$", cleaned, flags=re.IGNORECASE)
    if negated_proposition:
        return Atom("$prop", negated_proposition.group(1).lower(), negated=True)
    propositional_truth = re.match(r"^([A-Z])\s+is\s+(true|false)$", cleaned, flags=re.IGNORECASE)
    if propositional_truth:
        symbol, truth = propositional_truth.groups()
        return Atom("$prop", symbol.lower(), negated=truth.lower() == "false")
    propositional_question = re.match(r"^([A-Z])\s+(true|false)$", cleaned, flags=re.IGNORECASE)
    if propositional_question:
        symbol, truth = propositional_question.groups()
        return Atom("$prop", symbol.lower(), negated=truth.lower() == "false")
    if re.match(r"^[A-Z]$", cleaned):
        return Atom("$prop", cleaned.lower())

    for phrase, relation in sorted(RELATIONS.items(), key=lambda item: -len(item[0])):
        match = re.match(
            rf"^(.+?)\s+(?:is\s+)?{re.escape(phrase)}\s+(.+)$",
            cleaned,
            flags=re.IGNORECASE,
        )
        if match:
            subject = _normalize_words(match.group(1))
            obj = _normalize_words(match.group(2))
            if subject and obj:
                return Atom(subject, relation, obj)

    match = re.match(
        r"^(.+?)\s+(?:is|are|was|were|becomes?|has|have|does|do)\s+(not\s+)?(.+)$",
        cleaned,
        flags=re.IGNORECASE,
    )
    if match:
        subject_text, negative, predicate_text = match.groups()
        subject = _normalize_subject(subject_text)
        predicate = _normalize_words(predicate_text)
        if predicate == "not":
            return None
        return Atom(subject, predicate, negated=bool(negative)) if subject and predicate else None

    words = cleaned.split()
    if len(words) == 1:
        proposition = cleaned.lower()
        return Atom("$prop", proposition) if proposition else None

    subject = _normalize_subject(words[0])
    remainder = " ".join(words[1:])
    negative = bool(re.match(r"^not\b", remainder, flags=re.IGNORECASE))
    if negative:
        remainder = re.sub(r"^not\s+", "", remainder, flags=re.IGNORECASE)
    predicate = _normalize_words(remainder)
    if subject in {"a", "an", "the"} or not subject or not predicate:
        return None
    return Atom(subject, predicate, negated=negative)


def _normalize_subject(text: str) -> str:
    subject = _normalize_words(text)
    if subject in VARIABLE_SUBJECTS:
        return "$x"
    if subject == "$x":
        return subject
    return subject


def extract_rules(premises: list[dict[str, str]]) -> list[Rule]:
    rules: list[Rule] = []
    for premise in premises:
        text = premise["text"].strip().rstrip(".")
        universal = re.match(r"^all\s+(.+?)\s+are\s+(.+)$", text, flags=re.IGNORECASE)
        if universal:
            antecedent = parse_atom(f"someone is a {universal.group(1)}")
            if re.search(r"\s+or\s+", universal.group(2), flags=re.IGNORECASE):
                continue
            consequents = [
                parse_atom(f"someone is a {clause}")
                for clause in re.split(r"\s+and\s+", universal.group(2), flags=re.IGNORECASE)
            ]
            consequents = [consequent for consequent in consequents if consequent]
            if antecedent and consequents:
                for index, consequent in enumerate(consequents, start=1):
                    suffix = f"_{index}" if len(consequents) > 1 else ""
                    rules.append(
                        Rule(
                            premise["premise_id"].replace("p", "r", 1) + suffix,
                            premise["text"],
                            (antecedent,),
                            (consequent,),
                            source_premise_ids=(premise["premise_id"],),
                        )
                    )
            continue

        conditional = re.match(r"^if\s+(.+?)(?:,|\bthen\b)\s*(.+)$", text, flags=re.IGNORECASE)
        symbolic = re.match(r"^(.+?)\s*(?:->|=>|\bimplies\b)\s*(.+)$", text, flags=re.IGNORECASE)
        rule_id = premise["premise_id"].replace("p", "r", 1)
        if not conditional and re.search(r"\s+or\s+", text, flags=re.IGNORECASE):
            alternatives = tuple(
                atom
                for clause in re.split(r"\s+or\s+", text, flags=re.IGNORECASE)
                if (atom := parse_atom(clause)) is not None
            )
            if len(alternatives) > 1:
                rules.append(
                    Rule(
                        rule_id,
                        premise["text"],
                        (),
                        alternatives,
                        disjunctive=True,
                        source_premise_ids=(premise["premise_id"],),
                    )
                )
            continue
        if not conditional and symbolic:
            antecedent = parse_atom(symbolic.group(1))
            consequent = parse_atom(symbolic.group(2))
            if antecedent and consequent:
                rules.append(
                    Rule(
                        rule_id,
                        premise["text"],
                        (antecedent,),
                        (consequent,),
                        source_premise_ids=(premise["premise_id"],),
                    )
                )
            continue
        if not conditional:
            continue
        antecedent_text, consequent_text = conditional.groups()
        antecedents = tuple(
            atom
            for clause in re.split(r"\s+and\s+", antecedent_text, flags=re.IGNORECASE)
            if (atom := parse_atom(clause)) is not None
        )
        disjunctive = bool(re.search(r"\s+or\s+", consequent_text, flags=re.IGNORECASE))
        conjunctions = re.split(r"\s+or\s+", consequent_text, flags=re.IGNORECASE) if disjunctive else [consequent_text]
        consequent_clauses = [
            clause
            for conjunction in conjunctions
            for clause in re.split(r"\s+and\s+", conjunction, flags=re.IGNORECASE)
        ]
        consequents = tuple(
            atom
            for clause in consequent_clauses
            if (atom := parse_atom(clause)) is not None
        )
        if antecedents and consequents:
            rules.append(
                Rule(
                    rule_id,
                    premise["text"],
                    antecedents,
                    consequents,
                    disjunctive=disjunctive,
                    source_premise_ids=(premise["premise_id"],),
                )
            )
    return rules