from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from factual.answer_confidence import calculate_answer_confidence
from factual.generation.reasoning import FactualGeneration, generate_factual_response
from factual.pipeline import process_factual
from factual.decomposition.claim_extractor import extract_claims
from factual.retrieval.source_reliability import classify_source, estimate_source_reliability
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


def test_claim_extraction_keeps_coordinated_lists_together():
    claims = extract_claims(
        [{
            "step_id": 3,
            "text": "An LSTM unit consists of a cell state, input gate, forget gate, and output gate.",
        }]
    )

    assert [claim["claim_text"] for claim in claims] == [
        "An LSTM unit consists of a cell state, input gate, forget gate, and output gate."
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


@pytest.mark.parametrize(
    ("domain", "source_type", "expected_status"),
    [
        ("astrobiology.nasa.gov", "general", "KEEP"),
        ("mext.go.jp", "general", "KEEP"),
        ("www.ox.ac.uk", "general", "KEEP"),
        ("news.bbc.co.uk", "general", "KEEP"),
        ("en.wikipedia.org", "general", "KEEP"),
        ("developer.nvidia.com", "general", "KEEP"),
        ("world-capitals.org", "general", "DOWN_WEIGHT"),
        ("medium.com", "general", "DOWN_WEIGHT"),
        ("reddit.com", "general", "REJECT"),
        ("youtube.com", "general", "REJECT"),
    ],
)
def test_source_reliability_tiers_land_in_expected_bands(domain, source_type, expected_status):
    [filtered] = filter_sources([{"source_id": "s", "domain": domain, "source_type": source_type}])

    assert filtered["status"] == expected_status


def test_source_reliability_matches_domains_on_dot_boundaries():
    assert classify_source({"domain": "news.bbc.co.uk"})[0] == "wire_news"
    assert classify_source({"domain": "notbbc.co.uk"})[0] == "general"
    # "ent" / "gov" substrings must not grant official status.
    assert estimate_source_reliability({"domain": "entertainment.com"}) < 0.75
    assert estimate_source_reliability({"domain": "lovegov.com"}) < 0.75


def test_source_reliability_ranks_tiers_in_order():
    scores = [
        estimate_source_reliability({"domain": domain})
        for domain in ["nasa.gov", "nature.com", "britannica.com", "reuters.com", "cnn.com", "example.com", "medium.com", "reddit.com"]
    ]

    assert scores == sorted(scores, reverse=True)
    assert len(set(scores)) == len(scores)


def test_blog_source_type_caps_reliability_on_trusted_hosts():
    assert estimate_source_reliability({"domain": "en.wikipedia.org", "source_type": "blog"}) == 0.48


def test_reliability_filter_keeps_downweights_and_rejects():
    sources = [
        {"source_id": "keep", "domain": "www.officialaustralia.gov.au", "source_type": "government", "title": "Official government page", "retrieval_score": 0.9},
        {"source_id": "down_weight", "domain": "www.exampleblog.com", "source_type": "blog", "title": "Blog post", "retrieval_score": 0.7},
        {"source_id": "reject", "domain": "unknown-site.net", "source_type": "general", "title": "Low trust", "retrieval_score": 0.9, "reliability_score": 0.1},
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
    assert result["final_answer"] == (
        "The answer could not be verified from the available evidence."
    )
    assert "steps" in result
    assert isinstance(result["steps"], list)
    assert result["steps"]


def _stub_factual_runtime(monkeypatch, factual_pipeline):
    monkeypatch.setattr(
        factual_pipeline,
        "generate_factual_response",
        lambda _question: FactualGeneration(
            ["Canberra is the capital of Australia."],
            None,
        ),
    )
    monkeypatch.setattr(factual_pipeline, "get_factual_llm_service", lambda: None)
    monkeypatch.setattr(factual_pipeline, "search_sources", lambda *_args: [])


def test_factual_answer_uses_supported_final_claim_after_unknown_intermediate():
    import factual.pipeline as factual_pipeline

    claims = [
        {
            "essential": True,
            "text": "Determine who succeeded Arthur Balfour.",
            "verification": {"verdict": "UNKNOWN"},
        },
        {
            "essential": True,
            "text": "Henry Campbell-Bannerman succeeded Arthur Balfour.",
            "verification": {"verdict": "SUPPORT"},
        },
        {
            "essential": True,
            "text": "He served as Prime Minister from 1905 to 1908.",
            "verification": {"verdict": "SUPPORT"},
        },
    ]

    assert factual_pipeline._build_final_answer(claims) == (
        "Henry Campbell-Bannerman succeeded Arthur Balfour. "
        "He served as Prime Minister from 1905 to 1908.",
        "verified",
    )


def test_factual_answer_is_withheld_when_final_claim_is_not_supported():
    import factual.pipeline as factual_pipeline

    claims = [
        {
            "essential": True,
            "text": "Paris is the capital of France.",
            "verification": {"verdict": "SUPPORT"},
        },
        {
            "essential": True,
            "text": "The answer is unknown.",
            "verification": {"verdict": "UNKNOWN"},
        },
    ]

    assert factual_pipeline._build_final_answer(claims) == (
        "The answer could not be verified from the available evidence.",
        "unverified",
    )


def test_generate_factual_response_preserves_model_final_answer(monkeypatch):
    class FakeFactualLLM:
        def generate_factual_reasoning(self, question):
            assert question == "What is the capital of India?"
            return SimpleNamespace(
                steps=[SimpleNamespace(text="India is a country.")],
                final_answer="New Delhi is the capital of India.",
            )

    monkeypatch.setattr(
        "factual.generation.reasoning.get_factual_llm_service",
        lambda: FakeFactualLLM(),
    )

    generated = generate_factual_response("What is the capital of India?")

    assert generated.reasoning_steps == ["India is a country."]
    assert generated.final_answer == "New Delhi is the capital of India."


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


def test_source_search_preserves_results_without_cited_summaries(monkeypatch):
    class FakeSearchService:
        def search_web(self, _query):
            return [
                {
                    "title": "A source discovered by web search",
                    "url": "https://example.com/result",
                    "text": "",
                    "text_origin": "search_source_without_citation",
                }
            ]

    monkeypatch.setattr(
        "factual.retrieval.source_search.get_factual_llm_service",
        lambda: FakeSearchService(),
    )
    monkeypatch.setattr("factual.retrieval.source_search._fetch_page_text", lambda _url: "")

    sources = search_sources("A claim with no matching snippet")

    assert len(sources) == 1
    assert sources[0]["url"] == "https://example.com/result"
    assert sources[0]["text"] == ""
    assert sources[0]["text_origin"] == "search_source_without_citation"


def test_source_search_fetches_page_text_for_uncited_result(monkeypatch):
    class FakeSearchService:
        def search_web(self, _query):
            return [
                {
                    "title": "LSTM components",
                    "url": "https://example.com/lstm",
                    "text": "A recurrent network stores information in memory.",
                    "text_origin": "citation_linked_model_summary",
                }
            ]

    page_text = (
        "The forget gate controls what information to discard from the cell state. "
        "The input gate controls which new information is added to the cell state."
    )
    monkeypatch.setattr(
        "factual.retrieval.source_search.get_factual_llm_service",
        lambda: FakeSearchService(),
    )
    fetched_urls = []

    def fake_fetch(url):
        fetched_urls.append(url)
        return page_text

    monkeypatch.setattr("factual.retrieval.source_search._fetch_page_text", fake_fetch)

    sources = search_sources("The forget gate controls information discarded from the cell state.")

    assert fetched_urls == ["https://example.com/lstm"]
    assert sources[0]["text_origin"] == "fetched_webpage_content"
    assert "forget gate controls" in sources[0]["text"]


def test_readable_page_parser_skips_scripts_and_navigation():
    from factual.retrieval.source_search import _ReadableTextParser

    parser = _ReadableTextParser()
    parser.feed(
        "<nav>Navigation text</nav><article><h1>LSTM</h1>"
        "<p>The forget gate controls memory.</p><script>ignore()</script></article>"
    )

    parsed_text = " ".join(parser.parts)

    assert "LSTM" in parsed_text
    assert "forget gate controls memory" in parsed_text
    assert "Navigation text" not in parsed_text
    assert "ignore()" not in parsed_text


def test_page_fetch_blocks_localhost_addresses():
    from factual.retrieval.source_search import _is_public_http_url

    assert _is_public_http_url("http://127.0.0.1/internal") is False
    assert _is_public_http_url("http://localhost/internal") is False


def test_factual_pipeline_logs_retrieval_stage_counts(monkeypatch, caplog):
    import factual.pipeline as factual_pipeline

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

    with caplog.at_level("INFO", logger="factual.pipeline"):
        process_factual("What is the capital of France?")

    assert "candidates=0 retained=0 rejected=0 evidence=0" in caplog.text


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
        "generate_factual_response",
        lambda _question: FactualGeneration(
            ["Canberra is the capital of Australia."],
            "Canberra is the capital of Australia.",
        ),
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
    assert result["final_answer"] == "Canberra is the capital of Australia."
    assert result["calibration_status"] == "fixed_sigmoid_not_empirically_calibrated"


def test_factual_pipeline_answers_from_verified_conclusion_not_reasoning_plan(monkeypatch):
    import factual.pipeline as factual_pipeline

    question = "What is the capital of India?"
    source = {
        "source_id": "s1",
        "title": "India capital",
        "url": "https://example.gov.in/capital",
        "domain": "example.gov.in",
        "source_type": "government",
        "text": "The capital of India is New Delhi.",
        "text_origin": "fetched_webpage_content",
        "retrieval_score": 1.0,
    }
    evidence = {
        "source_id": "s1",
        "title": "India capital",
        "url": source["url"],
        "domain": source["domain"],
        "text": source["text"],
        "text_origin": source["text_origin"],
        "reliability_method": "domain_type_policy",
        "source_reliability": 0.9,
        "relevance_score": 1.0,
        "status": "KEEP",
    }

    class FakeVerifier:
        def assess_factual_claim(self, _question, _claim_text, _evidence):
            return {
                "confidence": 0.9,
                "essential": False,
                "source_assessments": [{"source_id": "s1", "verdict": "SUPPORT"}],
            }

    monkeypatch.setattr(
        factual_pipeline,
        "generate_factual_response",
        lambda _question: FactualGeneration(
            ["Identify the country in question.", "Recall its capital city."],
            "New Delhi is the capital of India.",
        ),
    )
    monkeypatch.setattr(factual_pipeline, "get_factual_llm_service", lambda: FakeVerifier())
    monkeypatch.setattr(factual_pipeline, "search_sources", lambda *_args: [source])
    monkeypatch.setattr(
        factual_pipeline,
        "retrieve_evidence_for_claim",
        lambda *_args: [evidence],
    )

    result = process_factual(question)

    assert result["final_answer"] == "New Delhi is the capital of India."
    assert result["steps"][-1]["text"] == "New Delhi is the capital of India."
    assert result["steps"][-1]["claims"][0]["essential"] is True
    assert result["steps"][-1]["claims"][0]["verification"]["verdict"] == "SUPPORT"


def test_factual_pipeline_preserves_unverified_model_answer(monkeypatch):
    import factual.pipeline as factual_pipeline

    monkeypatch.setattr(
        factual_pipeline,
        "generate_factual_response",
        lambda _question: FactualGeneration(
            ["Dangerous Minds is the movie in question."],
            "Dangerous Minds.",
        ),
    )
    monkeypatch.setattr(factual_pipeline, "get_factual_llm_service", lambda: None)
    monkeypatch.setattr(factual_pipeline, "search_sources", lambda *_args: [])

    result = process_factual(
        "What Michelle Pfeiffer movie got a boost from the Coolio song Gangsta's Paradise?"
    )

    assert result["final_answer"] == "Dangerous Minds."
    assert result["answer_confidence_status"] == "unverified_model_answer"
    assert result["answer_confidence"] is not None


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
