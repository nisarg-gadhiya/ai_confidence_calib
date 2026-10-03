import math


def entropy(
    probabilities: list[float],
) -> float:

    if not probabilities:
        return 0.0

    return -sum(
        probability * math.log(probability)
        for probability in probabilities
        if probability > 0
    )


def mean_token_probability(
    probabilities: list[float],
) -> float:

    if not probabilities:
        return 0.0

    return (
        sum(probabilities)
        / len(probabilities)
    )