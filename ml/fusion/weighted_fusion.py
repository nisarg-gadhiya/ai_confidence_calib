def weighted_fusion(
    verification: float,
    consistency: float,
    verification_weight: float = 0.5,
    consistency_weight: float = 0.5,
) -> float:

    total_weight = (
        verification_weight
        + consistency_weight
    )

    if total_weight <= 0:

        raise ValueError(
            "Weights must sum to a positive value."
        )

    confidence = (
        verification * verification_weight
        + consistency * consistency_weight
    ) / total_weight

    return confidence