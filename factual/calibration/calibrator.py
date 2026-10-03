from __future__ import annotations

import math


def calibrate_probability(
    self_verification_score: float,
    consistency_score: float,
    evidence_score: float,
    fused_confidence: float | None = None,
) -> float:
    fused = fused_confidence if fused_confidence is not None else (
        0.4 * self_verification_score + 0.3 * consistency_score + 0.3 * evidence_score
    )
    logit = -1.0 + 3.2 * fused
    probability = 1.0 / (1.0 + math.exp(-logit))
    return max(0.0, min(1.0, probability))
