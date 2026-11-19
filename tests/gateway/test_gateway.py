import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.api.routes import gateway as gateway_api, inference
from app.api.schemas.reasoning import InferenceResponse, ReasoningStepResponse
from app.services import calibration_store
from app.api.schemas.reasoning import InferenceRequest
from app.services.llm_service import (
    GeneratedStep,
    LLMResponse,
    StepAssessment,
    StepContinuation,
)
from factual import pipeline as factual_pipeline
from factual.generation.reasoning import FactualGeneration
from gateway.schemas import QuestionClassification
from gateway.router import route_question


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
        "generate_factual_response",
        lambda _question: FactualGeneration(
            ["Paris is the capital of France."],
            None,
        ),
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
    monkeypatch.setattr(gateway_api, "save_calibration_run", lambda *_args: None)

    response = TestClient(app).post("/api/ask", json={"question": question})

    assert response.status_code == 200
    assert response.json() == direct_result


def test_gateway_persists_step_calibration_to_json(monkeypatch, tmp_path):
    question = "All cats are mammals. Tom is a cat. Is Tom a mammal?"
    response_data = {
        "question": question,
        "final_answer": "Yes. Tom is a mammal.",
        "answer_confidence": 0.82,
        "rules": [{"rule_id": "r1"}],
        "steps": [
            {
                "step_id": 1,
                "text": "Tom is a mammal.",
                "sample_count": 5,
                "claims": [
                    {
                        "claim_id": "c1_1",
                        "text": "Tom is a mammal.",
                        "essential": True,
                        "verification": {
                            "verdict": "ENTAILED",
                            "logical_validity_score": 1.0,
                        },
                        "self_verification_score": 0.9,
                        "consistency_score": 0.8,
                        "calibrated_probability": 0.82,
                    }
                ],
            }
        ],
    }
    store_path = tmp_path / "calibration_runs.json"
    monkeypatch.setattr(calibration_store, "CALIBRATION_STORE_PATH", store_path)
    monkeypatch.setattr("gateway.router.classify_question", lambda _question: "logical")
    monkeypatch.setattr("gateway.router.process_logical", lambda *_args: response_data)

    response = TestClient(app).post("/api/ask", json={"question": question})

    assert response.status_code == 200
    records = json.loads(store_path.read_text(encoding="utf-8"))
    assert len(records) == 1
    assert records[0]["category"] == "logical"
    assert records[0]["answer"] == "Yes. Tom is a mammal."
    assert records[0]["confidence"] == 0.82
    assert records[0]["steps"][0]["calibrated_probability"] == 0.82
    assert records[0]["pipeline_output"] == response_data


def test_calibration_store_preserves_factual_output_and_source_links(monkeypatch, tmp_path):
    question = "What is the capital of Australia?"
    response_data = {
        "question": question,
        "final_answer": "Canberra is the capital of Australia.",
        "answer_confidence": 0.91,
        "steps": [
            {
                "step_id": 1,
                "text": "Canberra is the capital of Australia.",
                "claims": [
                    {
                        "claim_id": "c1_1",
                        "text": "Canberra is the capital of Australia.",
                        "essential": True,
                        "verification": {"verdict": "SUPPORT", "evidence_score": 1.0},
                        "sources": [
                            {
                                "source_id": "s1",
                                "title": "Australian Government",
                                "url": "https://www.australia.gov.au/capital",
                                "domain": "australia.gov.au",
                                "text": "Canberra is the capital of Australia.",
                            }
                        ],
                    }
                ],
            }
        ],
    }
    store_path = tmp_path / "calibration_runs.json"
    monkeypatch.setattr(calibration_store, "CALIBRATION_STORE_PATH", store_path)

    calibration_store.save_calibration_run(question, response_data)

    record = json.loads(store_path.read_text(encoding="utf-8"))[0]
    assert record["category"] == "factual"
    assert record["pipeline_output"] == response_data
    assert record["steps"][0]["sources"] == [
        {
            "source_id": "s1",
            "title": "Australian Government",
            "url": "https://www.australia.gov.au/capital",
            "domain": "australia.gov.au",
        }
    ]


def test_calibration_store_serializes_arithmetic_response(monkeypatch, tmp_path):
    store_path = tmp_path / "calibration_runs.json"
    monkeypatch.setattr(calibration_store, "CALIBRATION_STORE_PATH", store_path)
    response = InferenceResponse(
        question="What is 2 + 2?",
        reasoning=[
            ReasoningStepResponse(
                step_number=1,
                step_text="Add 2 and 2.",
                step_type="arithmetic",
                verification_score=0.9,
                consistency_score=0.8,
                fused_confidence=0.85,
                sample_count=5,
            )
        ],
        final_answer="4",
        final_answer_confidence=0.85,
    )

    calibration_store.save_calibration_run(response.question, response)

    records = json.loads(store_path.read_text(encoding="utf-8"))
    assert records[0]["category"] == "arithmetic"
    assert records[0]["answer"] == "4"
    assert records[0]["steps"][0]["fused_confidence"] == 0.85


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
    monkeypatch.setattr(gateway_api, "save_calibration_run", lambda *_args: None)
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
    assert client.post(
        "/api/questions",
        json={"question_text": "What is the capital of France?"},
    ).status_code == 404
    assert client.get("/api/questions/1").status_code == 404


def test_logical_category_routes_to_logical_pipeline(monkeypatch):
    expected = {"question": "Who is the shortest?", "steps": []}
    monkeypatch.setattr("gateway.router.classify_question", lambda _question: "logical")
    monkeypatch.setattr("gateway.router.process_logical", lambda question, _samples: expected)

    result = route_question("Who is the shortest?", num_consistency_samples=3)

    assert result is expected
    monkeypatch.setattr(gateway_api, "save_calibration_run", lambda *_args: None)
    response = TestClient(app).post(
        "/api/ask",
        json={"question": "Who is the shortest?", "num_consistency_samples": 3},
    )
    assert response.status_code == 200
    assert response.json() == expected
