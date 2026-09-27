from collections import Counter


def normalize(
    text: str,
) -> str:

    return " ".join(
        text.lower().split()
    )


def consistency_score(
    samples: list[str],
) -> float:

    if not samples:
        return 0.0

    normalized_samples = [
        normalize(sample)
        for sample in samples
    ]

    counts = Counter(
        normalized_samples
    )

    most_common = max(
        counts.values()
    )

    return most_common / len(samples)