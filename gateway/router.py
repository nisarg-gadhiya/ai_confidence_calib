from gateway.classifier import classify_question


def route_question(question: str) -> str:
    category = classify_question(question)

    if category in {"arithmetic", "logical", "factual"}:
        return category

    raise ValueError(f"Unsupported question category: {category!r}")
