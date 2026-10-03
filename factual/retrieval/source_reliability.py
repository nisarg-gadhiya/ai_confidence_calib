from __future__ import annotations

from typing import Any

SOURCE_RELIABILITY_WEIGHTS = {
    "official_government": 0.97,
    "government": 0.94,
    "academic": 0.92,
    "reference": 0.9,
    "institutional": 0.88,
    "reputable_news": 0.8,
    "news": 0.78,
    "blog": 0.48,
    "general": 0.52,
}


def estimate_source_reliability(source: dict[str, Any]) -> float:
    domain = str(source.get("domain") or "").lower()
    source_type = str(source.get("source_type") or "general").lower()
    score = SOURCE_RELIABILITY_WEIGHTS.get(source_type, 0.55)

    if "gov" in domain or "government" in domain:
        score = max(score, 0.96)
    if "edu" in domain:
        score = max(score, 0.93)
    if "wikipedia" in domain:
        score = min(score, 0.82)
    if "blog" in domain or "blog" in source_type:
        score = min(score, 0.52)

    return max(0.0, min(1.0, score))
