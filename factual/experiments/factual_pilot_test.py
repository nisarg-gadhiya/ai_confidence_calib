import json
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
from factual.pipeline import process_factual


PILOT_SIZE = 100
DATASET_NAME = "mandarjoshi/trivia_qa"
DATASET_CONFIG = "rc.nocontext"
DATASET_SPLIT = "validation"
RESULT_PATH = Path(__file__).resolve().parent / "results" / "triviaqa_pilot_100.json"


def _load_samples() -> list[dict[str, Any]]:
    dataset = load_dataset(
        DATASET_NAME,
        DATASET_CONFIG,
        split=DATASET_SPLIT,
        streaming=True,
    )
    samples = list(islice(iter(dataset), PILOT_SIZE))
    if len(samples) < PILOT_SIZE:
        raise RuntimeError(
            f"TriviaQA validation split yielded {len(samples)} rows; "
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
                "selection": "First 100 rows from a streamed validation split.",
                "results": results,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _average_claim_value(
    results: list[dict[str, Any]],
    key: str,
) -> float | None:
    values = [
        claim[key]
        for result in results
        for step in result.get("pipeline_response", {}).get("steps", [])
        for claim in step.get("claims", [])
        if claim.get(key) is not None
    ]
    return mean(values) if values else None


def _format_average(value: float | None) -> str:
    return f"{value:.4f}" if value is not None else "N/A"


def main() -> None:
    if not settings.llm_api_key:
        raise RuntimeError("Set LLM_API_KEY in the repository-root .env before running the pilot.")

    print("=" * 40)
    print("TRIVIAQA FACTUAL PILOT")
    print("=" * 40)
    samples = _load_samples()
    results: list[dict[str, Any]] = []
    successful_results: list[dict[str, Any]] = []

    for index, sample in enumerate(samples, start=1):
        question = sample["question"]
        answer = sample.get("answer") or {}
        question_id = sample.get("question_id") or f"triviaqa-validation-{index:04d}"
        reference_answer = answer.get("value")
        reference_aliases = answer.get("aliases", [])
        print(f"\nQuestion {index}/{PILOT_SIZE}")
        print(f"Question ID: {question_id}")

        try:
            pipeline_response = process_factual(question)
            reasoning_steps = pipeline_response["steps"]
            result = {
                "question_id": question_id,
                "question": question,
                "reference_answer": reference_answer,
                "reference_aliases": reference_aliases,
                "generated_reasoning": "\n".join(
                    f"Step {step['step_id']}: {step['text']}"
                    for step in reasoning_steps
                ),
                "pipeline_response": pipeline_response,
            }
            successful_results.append(result)
        except Exception as error:
            result = {
                "question_id": question_id,
                "question": question,
                "reference_answer": reference_answer,
                "reference_aliases": reference_aliases,
                "error": {
                    "type": type(error).__name__,
                    "message": str(error),
                },
            }
            print(f"Question failed: {type(error).__name__}: {error}")

        results.append(result)
        _save_results(results)

    step_counts = [
        len(result["pipeline_response"]["steps"])
        for result in successful_results
    ]
    claims = [
        claim
        for result in successful_results
        for step in result["pipeline_response"]["steps"]
        for claim in step["claims"]
    ]
    source_count = sum(len(claim["sources"]) for claim in claims)
    confidence_values = [
        result["pipeline_response"]["answer_confidence"]
        for result in successful_results
        if result["pipeline_response"]["answer_confidence"] is not None
    ]

    print("\n" + "=" * 40)
    print("PILOT EXPERIMENT SUMMARY")
    print("=" * 40)
    print(f"Questions attempted: {len(results)}")
    print(f"Questions successful: {len(successful_results)}")
    print(f"Questions failed: {len(results) - len(successful_results)}")
    print(
        "Average steps/question: "
        + _format_average(mean(step_counts) if step_counts else None)
    )
    print(f"Factual claims assessed: {len(claims)}")
    print(f"Evidence sources retrieved: {source_count}")
    print(
        "Average answer confidence: "
        + _format_average(mean(confidence_values) if confidence_values else None)
    )
    print(
        "Average calibrated claim probability: "
        + _format_average(_average_claim_value(successful_results, "calibrated_probability"))
    )
    print("Answer accuracy: Not available; the factual pipeline does not return a final answer.")
    print("Total LLM/API calls: Not available from the existing inference service")
    print("Token/cost tracking not available")
    print(f"Results saved to: {RESULT_PATH}")
    print("=" * 40)


if __name__ == "__main__":
    main()
