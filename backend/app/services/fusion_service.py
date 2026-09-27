def fuse_confidence(
    verification_score: float,
    consistency_score: float,
    verification_weight: float | None = None,
    consistency_weight: float | None = None,
    step_type: str = "other",
    token_probability: float | None = None,
) -> float:

    if verification_weight is None and consistency_weight is None:
        weights = fusion_weights(step_type)
        if token_probability is None:
            weights = weights[:2]
        else:
            weights = (*weights[:2], weights[2])
    elif verification_weight is not None and consistency_weight is not None:
        weights = (verification_weight, consistency_weight)
    else:
        raise ValueError("Provide both explicit fusion weights or neither.")

    total_weight = (
        sum(weights)
    )

    if total_weight <= 0:
        raise ValueError(
            "Fusion weights must sum to a positive value."
        )

    confidence = weights[0] * verification_score + weights[1] * consistency_score
    if token_probability is not None and len(weights) == 3:
        confidence += weights[2] * token_probability
    confidence /= total_weight

    return max(
        0.0,
        min(1.0, confidence),
    )


def fusion_weights(
    step_type: str,
) -> tuple[float, float, float]:
    return {
        "arithmetic": (0.35, 0.4, 0.25),
        "unit_conversion": (0.4, 0.35, 0.25),
        "factual_recall": (0.55, 0.25, 0.2),
        "logical_inference": (0.5, 0.3, 0.2),
        "setup": (0.5, 0.3, 0.2),
        "conclusion": (0.5, 0.3, 0.2),
    }.get(step_type, (0.5, 0.3, 0.2))


def predict_error_step(
    confidences: dict[int, float],
) -> int | None:

    if not confidences:
        return None

    return min(
        confidences,
        key=confidences.get,
    )