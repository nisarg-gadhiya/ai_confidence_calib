from ml.evaluation.localization import (
    rank_steps_by_confidence,
)

from ml.fusion.weighted_fusion import (
    weighted_fusion,
)


def main():

    verification = {
        1: 0.94,
        2: 0.87,
        3: 0.42,
    }

    consistency = {
        1: 0.90,
        2: 0.80,
        3: 0.40,
    }

    fused = {
        step: weighted_fusion(
            verification[step],
            consistency[step],
        )
        for step in verification
    }

    ranking = rank_steps_by_confidence(
        fused
    )

    print(
        "Fused confidence:",
        fused,
    )

    print(
        "Lowest-confidence step:",
        ranking[0],
    )


if __name__ == "__main__":
    main()