from __future__ import annotations

import re


PREDICATE_PATTERN = re.compile(
    r"\b(?:am|is|are|was|were|be|been|being|has|have|had|do|does|did|"
    r"can|could|will|would|should|must|may|might|consists|contains|includes|"
    r"controls|carries|determines|decides|retains|forgets|provides|uses|"
    r"works|learns|reduces|increases|supports|updates|produces|represents)\b",
    re.IGNORECASE,
)


def _has_predicate(text: str) -> bool:
    return bool(PREDICATE_PATTERN.search(text))


def _split_atomic_claims(text: str) -> list[str]:
    parts = re.split(r"\s+(and|but|however|also)\s+", text, flags=re.IGNORECASE)
    clauses = [parts[0]]
    for index in range(1, len(parts), 2):
        conjunction = parts[index]
        next_clause = parts[index + 1]
        if (
            conjunction.lower() == "and"
            and not (_has_predicate(clauses[-1]) and _has_predicate(next_clause))
        ):
            clauses[-1] = f"{clauses[-1]} and {next_clause}"
        else:
            clauses.append(next_clause)

    candidates = [part.strip(" .,;") for part in clauses if part.strip()]
    normalized: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in normalized:
            normalized.append(candidate.rstrip(".") + ".")
    return normalized or [text.rstrip(".") + "."]


def extract_claims(steps: list[dict]) -> list[dict]:
    claims: list[dict] = []
    for step in steps:
        step_id = step["step_id"]
        text = step["text"]
        for offset, clause in enumerate(_split_atomic_claims(text), start=1):
            claim_text = clause.strip()
            if not claim_text:
                continue
            claims.append(
                {
                    "claim_id": f"c{step_id}_{offset}",
                    "step_id": step_id,
                    "claim_text": claim_text,
                }
            )
    return claims
