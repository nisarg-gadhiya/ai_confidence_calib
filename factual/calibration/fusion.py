from __future__ import annotations


def fuse_step_signals(
    self_verification_score: float,
    consistency_score: float,
    evidence_score: float,
    weights: dict[str, float] | None = None,
) -> float:
    if weights is None:
        weights = {
            "self_verification": 0.4,
            "consistency": 0.3,
            "evidence": 0.3,
        }
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("Fusion weights must sum to a positive value.")
    fused = (
        self_verification_score * weights["self_verification"]
        + consistency_score * weights["consistency"]
        + evidence_score * weights["evidence"]
    ) / total
    return max(0.0, min(1.0, fused))
