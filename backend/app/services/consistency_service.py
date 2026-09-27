from collections import Counter
import math


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

    normalized = [
        normalize(sample)
        for sample in samples
    ]

    counts = Counter(normalized)

    most_common_count = max(
        counts.values()
    )

    return most_common_count / len(samples)


def exact_agreement_score(
    samples: list[str],
) -> float:
    if not samples:
        return 0.0

    counts = Counter(normalize(sample) for sample in samples)
    return max(counts.values()) / len(samples)


def semantic_cluster_metrics(
    cluster_ids: list[int],
) -> tuple[float, float]:
    if not cluster_ids:
        return 0.0, 1.0

    counts = Counter(cluster_ids)
    sample_count = len(cluster_ids)
    agreement = max(counts.values()) / sample_count

    if sample_count == 1:
        return agreement, 0.0

    entropy = -sum(
        (count / sample_count) * math.log(count / sample_count)
        for count in counts.values()
    )
    normalized_entropy = entropy / math.log(sample_count)
    return agreement, normalized_entropy


def prefix_conditioned_consistency(
    question: str,
    prefix: str,
    generated_suffixes: list[str],
) -> float:

    return consistency_score(
        generated_suffixes
    )