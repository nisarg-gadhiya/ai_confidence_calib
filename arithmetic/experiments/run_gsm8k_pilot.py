import json
import sys
from pathlib import Path
from statistics import mean
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
for import_root in (REPOSITORY_ROOT, BACKEND_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from backend.app.api.routes.inference import InferenceRequest, run_inference
from arithmetic.data.download_gsm8k import load_gsm8k
from arithmetic.data.preprocess import parse_gsm8k_example


PILOT_SIZE = 5
CONSISTENCY_SAMPLES = 5
RESULT_PATH = Path(__file__).resolve().parent / "results" / "gsm8k_pilot_5.json"


def _save_results(results: list[dict[str, Any]]) -> None:
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(
        json.dumps(
            {
                "dataset": "openai/gsm8k",
                "split": "test",
                "questions_selected": PILOT_SIZE,
                "consistency_samples_per_step": CONSISTENCY_SAMPLES,
                "results": results,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _build_result(
    question_id: str,
    question: str,
    reference_answer: str,
    inference_response: Any,
) -> dict[str, Any]:
    response_data = inference_response.model_dump(mode="json")
    reasoning_steps = response_data["reasoning"]
    generated_reasoning = "\n".join(
        f"Step {step['step_number']}: {step['step_text']}"
        for step in reasoning_steps
    )
    return {
        "question_id": question_id,
        "question": question,
        "reference_answer": reference_answer,
        "generated_reasoning": generated_reasoning,
        "reasoning_steps": reasoning_steps,
        "predicted_error_step": response_data["predicted_error_step"],
        "final_answer": response_data["final_answer"],
        "final_answer_confidence": response_data["final_answer_confidence"],
        "confidence_method": response_data["confidence_method"],
        "inference_response": response_data,
    }


def _average_step_value(
    results: list[dict[str, Any]],
    key: str,
) -> float | None:
    values = [
        step[key]
        for result in results
        for step in result.get("reasoning_steps", [])
        if step.get(key) is not None
    ]
    return mean(values) if values else None


def _format_average(value: float | None) -> str:
    return f"{value:.4f}" if value is not None else "N/A"


def main() -> None:
    print("=" * 40)
    print("GSM8K PILOT EXPERIMENT")
    print("=" * 40)

    dataset = load_gsm8k()
    test_split = dataset["test"]
    if len(test_split) < PILOT_SIZE:
        raise RuntimeError(
            f"GSM8K test split has {len(test_split)} rows; "
            f"the pilot requires exactly {PILOT_SIZE}."
        )
    samples = test_split.select(range(PILOT_SIZE))

    results: list[dict[str, Any]] = []
    successful_results: list[dict[str, Any]] = []

    for index, sample in enumerate(samples, start=1):
        question_id = f"gsm8k-test-{index:04d}"
        question = sample.get("question", "")
        reference_answer = sample.get("answer", "")
        print(f"\nQuestion {index}/{PILOT_SIZE}")
        print(f"Question ID: {question_id}")

        try:
            example = parse_gsm8k_example(sample, question_id=question_id)
            question = example.question
            reference_answer = example.reference_answer
            print("Pipeline stages (handled by the existing inference endpoint):")
            print("  Generating reasoning and parsing steps...")
            print("  Running per-step verification...")
            print(
                f"  Running K={CONSISTENCY_SAMPLES} "
                "fixed-prefix consistency sampling..."
            )
            print("  Calculating confidence and localizing error...")
            inference_response = run_inference(
                InferenceRequest(
                    question=question,
                    num_consistency_samples=CONSISTENCY_SAMPLES,
                )
            )
            result = _build_result(
                question_id,
                question,
                reference_answer,
                inference_response,
            )
            successful_results.append(result)
        except Exception as error:
            result = {
                "question_id": question_id,
                "question": question,
                "reference_answer": reference_answer,
                "error": {
                    "type": type(error).__name__,
                    "message": str(error),
                },
            }
            print(f"Question failed: {type(error).__name__}: {error}")

        results.append(result)
        _save_results(results)

    step_count = [
        len(result["reasoning_steps"])
        for result in successful_results
    ]
    print("\n" + "=" * 40)
    print("PILOT EXPERIMENT SUMMARY")
    print("=" * 40)
    print(f"Questions attempted: {len(results)}")
    print(f"Questions successful: {len(successful_results)}")
    print(f"Questions failed: {len(results) - len(successful_results)}")
    print(
        "Average steps/question: "
        + _format_average(mean(step_count) if step_count else None)
    )
    print(
        "Average step confidence: "
        + _format_average(_average_step_value(successful_results, "fused_confidence"))
    )
    print(
        "Average verification score: "
        + _format_average(_average_step_value(successful_results, "verification_score"))
    )
    print(
        "Average consistency score: "
        + _format_average(_average_step_value(successful_results, "consistency_score"))
    )
    print("Total LLM/API calls: Not available from the existing inference service")
    print("Total input tokens: Not available")
    print("Total output tokens: Not available")
    print("Total tokens: Not available")
    print("Cost: Not available")
    print("Token/cost tracking not available")
    print(f"Results saved to: {RESULT_PATH}")
    print("=" * 40)


if __name__ == "__main__":
    main()