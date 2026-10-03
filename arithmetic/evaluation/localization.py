def rank_steps_by_confidence(
    confidences: dict[int, float],
) -> list[int]:

    return sorted(
        confidences,
        key=confidences.get,
    )


def top1(
    predicted_steps: list[int],
    true_error_step: int,
) -> float:

    if not predicted_steps:
        return 0.0

    return float(
        predicted_steps[0]
        == true_error_step
    )


def top2(
    predicted_steps: list[int],
    true_error_step: int,
) -> float:

    return float(
        true_error_step
        in predicted_steps[:2]
    )


def evaluate_localization(
    cases: list[dict],
) -> dict[str, float | int]:
    eligible = [
        case
        for case in cases
        if case.get("true_error_step") is not None
        and case.get("final_answer_correct") is False
    ]
    if not eligible:
        return {"evaluated_cases": 0, "top1_accuracy": 0.0, "top2_accuracy": 0.0}

    top1_total = 0.0
    top2_total = 0.0
    for case in eligible:
        ranked = rank_steps_by_confidence(case["confidences"])
        true_step = case["true_error_step"]
        top1_total += top1(ranked, true_step)
        top2_total += top2(ranked, true_step)

    return {
        "evaluated_cases": len(eligible),
        "top1_accuracy": top1_total / len(eligible),
        "top2_accuracy": top2_total / len(eligible),
    }