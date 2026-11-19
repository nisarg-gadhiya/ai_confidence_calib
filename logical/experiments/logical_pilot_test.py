import json
import re
import sys
from itertools import islice
from pathlib import Path
from statistics import mean
from typing import Any

from datasets import load_dataset


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
for import_root in (REPOSITORY_ROOT, BACKEND_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from app.core.config import settings
from logical.pipeline import process_logical
from logical.premises.extractor import extract_target_statement
from logical.rules.extractor import parse_atom


PILOT_SIZE = 100
CONSISTENCY_SAMPLES = 5
DATASET_NAME = "tasksource/ruletaker"
DATASET_CONFIG = "default"
DATASET_SPLIT = "test"
RESULT_PATH = Path(__file__).resolve().parent / "results" / "ruletaker_pilot_100.json"
CLAIM_PATTERN = re.compile(
    r"^(.+?)\s+is\s+(not\s+)?(.+)$",
    re.IGNORECASE,
)


def _claim_as_question(claim: str) -> str | None:
    normalized = claim.strip().rstrip(".!?")
    match = CLAIM_PATTERN.fullmatch(normalized)
    if not match:
        return None

    subject, negation, predicate = match.groups()
    question = f"Is {subject.strip()} {'not ' if negation else ''}{predicate.strip()}?"
    target_text = extract_target_statement(question)
    return question if target_text and parse_atom(target_text) is not None else None


def _load_samples() -> list[dict[str, Any]]:
    dataset = load_dataset(
        DATASET_NAME,
        DATASET_CONFIG,
        split=DATASET_SPLIT,
        streaming=True,
    )
    samples = []
    for dataset_index, row in enumerate(dataset):
        question = _claim_as_question(str(row.get("question", "")))
        if question is None:
            continue
        samples.append(
            {
                "dataset_index": dataset_index,
                "question_id": f"ruletaker-test-{dataset_index:06d}",
                "context": row["context"],
                "dataset_claim": row["question"],
                "question": question,
                "reference_label": row["label"],
                "config": row.get("config"),
            }
        )
        if len(samples) == PILOT_SIZE:
            break

    if len(samples) < PILOT_SIZE:
        raise RuntimeError(
            f"Found only {len(samples)} parser-compatible RuleTaker rows; "
            f"the pilot requires {PILOT_SIZE}."
        )
    return samples


def _save_results(results: list[dict[str, Any]]) -> None:
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(
        json.dumps(
            {
                "dataset": DATASET_NAME,
                "config": DATASET_CONFIG,
                "split": DATASET_SPLIT,
                "questions_selected": PILOT_SIZE,
                "selection": (
                    "First 100 rows whose claim can be converted to a supported "
                    "yes/no query."
                ),
                "consistency_samples_per_step": CONSISTENCY_SAMPLES,
                "results": results,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _target_verdict(inference_response: dict[str, Any]) -> str | None:
    for step in reversed(inference_response.get("steps", [])):
        for claim in step.get("claims", []):
            if claim.get("essential"):
                return claim.get("verification", {}).get("verdict")
    return None


def _average_claim_value(
    results: list[dict[str, Any]],
    key: str,
) -> float | None:
    values = [
        claim[key]
        for result in results
        for step in result.get("inference_response", {}).get("steps", [])
        for claim in step.get("claims", [])
        if claim.get(key) is not None
    ]
    return mean(values) if values else None


def _average_logical_validity(results: list[dict[str, Any]]) -> float | None:
    values = [
        claim["verification"]["logical_validity_score"]
        for result in results
        for step in result.get("inference_response", {}).get("steps", [])
        for claim in step.get("claims", [])
    ]
    return mean(values) if values else None


def _format_average(value: float | None) -> str:
    return f"{value:.4f}" if value is not None else "N/A"


def main() -> None:
    if not settings.llm_api_key:
        raise RuntimeError("Set LLM_API_KEY in the repository-root .env before running the pilot.")

    print("=" * 40)
    print("RULETAKER LOGICAL PILOT")
    print("=" * 40)
    samples = _load_samples()
    results: list[dict[str, Any]] = []
    successful_results: list[dict[str, Any]] = []

    for index, sample in enumerate(samples, start=1):
        model_input = f"{sample['context'].strip()} {sample['question']}"
        print(f"\nQuestion {index}/{PILOT_SIZE}")
        print(f"Question ID: {sample['question_id']}")

        try:
            inference_response = process_logical(
                model_input,
                num_consistency_samples=CONSISTENCY_SAMPLES,
            )
            target_verdict = _target_verdict(inference_response)
            predicted_label = (
                "entailment"
                if target_verdict == "ENTAILED"
                else "not entailment"
                if target_verdict in {"CONTRADICTED", "UNKNOWN"}
                else None
            )
            expected_label = sample["reference_label"].strip().lower()
            result = {
                **sample,
                "model_input": model_input,
                "predicted_verdict": target_verdict,
                "predicted_label": predicted_label,
                "is_correct": predicted_label == expected_label,
                "final_answer": inference_response.get("final_answer"),
                "inference_response": inference_response,
            }
            successful_results.append(result)
        except Exception as error:
            result = {
                **sample,
                "model_input": model_input,
                "error": {
                    "type": type(error).__name__,
                    "message": str(error),
                },
            }
            print(f"Question failed: {type(error).__name__}: {error}")

        results.append(result)
        _save_results(results)

    labeled_results = [
        result
        for result in successful_results
        if result.get("is_correct") is not None
    ]
    step_counts = [
        len(result["inference_response"]["steps"])
        for result in successful_results
    ]
    accuracy = (
        sum(result["is_correct"] for result in labeled_results) / len(labeled_results)
        if labeled_results
        else None
    )

    print("\n" + "=" * 40)
    print("PILOT EXPERIMENT SUMMARY")
    print("=" * 40)
    print(f"Questions attempted: {len(results)}")
    print(f"Questions successful: {len(successful_results)}")
    print(f"Questions failed: {len(results) - len(successful_results)}")
    print(f"Binary label accuracy: {_format_average(accuracy)}")
    print(
        "Average steps/question: "
        + _format_average(mean(step_counts) if step_counts else None)
    )
    print(
        "Average calibrated claim confidence: "
        + _format_average(_average_claim_value(successful_results, "calibrated_probability"))
    )
    print(
        "Average logical validity: "
        + _format_average(_average_logical_validity(successful_results))
    )
    print("Total LLM/API calls: Not available from the existing inference service")
    print("Token/cost tracking not available")
    print(f"Results saved to: {RESULT_PATH}")
    print("=" * 40)


if __name__ == "__main__":
    main()
