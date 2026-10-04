from __future__ import annotations

import re


SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+|\n+")
INSTRUCTION_PATTERN = re.compile(
    r"^(?:identify|determine|analyze|analyse|find|check|consider|suppose|assume)\b",
    re.IGNORECASE,
)


def extract_premises(question: str) -> list[dict[str, str]]:
    statements = [
        statement.strip(" \t\r\n.;")
        for statement in SENTENCE_PATTERN.split(question)
        if statement.strip(" \t\r\n.;")
    ]
    premises = [
        statement
        for statement in statements
        if not statement.endswith("?") and not INSTRUCTION_PATTERN.match(statement)
    ]
    return [
        {"premise_id": f"p{index}", "text": statement + "."}
        for index, statement in enumerate(premises, start=1)
    ]


def extract_target_statement(question: str) -> str | None:
    questions = [
        statement.strip()
        for statement in SENTENCE_PATTERN.split(question)
        if statement.strip().endswith("?")
    ]
    if not questions:
        return None

    target = questions[-1].rstrip("?").strip()
    target = re.sub(r"^(?:is|are|was|were)\s+", "", target, flags=re.IGNORECASE)
    target = re.sub(r"^(?:does|do|did|can|could|would|will)\s+", "", target, flags=re.IGNORECASE)
    target = re.sub(r"\bnecessarily\s+", "", target, flags=re.IGNORECASE)
    target = re.sub(r"\s+", " ", target).strip()
    return target or None