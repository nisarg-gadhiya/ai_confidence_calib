from __future__ import annotations


def aggregate_evidence_score(
    support_evidence: list[dict] | None = None,
    contradict_evidence: list[dict] | None = None,
    unknown_evidence: list[dict] | None = None,
) -> float:
    support = support_evidence or []
    contradict = contradict_evidence or []
    unknown = unknown_evidence or []

    support_weight = sum(
        (float(item.get("source_reliability", 0.0)) * float(item.get("relevance_score", 0.0)))
        for item in support
    )
    contradict_weight = sum(
        (float(item.get("source_reliability", 0.0)) * float(item.get("relevance_score", 0.0)))
        for item in contradict
    )
    unknown_weight = sum(
        (float(item.get("source_reliability", 0.0)) * float(item.get("relevance_score", 0.0)))
        for item in unknown
    )

    total_weight = support_weight + contradict_weight + unknown_weight
    if total_weight <= 0:
        return 0.0

    score = (support_weight - contradict_weight) / total_weight
    score = max(0.0, min(1.0, (score + 1.0) / 2.0))

    if not support and not contradict:
        return 0.2 + (0.4 * min(1.0, unknown_weight))

    return score
