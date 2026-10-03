import pytest
from fastapi.testclient import TestClient

from app.main import app
from factual.answer_confidence import calculate_answer_confidence
from factual.pipeline import process_factual
from factual.decomposition.claim_extractor import extract_claims
from factual.retrieval.source_reliability import estimate_source_reliability
from factual.retrieval.reliability_filter import filter_sources
from factual.retrieval.source_search import search_sources
from factual.verification.claim_evidence import verify_claim_against_evidence
from factual.signals.evidence_score import aggregate_evidence_score
from factual.calibration.fusion import fuse_step_signals
from factual.evaluation.localization import localize_riskiest_step


def test_claim_extraction_creates_atomic_claims():
    steps = [
        {
            "step_id": 1,
            "text": "Canberra is the capital of Australia, and Australia is a country in Oceania.",
        }
    ]

    claims = extract_claims(steps)

    assert [claim["claim_text"] for claim in claims] == [
        "Canberra is the capital of Australia.",
        "Australia is a country in Oceania.",
    ]


def test_source_reliability_estimation_uses_configured_policy():
    source = {
        "source_id": "s1",
        "domain": "www.abc.net.au",
        "source_type": "news",
        "title": "Australia capital",
    }

    score = estimate_source_reliability(source)

    assert 0.0 <= score <= 1.0
    assert score > 0.5


def test_reliability_filter_keeps_downweights_and_rejects():
    sources = [
        {"source_id": "keep", "domain": "www.officialaustralia.gov.au", "source_type": "government", "title": "Official government page", "retrieval_score": 0.9},
        {"source_id": "down_weight", "domain": "www.exampleblog.com", "source_type": "blog", "title": "Blog post", "retrieval_score": 0.7},
        {"source_id": "reject", "domain": "unknown-site.net", "source_type": "general", "title": "Low trust", "retrieval_score": 0.1},
    ]

    filtered = filter_sources(sources)

    assert {item["source_id"]: item["status"] for item in filtered} == {
        "keep": "KEEP",
        "down_weight": "DOWN_WEIGHT",
        "reject": "REJECT",
    }


def test_verification_support_and_contradict_and_unknown():
    support = verify_claim_against_evidence(
        "Canberra is the capital of Australia.",
        "Canberra is the capital city of Australia.",
    )
    contradict = verify_claim_against_evidence(
        "Canberra is the capital of Australia.",
        "Sydney is the capital of Australia.",
    )
    unknown = verify_claim_against_evidence(
        "Canberra is the capital of Australia.",
        "Australia is located in the Southern Hemisphere.",
    )

    assert support == "SUPPORT"
    assert contradict == "CONTRADICT"
    assert unknown == "UNKNOWN"


def test_evidence_aggregation_weighted_support_and_contradiction():
    aggregated = aggregate_evidence_score(
        support_evidence=[
            {"source_reliability": 0.95, "relevance_score": 0.9},
            {"source_reliability": 0.9, "relevance_score": 0.8},
        ],
        contradict_evidence=[
            {"source_reliability": 0.7, "relevance_score": 0.75},
        ],
        unknown_evidence=[
            {"source_reliability": 0.5, "relevance_score": 0.4},
        ],
    )

    assert 0.0 <= aggregated <= 1.0
    assert aggregated > 0.5


def test_confidence_fusion_blends_signals():
    fused = fuse_step_signals(
        self_verification_score=0.8,
        consistency_score=0.9,
        evidence_score=0.7,
        weights={"self_verification": 0.4, "consistency": 0.3, "evidence": 0.3},
    )

    assert 0.0 <= fused <= 1.0
    assert fused > 0.7


def test_error_localization_uses_lowest_probability_step():
    steps = [
        {"step_id": 1, "calibrated_probability": 0.96},
        {"step_id": 2, "calibrated_probability": 0.41},
        {"step_id": 3, "calibrated_probability": 0.87},
    ]

    assert localize_riskiest_step(steps) == 2


def test_factual_pipeline_processes_question_without_mutating_input(monkeypatch):
    import factual.pipeline as factual_pipeline

    _stub_factual_runtime(monkeypatch, factual_pipeline)
    question = "What is the capital of Australia?"
    result = process_factual(question)

    assert result["question"] == question
    assert "steps" in result
    assert isinstance(result["steps"], list)
    assert result["steps"]


def _stub_factual_runtime(monkeypatch, factual_pipeline):
    monkeypatch.setattr(
        factual_pipeline,
        "generate_reasoning_steps",
        lambda _question: ["Canberra is the capital of Australia."],
    )
    monkeypatch.setattr(factual_pipeline, "get_factual_llm_service", lambda: None)
    monkeypatch.setattr(factual_pipeline, "search_sources", lambda *_args: [])


def test_source_search_maps_live_citations_to_source_records(monkeypatch):
    class FakeSearchService:
        def search_web(self, query):
            assert "Canberra is the capital of Australia." in query
            return [
                {
                    "title": "Australian Government",
                    "url": "https://www.australia.gov.au/capital",
                    "text": "Canberra is the capital of Australia.",
                }
            ]

    monkeypatch.setattr(
        "factual.retrieval.source_search.get_factual_llm_service",
        lambda: FakeSearchService(),
    )

    sources = search_sources(
        "Canberra is the capital of Australia.",
        "What is the capital of Australia?",
    )

    assert len(sources) == 1
    assert sources[0]["url"] == "https://www.australia.gov.au/capital"
    assert sources[0]["domain"] == "australia.gov.au"
    assert sources[0]["source_type"] == "government"
    assert sources[0]["retrieval_score"] > 0.0


def test_factual_pipeline_uses_independent_source_verdicts(monkeypatch):
    import factual.pipeline as factual_pipeline

    class FakeVerifier:
        def assess_factual_claim(self, question, claim_text, evidence):
            assert question == "What is the capital of Australia?"
            assert claim_text == "Canberra is the capital of Australia."
            assert len(evidence) == 2
            return {
                "confidence": 0.9,
                "essential": True,
                "source_assessments": [
                    {"source_id": "source_a", "verdict": "SUPPORT"},
                    {"source_id": "source_b", "verdict": "SUPPORT"},
                ],
            }

    sources = [
        {
            "source_id": source_id,
            "title": "Capital reference",
            "url": f"https://example.gov.au/{source_id}",
            "domain": "example.gov.au",
            "source_type": "government",
            "text": "Canberra is the capital of Australia.",
            "text_origin": "citation_linked_model_summary",
            "retrieval_score": 1.0,
        }
        for source_id in ("source_a", "source_b")
    ]
    monkeypatch.setattr(
        factual_pipeline,
        "generate_reasoning_steps",
        lambda _question: ["Canberra is the capital of Australia."],
    )
    monkeypatch.setattr(factual_pipeline, "get_factual_llm_service", lambda: FakeVerifier())
    monkeypatch.setattr(factual_pipeline, "search_sources", lambda *_args: sources)

    result = process_factual("What is the capital of Australia?")
    claim = result["steps"][0]["claims"][0]

    assert claim["essential"] is True
    assert claim["consistency_score"] == 1.0
    assert claim["verification"]["verdict"] == "SUPPORT"
    assert claim["sources"][0]["text_origin"] == "citation_linked_model_summary"
    assert [item["url"] for item in claim["sources"]] == [
        "https://example.gov.au/source_a",
        "https://example.gov.au/source_b",
    ]
    assert result["answer_confidence"] is not None
    assert result["calibration_status"] == "fixed_sigmoid_not_empirically_calibrated"


def test_calculate_answer_confidence_uses_geometric_mean_for_essential_claims():
    claims = [
        {"claim_id": "c1", "essential": True, "calibrated_probability": 0.92},
        {"claim_id": "c2", "essential": True, "calibrated_probability": 0.86},
        {"claim_id": "c3", "essential": True, "calibrated_probability": 0.74},
        {"claim_id": "c4", "essential": True, "calibrated_probability": 0.91},
        {"claim_id": "c5", "essential": False, "calibrated_probability": 0.1},
    ]

    assert calculate_answer_confidence(claims) == pytest.approx(0.854, abs=1e-3)


def test_calculate_answer_confidence_handles_simple_cases():
    assert calculate_answer_confidence([
        {"claim_id": "c1", "essential": True, "calibrated_probability": 0.9},
        {"claim_id": "c2", "essential": True, "calibrated_probability": 0.9},
        {"claim_id": "c3", "essential": True, "calibrated_probability": 0.9},
    ]) == pytest.approx(0.9)

    assert calculate_answer_confidence([
        {"claim_id": "c1", "essential": True, "calibrated_probability": 1.0},
        {"claim_id": "c2", "essential": True, "calibrated_probability": 1.0},
        {"claim_id": "c3", "essential": True, "calibrated_probability": 1.0},
    ]) == pytest.approx(1.0)

    assert calculate_answer_confidence([
        {"claim_id": "c1", "essential": True, "calibrated_probability": 0.0},
        {"claim_id": "c2", "essential": True, "calibrated_probability": 0.9},
        {"claim_id": "c3", "essential": True, "calibrated_probability": 0.8},
    ]) == 0.0

    assert calculate_answer_confidence([
        {"claim_id": "c1", "essential": True, "calibrated_probability": 0.83},
    ]) == pytest.approx(0.83)

    assert calculate_answer_confidence([
        {"claim_id": "c1", "essential": False, "calibrated_probability": 0.1},
    ]) is None


def test_factual_http_endpoint_is_not_mounted():
    client = TestClient(app)
    response = client.post("/api/factual", json={"question": "What is the capital of Australia?"})

    assert response.status_code == 404
