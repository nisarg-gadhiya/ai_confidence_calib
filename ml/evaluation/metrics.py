import math
from collections.abc import Sequence


def _validate_inputs(
    probabilities: Sequence[float],
    labels: Sequence[int],
    n_bins: int | None = None,
) -> None:
    if len(probabilities) != len(labels):
        raise ValueError("probabilities and labels must have equal length")
    if any(not 0 <= probability <= 1 for probability in probabilities):
        raise ValueError("probabilities must be between 0 and 1")
    if any(label not in (0, 1) for label in labels):
        raise ValueError("labels must be binary values 0 or 1")
    if n_bins is not None and n_bins < 1:
        raise ValueError("n_bins must be at least 1")


def brier_score(
    probability: float,
    label: int,
) -> float:

    return (
        probability - label
    ) ** 2


def binary_nll(
    probability: float,
    label: int,
) -> float:

    probability = min(
        max(probability, 1e-12),
        1 - 1e-12,
    )

    return -(
        label * math.log(probability)
        + (1 - label)
        * math.log(1 - probability)
    )


def expected_calibration_error(
    probabilities: list[float],
    labels: list[int],
    n_bins: int = 10,
) -> float:

    _validate_inputs(probabilities, labels, n_bins)

    if not probabilities:
        return 0.0

    total = len(probabilities)

    ece = 0.0

    for bin_index in range(n_bins):

        lower = bin_index / n_bins
        upper = (bin_index + 1) / n_bins

        indices = [
            i
            for i, probability
            in enumerate(probabilities)
            if (
                lower <= probability < upper
                or (
                    bin_index == n_bins - 1
                    and probability == upper
                )
            )
        ]

        if not indices:
            continue

        confidence = (
            sum(
                probabilities[i]
                for i in indices
            )
            / len(indices)
        )

        accuracy = (
            sum(
                labels[i]
                for i in indices
            )
            / len(indices)
        )

        ece += (
            len(indices)
            / total
            * abs(
                confidence - accuracy
            )
        )

    return ece


def maximum_calibration_error(
    probabilities: list[float],
    labels: list[int],
    n_bins: int = 10,
) -> float:
    _validate_inputs(probabilities, labels, n_bins)
    if not probabilities:
        return 0.0

    return max(
        (
            abs(
                sum(probabilities[index] for index in indices) / len(indices)
                - sum(labels[index] for index in indices) / len(indices)
            )
            for indices in _bin_indices(probabilities, n_bins)
            if indices
        ),
        default=0.0,
    )


def binary_auroc(
    probabilities: list[float],
    labels: list[int],
) -> float | None:
    _validate_inputs(probabilities, labels)
    positive_count = sum(labels)
    negative_count = len(labels) - positive_count
    if positive_count == 0 or negative_count == 0:
        return None

    ranked = sorted(range(len(probabilities)), key=probabilities.__getitem__)
    positive_rank_sum = 0.0
    index = 0
    while index < len(ranked):
        end = index + 1
        while (
            end < len(ranked)
            and probabilities[ranked[end]] == probabilities[ranked[index]]
        ):
            end += 1
        average_rank = ((index + 1) + end) / 2
        positive_rank_sum += sum(labels[ranked[position]] for position in range(index, end)) * average_rank
        index = end

    return (
        positive_rank_sum - positive_count * (positive_count + 1) / 2
    ) / (positive_count * negative_count)


def reliability_bins(
    probabilities: list[float],
    labels: list[int],
    n_bins: int = 10,
) -> list[dict[str, float | int]]:
    _validate_inputs(probabilities, labels, n_bins)
    bins: list[dict[str, float | int]] = []
    for indices in _bin_indices(probabilities, n_bins):
        if not indices:
            continue
        bins.append(
            {
                "count": len(indices),
                "mean_confidence": sum(probabilities[index] for index in indices) / len(indices),
                "accuracy": sum(labels[index] for index in indices) / len(indices),
            }
        )
    return bins


def _bin_indices(
    probabilities: Sequence[float],
    n_bins: int,
) -> list[list[int]]:
    bins = [[] for _ in range(n_bins)]
    for index, probability in enumerate(probabilities):
        bin_index = min(int(probability * n_bins), n_bins - 1)
        bins[bin_index].append(index)
    return bins