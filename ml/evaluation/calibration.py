from .metrics import (
    binary_auroc,
    binary_nll,
    brier_score,
    expected_calibration_error,
    maximum_calibration_error,
    reliability_bins,
)


def evaluate_calibration(
    probabilities: list[float],
    labels: list[int],
) -> dict[str, float | None | list[dict[str, float | int]]]:

    if len(probabilities) != len(labels):

        raise ValueError(
            "probabilities and labels "
            "must have equal length"
        )

    if not probabilities:
        raise ValueError("At least one labeled prediction is required")

    return {

        "ece": expected_calibration_error(
            probabilities,
            labels,
        ),

        "mce": maximum_calibration_error(
            probabilities,
            labels,
        ),

        "brier_score": sum(
            brier_score(
                probability,
                label,
            )
            for probability, label
            in zip(
                probabilities,
                labels,
            )
        ) / len(probabilities),

        "nll": sum(
            binary_nll(
                probability,
                label,
            )
            for probability, label
            in zip(
                probabilities,
                labels,
            )
        ) / len(probabilities),

        "auroc": binary_auroc(probabilities, labels),

        "reliability_bins": reliability_bins(probabilities, labels),
    }