def verify_step(
    question: str,
    step_text: str,
) -> float:
    """
    Development baseline.

    This is intentionally simple.
    Later this will become the actual LLM self-verification signal.
    """

    score = 0.50

    if any(
        character.isdigit()
        for character in step_text
    ):
        score += 0.15

    if any(
        operator in step_text
        for operator in (
            "+",
            "-",
            "*",
            "/",
            "=",
        )
    ):
        score += 0.10

    if len(step_text.split()) >= 5:
        score += 0.10

    if any(
        word in step_text.lower()
        for word in (
            "therefore",
            "because",
            "so",
            "result",
        )
    ):
        score += 0.05

    return max(
        0.0,
        min(1.0, score),
    )