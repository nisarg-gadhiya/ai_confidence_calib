from __future__ import annotations

import math


def calculate_answer_confidence(claims: list[dict]) -> float | None:
    """Compute the geometric mean of the calibrated probabilities for essential claims."""
    essential_claims = [claim for claim in claims if claim.get("essential") is True]
    if not essential_claims:
        return None

    probabilities: list[float] = []
    for claim in essential_claims:
        probability = claim.get("calibrated_probability")
        if probability is None or isinstance(probability, bool):
            raise ValueError("Essential claim is missing a valid calibrated_probability.")
        try:
            probability = float(probability)
        except (TypeError, ValueError) as exc:
            raise ValueError("Essential claim calibrated_probability must be numeric.") from exc
        if not 0.0 <= probability <= 1.0:
            raise ValueError("Essential claim calibrated_probability must be between 0 and 1.")
        probabilities.append(probability)

    if any(probability == 0.0 for probability in probabilities):
        return 0.0

    log_confidence = sum(math.log(probability) for probability in probabilities) / len(probabilities)
    return math.exp(log_confidence)
