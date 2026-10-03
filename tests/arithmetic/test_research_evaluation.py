import pytest

from arithmetic.data.error_injection import inject_numeric_step_error
from arithmetic.evaluation.calibration import evaluate_calibration
from arithmetic.evaluation.localization import evaluate_localization
from arithmetic.evaluation.metrics import binary_auroc, maximum_calibration_error
from arithmetic.fusion.xgboost_model import train_step_calibrator
from backend.app.services.calibration_service import predict_step_confidence
from backend.app.services.fusion_service import fuse_confidence


def test_calibration_report_includes_discrimination_and_reliability():
    report = evaluate_calibration(
        [0.1, 0.8, 0.4, 0.6],
        [0, 1, 0, 1],
    )

    assert report["ece"] == pytest.approx(0.275)
    assert report["mce"] == pytest.approx(0.4)
    assert report["brier_score"] == pytest.approx(0.0925)
    assert report["auroc"] == pytest.approx(1.0)
    assert report["reliability_bins"]


def test_auroc_handles_tied_scores_and_single_class_labels():
    assert binary_auroc([0.5, 0.5], [0, 1]) == pytest.approx(0.5)
    assert binary_auroc([0.9, 0.8], [1, 1]) is None


def test_calibration_rejects_invalid_probabilities():
    with pytest.raises(ValueError, match="between 0 and 1"):
        maximum_calibration_error([1.2], [1])


def test_controlled_error_injection_records_the_source_step():
    result = inject_numeric_step_error(
        ["There are 5 bags.", "5 * 8 = 40 apples."],
        step_number=2,
    )

    assert result.steps == ["There are 5 bags.", "5 * 8 = 41 apples."]
    assert result.true_error_step == 2


def test_localization_metrics_only_score_known_wrong_answers():
    report = evaluate_localization(
        [
            {
                "final_answer_correct": False,
                "true_error_step": 2,
                "confidences": {1: 0.9, 2: 0.2, 3: 0.4},
            },
            {
                "final_answer_correct": True,
                "true_error_step": None,
                "confidences": {1: 0.2},
            },
        ]
    )

    assert report == {
        "evaluated_cases": 1,
        "top1_accuracy": 1.0,
        "top2_accuracy": 1.0,
    }


def test_fusion_weights_include_step_type_and_optional_token_signal():
    confidence = fuse_confidence(
        verification_score=0.5,
        consistency_score=0.7,
        step_type="arithmetic",
        token_probability=0.8,
    )

    assert confidence == pytest.approx(0.35 * 0.5 + 0.4 * 0.7 + 0.25 * 0.8)


def test_xgboost_calibrator_uses_grouped_holdout_and_loads(tmp_path):
    records = []
    for question_index in range(12):
        for correct in (0, 1):
            signal = 0.9 if correct else 0.2
            records.append(
                {
                    "question_id": f"question-{question_index}",
                    "step_correct": correct,
                    "features": {
                        "step_type": "arithmetic",
                        "verification_score": signal,
                        "consistency_score": signal,
                        "sample_agreement_score": signal,
                        "semantic_entropy": 1 - signal,
                        "mean_token_logprob": -0.1 if correct else -1.2,
                        "token_entropy": 1 - signal,
                    },
                }
            )

    model, report = train_step_calibrator(records, test_size=0.25)
    model_path = tmp_path / "step-calibrator.json"
    model.save_model(model_path)

    probability = predict_step_confidence(
        records[0]["features"],
        str(model_path),
    )

    assert report["train_questions"] + report["test_questions"] == 12
    assert set(report["train_question_ids"]).isdisjoint(report["test_question_ids"])
    assert report["auroc"] == pytest.approx(1.0)
    assert probability is not None
    assert 0 <= probability <= 1