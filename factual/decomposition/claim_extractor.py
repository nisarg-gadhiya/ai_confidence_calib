from __future__ import annotations

import re


def _split_atomic_claims(text: str) -> list[str]:
    clauses = re.split(r"\s+(?:and|but|however|also)\s+", text, flags=re.IGNORECASE)
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
