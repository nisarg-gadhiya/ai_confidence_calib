def verification_score_from_labels(
    verifier_outputs: list[bool],
) -> float:

    if not verifier_outputs:
        return 0.0

    return (
        sum(verifier_outputs)
        / len(verifier_outputs)
    )