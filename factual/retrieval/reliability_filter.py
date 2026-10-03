from __future__ import annotations

from factual.retrieval.source_reliability import estimate_source_reliability


def filter_sources(sources: list[dict], keep_threshold: float = 0.75, down_weight_threshold: float = 0.45) -> list[dict]:
    filtered: list[dict] = []
    for source in sources:
        reliability = float(source.get("reliability_score", estimate_source_reliability(source)))
        retrieval_score = float(source.get("retrieval_score", 0.5))
        score = (reliability + retrieval_score) / 2.0
        if score >= keep_threshold:
            status = "KEEP"
        elif score >= down_weight_threshold:
            status = "DOWN_WEIGHT"
        else:
            status = "REJECT"
        filtered.append({**source, "reliability_score": score, "status": status})
    return filtered
