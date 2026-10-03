from collections import Counter


def normalize(text: str) -> str:
    return " ".join(text.lower().split())


def consistency_score(samples: list[str]) -> float:
    if not samples:
        return 0.0
    normalized = [normalize(sample) for sample in samples]
    counts = Counter(normalized)
    return max(counts.values()) / len(samples)
