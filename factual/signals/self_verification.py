from __future__ import annotations


def self_verification_score(question: str, step_text: str, claim_text: str | None = None) -> float:
    text = (claim_text or step_text or question).lower()
    score = 0.5

    if any(keyword in text for keyword in ("capital", "author", "written by", "ended", "was", "is")):
        score += 0.2
    if len(text.split()) >= 5:
        score += 0.1
    if any(marker in text for marker in ("official", "reliable", "confirmed", "reference")):
        score += 0.1

    return max(0.0, min(1.0, score))
