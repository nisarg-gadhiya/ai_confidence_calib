from collections.abc import Sequence

from sklearn.model_selection import GroupShuffleSplit

from backend.app.services.calibration_features import encode_feature_rows
from ml.evaluation.calibration import evaluate_calibration


def train_step_calibrator(
	records: Sequence[dict],
	test_size: float = 0.25,
	random_state: int = 42,
):
	if len(records) < 4:
		raise ValueError("At least four labeled step records are required")

	labels = [int(record["step_correct"]) for record in records]
	groups = [str(record["question_id"]) for record in records]
	if set(labels) != {0, 1}:
		raise ValueError("Training data must contain both correct and incorrect steps")
	if any(not group for group in groups):
		raise ValueError("Every record must include a question_id for grouped splitting")

	feature_rows = [record["features"] for record in records]
	matrix = encode_feature_rows(feature_rows)
	splitter = GroupShuffleSplit(
		n_splits=50,
		test_size=test_size,
		random_state=random_state,
	)
	split = next(
		(
			(train_indices, test_indices)
			for train_indices, test_indices in splitter.split(matrix, labels, groups)
			if set(labels[index] for index in train_indices) == {0, 1}
			and set(labels[index] for index in test_indices) == {0, 1}
		),
		None,
	)
	if split is None:
		raise ValueError(
			"Could not create a question-grouped split containing both labels "
			"in train and test; add more labeled questions."
		)

	train_indices, test_indices = split
	from xgboost import XGBClassifier

	model = XGBClassifier(
		n_estimators=160,
		max_depth=3,
		learning_rate=0.04,
		subsample=0.85,
		colsample_bytree=0.85,
		reg_lambda=2.0,
		eval_metric="logloss",
		n_jobs=1,
		random_state=random_state,
	)
	model.fit(
		[matrix[index] for index in train_indices],
		[labels[index] for index in train_indices],
	)
	probabilities = model.predict_proba(
		[matrix[index] for index in test_indices]
	)[:, 1].tolist()
	test_labels = [labels[index] for index in test_indices]
	report = evaluate_calibration(probabilities, test_labels)
	train_question_ids = sorted({groups[index] for index in train_indices})
	test_question_ids = sorted({groups[index] for index in test_indices})
	report["train_questions"] = len(train_question_ids)
	report["test_questions"] = len(test_question_ids)
	report["train_question_ids"] = train_question_ids
	report["test_question_ids"] = test_question_ids
	report["train_steps"] = len(train_indices)
	report["test_steps"] = len(test_indices)
	return model, report
