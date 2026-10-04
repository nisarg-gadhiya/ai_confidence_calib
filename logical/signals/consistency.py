from __future__ import annotations

from app.services.consistency_service import exact_agreement_score, semantic_cluster_metrics


def assess_consistency(
    samples: list[str],
    cluster_ids: list[int] | None,
    fact_count: int = 0,
    contradiction_count: int = 0,
) -> tuple[float, float | None, str]:
    if cluster_ids is None:
        score = exact_agreement_score(samples)
        entropy = None
        method = "exact_match_fallback"
    else:
        score, entropy = semantic_cluster_metrics(cluster_ids)
        method = "model_semantic_clusters"
    if fact_count > 0:
        consistent_fact_count = max(0, fact_count - (2 * contradiction_count))
        score *= consistent_fact_count / fact_count
    return score, entropy, method