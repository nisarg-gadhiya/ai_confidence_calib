import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.api.routes import inference
from app.api.schemas.reasoning import InferenceRequest
from app.services.llm_service import (
    GeneratedStep,
    LLMResponse,
    StepAssessment,
    StepContinuation,
)
from factual import pipeline as factual_pipeline
from gateway.schemas import QuestionClassification
from gateway.router import LogicalPipelineNotImplementedError, route_question


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("What is 35% of 800?", "arithmetic"),
        ("A train travels 240 km in 4 hours. What is its speed?", "arithmetic"),
        ("John is taller than Mike. Mike is taller than David. Who is shortest?", "logical"),
        ("If A is greater than B and B is greater than C, which is smallest?", "logical"),
        ("What is the capital of Japan?", "factual"),
        ("Who wrote Romeo and Juliet?", "factual"),
    ],
)
def test_question_classification_schema_accepts_expected_categories(question, expected):
    payload = {"category": expected}
    result = QuestionClassification.model_validate(payload)
    assert result.category == expected


def test_question_classification_schema_rejects_unknown_category():
    with pytest.raises(ValidationError):
        QuestionClassification.model_validate({"category": "unknown"})


def test_route_question_returns_existing_inference_result_unchanged(monkeypatch):
    question = "  What is 25% of 400?  "
    sample_counts = []

    class FakeLLMService:
        def __init__(self, **_kwargs):
            pass

        def generate_reasoning(self, received_question):
            assert received_question == question
            return LLMResponse(
                text="Step 1: Calculate 25% of 400.",
                final_answer="100",
                steps=[GeneratedStep(1, "Calculate 25% of 400.", "arithmetic")],
            )

        def generate_step_continuations(
            self, _question, _preceding_steps, next_step_number, num_samples
        ):
            assert next_step_number == 1
            sample_counts.append(num_samples)
            return [StepContinuation(text="Calculate to get 100.") for _ in range(num_samples)]

        def verify_step(self, _question, step, _preceding_steps, samples):
            return StepAssessment(
                p_true=0.9,
                rationale="The calculation is supported.",
                step_type=step.step_type,
                sample_cluster_ids=[0] * len(samples),
            )

    monkeypatch.setattr(inference, "LLMService", FakeLLMService)
    request = InferenceRequest(question=question, num_consistency_samples=3)
    direct_result = inference.run_inference(request)
    monkeypatch.setattr("gateway.router.classify_question", lambda value: "arithmetic")
    monkeypatch.setattr("gateway.router.run_inference", inference.run_inference)

    gateway_result = route_question(question, num_consistency_samples=3)

    assert gateway_result == direct_result
    assert gateway_result.question == question
    assert sample_counts == [3, 3]


def test_route_question_returns_factual_pipeline_result_unchanged(monkeypatch):
    question = "What is the capital of France?"
    monkeypatch.setattr(
        factual_pipeline,
        "generate_reasoning_steps",
        lambda _question: ["Paris is the capital of France."],
    )
    monkeypatch.setattr(factual_pipeline, "get_factual_llm_service", lambda: None)
    monkeypatch.setattr(factual_pipeline, "search_sources", lambda *_args: [])
    direct_result = factual_pipeline.process_factual(question)
    monkeypatch.setattr("gateway.router.classify_question", lambda value: "factual")
    monkeypatch.setattr("gateway.router.process_factual", factual_pipeline.process_factual)

    gateway_result = route_question(question)

    assert gateway_result == direct_result
    assert gateway_result["question"] == question


def test_gateway_ask_endpoint_returns_pipeline_payload_without_wrapper(monkeypatch):
    question = "What is the capital of France?"
    direct_result = {"question": question, "steps": [], "answer_confidence": 0.8}
    monkeypatch.setattr("gateway.router.classify_question", lambda _question: "factual")
    monkeypatch.setattr("gateway.router.process_factual", lambda _question: direct_result)

    response = TestClient(app).post("/api/ask", json={"question": question})

    assert response.status_code == 200
    assert response.json() == direct_result


def test_gateway_arithmetic_response_matches_existing_inference_endpoint(monkeypatch):
    question = "What is 25% of 400?"

    class FakeLLMService:
        def __init__(self, **_kwargs):
            pass

        def generate_reasoning(self, received_question):
            assert received_question == question
            return LLMResponse(
                text="",
                final_answer="100",
                steps=[],
            )

    monkeypatch.setattr(inference, "LLMService", FakeLLMService)
    monkeypatch.setattr("gateway.router.classify_question", lambda _question: "arithmetic")
    client = TestClient(app)
    payload = {"question": question, "num_consistency_samples": 3}

    direct_response = inference.run_inference(InferenceRequest(**payload))
    gateway_response = client.post("/api/ask", json=payload)

    assert gateway_response.status_code == 200
    assert gateway_response.json() == direct_response.model_dump()


def test_direct_inference_and_factual_endpoints_are_unmounted():
    client = TestClient(app)

    assert client.post(
        "/api/inference",
        json={"question": "What is 2 + 2?"},
    ).status_code == 404
    assert client.post(
        "/api/factual",
        json={"question": "What is the capital of France?"},
    ).status_code == 404
    assert client.post(
        "/api/classify",
        json={"question": "What is the capital of France?"},
    ).status_code == 404


def test_logical_category_returns_not_implemented(monkeypatch):
    monkeypatch.setattr("gateway.router.classify_question", lambda _question: "logical")

    with pytest.raises(LogicalPipelineNotImplementedError):
        route_question("Who is the shortest?")

    response = TestClient(app).post(
        "/api/ask",
        json={"question": "Who is the shortest?"},
    )
    assert response.status_code == 501
    assert response.json() == {
        "detail": "The logical reasoning pipeline is not implemented."
    }
