import math
from collections.abc import Mapping


NUMERIC_FEATURES = (
    "verification_score",
    "consistency_score",
    "sample_agreement_score",
    "semantic_entropy",
    "mean_token_logprob",
    "token_entropy",
)

STEP_TYPES = (
    "arithmetic",
    "unit_conversion",
    "factual_recall",
    "logical_inference",
    "setup",
    "conclusion",
    "other",
)

FEATURE_NAMES = NUMERIC_FEATURES + tuple(
    f"step_type_{step_type}"
    for step_type in STEP_TYPES
)


def encode_feature_rows(
    rows: list[Mapping[str, object]],
) -> list[list[float]]:
    encoded: list[list[float]] = []
    for row in rows:
        features: list[float] = []
        for name in NUMERIC_FEATURES:
            value = row.get(name)
            features.append(
                float(value)
                if isinstance(value, (int, float)) and not isinstance(value, bool)
                else math.nan
            )

        step_type = row.get("step_type")
        normalized_type = step_type if step_type in STEP_TYPES else "other"
        features.extend(
            float(normalized_type == category)
            for category in STEP_TYPES
        )
        encoded.append(features)
    return encoded