from ml.evaluation.localization import (
    rank_steps_by_confidence,
    top1,
    top2,
)


def test_localization():

    ranked = rank_steps_by_confidence(
        {
            1: 0.9,
            2: 0.2,
            3: 0.7,
        }
    )

    assert ranked == [
        2,
        3,
        1,
    ]

    assert top1(
        ranked,
        2,
    ) == 1.0

    assert top2(
        ranked,
        3,
    ) == 1.0