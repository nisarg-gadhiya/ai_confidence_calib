def top_k_localization(
    predicted_ranking: list[int],
    true_error_step: int,
    k: int,
) -> bool:

    return true_error_step in predicted_ranking[:k]


def localization_metrics(
    ranked_steps: list[int],
    true_error_step: int,
) -> dict[str, float]:

    return {
        "top1_accuracy": float(
            top_k_localization(
                ranked_steps,
                true_error_step,
                1,
            )
        ),

        "top2_accuracy": float(
            top_k_localization(
                ranked_steps,
                true_error_step,
                2,
            )
        ),
    }