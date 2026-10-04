from __future__ import annotations

import pytest

from app.services.llm_service import GeneratedStep, LLMResponse, StepAssessment, StepContinuation
from factual.answer_confidence import calculate_answer_confidence
from factual.calibration.calibrator import calibrate_probability
from factual.calibration.fusion import fuse_step_signals
from logical.pipeline import process_logical
from logical.premises.extractor import extract_premises, extract_target_statement
from logical.rules.extractor import extract_rules, parse_atom
from logical.rules.rule_engine import LogicalSolver, run_rule_engine
from logical.verification.logical_verifier import verify_claim
from logical.signals.consistency import assess_consistency


def _check_question(question: str):
    premises = extract_premises(question)
    rules = extract_rules(premises)
    engine = run_rule_engine(premises, rules)
    target_text = extract_target_statement(question)
    target = parse_atom(target_text) if target_text else None
    return premises, rules, engine, verify_claim(target, engine) if target else None


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("All cats are mammals. Tom is a cat. Is Tom a mammal?", "ENTAILED"),
        ("All cats are mammals. Tom is a cat. Is Tom not a mammal?", "CONTRADICTED"),
        ("Tom is a cat. Is Tom friendly?", "UNKNOWN"),
        (
            "All mammals are animals. All dogs are mammals. Rex is a dog. Is Rex an animal?",
            "ENTAILED",
        ),
        (
            "If it rains, the ground becomes wet. The ground is wet. Is it necessarily raining?",
            "UNKNOWN",
        ),
        (
            "Alice is taller than Bob. Bob is taller than Charlie. Is Alice taller than Charlie?",
            "ENTAILED",
        ),
    ],
)
def test_deterministic_logical_verification(question, expected):
    _premises, _rules, _engine, verification = _check_question(question)

    assert verification["verdict"] == expected
    assert 0.0 <= verification["logical_validity_score"] <= 1.0


def test_contradicted_claim_has_zero_claim_validity_but_keeps_opposing_proof():
    _premises, _rules, _engine, verification = _check_question(
        "All cats are mammals. Tom is a cat. Is Tom not a mammal?"
    )

    assert verification["verdict"] == "CONTRADICTED"
    assert verification["logical_validity_score"] == 0.0
    assert verification["premises_used"] == ["p1", "p2"]
    assert verification["rules_used"] == ["r1"]


def test_explicitly_contradictory_premises_are_detected():
    _premises, _rules, engine, verification = _check_question(
        "Tom is a cat. Tom is not a cat."
    )

    assert engine.inconsistent is True
    assert engine.inconsistent_atoms == [("tom", "cat", None)]
    assert verification is None


def test_consistency_signal_accounts_for_explicit_premise_contradictions():
    score, _entropy, method = assess_consistency(
        ["same", "same", "different"],
        [0, 0, 1],
        fact_count=2,
        contradiction_count=1,
    )

    assert score == 0.0
    assert method == "model_semantic_clusters"


def test_premise_extraction_excludes_the_question():
    premises = extract_premises("All cats are mammals. Tom is a cat. Is Tom a mammal?")

    assert [item["text"] for item in premises] == [
        "All cats are mammals.",
        "Tom is a cat.",
    ]


def test_disjunction_does_not_entail_either_alternative():
    premise = [{"premise_id": "p1", "text": "A or B."}]
    engine = run_rule_engine(premise, extract_rules(premise))

    assert verify_claim(parse_atom("A or B"), engine)["verdict"] == "ENTAILED"
    assert verify_claim(parse_atom("A"), engine)["verdict"] == "UNKNOWN"
    assert verify_claim(parse_atom("B"), engine)["verdict"] == "UNKNOWN"


def test_z3_detects_disjunction_conflict_via_unsat_core():
    premises = [
        {"premise_id": "p1", "text": "A or B."},
        {"premise_id": "p2", "text": "Not A."},
        {"premise_id": "p3", "text": "Not B."},
    ]
    engine = run_rule_engine(premises, extract_rules(premises))

    assert engine.inconsistent is True
    assert engine.inconsistent_atoms == []
    assert engine.logic_solver.inconsistency_provenance["premises_used"] == ["p1", "p2", "p3"]
    assert verify_claim(parse_atom("A"), engine)["verdict"] == "UNKNOWN"


def test_conditional_disjunction_and_conjunction_antecedents():
    disjunctive_premises = [
        {"premise_id": "p1", "text": "If A, B or C."},
        {"premise_id": "p2", "text": "A is true."},
    ]
    disjunctive_engine = run_rule_engine(
        disjunctive_premises,
        extract_rules(disjunctive_premises),
    )
    assert verify_claim(parse_atom("B or C"), disjunctive_engine)["verdict"] == "ENTAILED"
    assert verify_claim(parse_atom("B"), disjunctive_engine)["verdict"] == "UNKNOWN"

    conjunctive_premises = [
        {"premise_id": "p1", "text": "If A and B, C."},
        {"premise_id": "p2", "text": "A is true."},
        {"premise_id": "p3", "text": "B is true."},
    ]
    conjunctive_engine = run_rule_engine(
        conjunctive_premises,
        extract_rules(conjunctive_premises),
    )
    assert verify_claim(parse_atom("C"), conjunctive_engine)["verdict"] == "ENTAILED"


def test_symbolic_implication_and_truth_question():
    premises = [
        {"premise_id": "p1", "text": "A -> B."},
        {"premise_id": "p2", "text": "A is true."},
    ]
    engine = run_rule_engine(premises, extract_rules(premises))

    assert verify_claim(parse_atom("B is true"), engine)["verdict"] == "ENTAILED"


def test_universal_rule_with_conjunctive_consequents():
    premises = [
        {"premise_id": "p1", "text": "All dogs are mammals and animals."},
        {"premise_id": "p2", "text": "Rex is a dog."},
    ]
    engine = run_rule_engine(premises, extract_rules(premises))

    assert verify_claim(parse_atom("Rex is an animal"), engine)["verdict"] == "ENTAILED"


def test_unsupported_rule_syntax_is_not_treated_as_a_fact():
    premises = [
        {"premise_id": "p1", "text": "Every cat is a mammal."},
        {"premise_id": "p2", "text": "Tom is a cat."},
    ]
    engine = run_rule_engine(premises, extract_rules(premises))

    assert engine.logic_solver.unsupported_premises == ["p1"]
    assert verify_claim(parse_atom("Tom is a mammal"), engine)["verdict"] == "UNKNOWN"


def test_unsupported_compound_premise_is_not_misread_as_an_atom():
    premises = [
        {"premise_id": "p1", "text": "Tom is a cat and Tom is friendly."},
        {"premise_id": "p2", "text": "Tom is a cat."},
    ]
    engine = run_rule_engine(premises, extract_rules(premises))

    assert engine.logic_solver.unsupported_premises == ["p1"]
    assert verify_claim(parse_atom("Tom is friendly"), engine)["verdict"] == "UNKNOWN"


def test_solver_unknown_status_is_conservative():
    from unittest.mock import Mock
    from z3 import unknown

    solver = LogicalSolver.__new__(LogicalSolver)
    solver.base_status = unknown
    solver.solver = Mock()
    solver.solver.reason_unknown.return_value = "timeout"
    solver.unsupported_premises = []
    solver.inconsistency_provenance = {"premises_used": [], "rules_used": []}

    result = solver.check_claim(parse_atom("A"))

    assert result.verdict == "UNKNOWN"
    assert result.reason == "timeout"


class FakeLogicalLLM:
    def generate_step_continuations(
        self,
        _question,
        _preceding_steps,
        next_step_number,
        num_samples,
    ):
        return [
            StepContinuation(text=f"candidate {next_step_number} variant {index}")
            for index in range(num_samples)
        ]

    def verify_step(self, _question, step, _preceding_steps, samples):
        return StepAssessment(
            p_true=0.62 + step.step_number * 0.05,
            rationale="The candidate step follows the fixed premise prefix.",
            step_type="logical_inference",
            sample_cluster_ids=[0, 0, 1][:len(samples)],
        )


def test_pipeline_reuses_fusion_calibration_localization_and_answer_confidence(monkeypatch):
    question = "All cats are mammals. Tom is a cat. Is Tom a mammal?"
    monkeypatch.setattr(
        "logical.pipeline.generate_logical_reasoning",
        lambda _question: LLMResponse(
            text="Step 1: Tom is a mammal.",
            final_answer="Yes, Tom is a mammal.",
            steps=[GeneratedStep(1, "Tom is a mammal.", "logical_inference")],
        ),
    )
    monkeypatch.setattr("logical.pipeline.get_logical_llm_service", lambda: FakeLogicalLLM())

    result = process_logical(question, num_consistency_samples=3)

    claim = result["steps"][-1]["claims"][0]
    assert claim["verification"]["verdict"] == "ENTAILED"
    assert claim["verification"]["logical_validity_score"] == 1.0
    assert claim["self_verification_score"] == pytest.approx(0.67)
    assert claim["consistency_score"] == pytest.approx(2 / 3)

    fused = fuse_step_signals(
        claim["self_verification_score"],
        claim["consistency_score"],
        claim["verification"]["logical_validity_score"],
    )
    expected_probability = calibrate_probability(
        claim["self_verification_score"],
        claim["consistency_score"],
        claim["verification"]["logical_validity_score"],
        fused_confidence=fused,
    )
    assert claim["calibrated_probability"] == pytest.approx(expected_probability)
    assert result["answer_confidence"] == pytest.approx(
        calculate_answer_confidence([claim])
    )
    assert result["predicted_error_step"] == 1
    assert result["final_answer"].startswith("Yes.")


def test_pipeline_localizes_multistep_proof_and_aggregates_only_final_claim(monkeypatch):
    question = (
        "All mammals are animals. All dogs are mammals. "
        "Rex is a dog. Is Rex an animal?"
    )
    monkeypatch.setattr(
        "logical.pipeline.generate_logical_reasoning",
        lambda _question: LLMResponse(
            text="Step 1: Rex is a mammal.\nStep 2: Rex is an animal.",
            final_answer="Rex is an animal.",
            steps=[
                GeneratedStep(1, "Rex is a mammal.", "logical_inference"),
                GeneratedStep(2, "Rex is an animal.", "logical_inference"),
            ],
        ),
    )
    monkeypatch.setattr("logical.pipeline.get_logical_llm_service", lambda: FakeLogicalLLM())

    result = process_logical(question, num_consistency_samples=3)

    claims = [step["claims"][0] for step in result["steps"]]
    assert [claim["text"] for claim in claims] == [
        "Rex is a mammal.",
        "Rex is an animal.",
    ]
    assert [claim["self_verification_score"] for claim in claims] == pytest.approx([0.67, 0.72])
    assert claims[0]["essential"] is False
    assert claims[1]["essential"] is True
    assert result["answer_confidence"] == pytest.approx(
        calculate_answer_confidence([claims[1]])
    )
    assert result["predicted_error_step"] in {1, 2}


def test_pipeline_reports_inconsistent_premises_without_external_retrieval(monkeypatch):
    question = "Tom is a cat. Tom is not a cat."
    monkeypatch.setattr(
        "logical.pipeline.generate_logical_reasoning",
        lambda _question: LLMResponse(
            text="Step 1: The premises contradict each other.",
            final_answer="The premises are inconsistent.",
            steps=[GeneratedStep(1, "The premises contradict each other.", "logical_inference")],
        ),
    )
    monkeypatch.setattr("logical.pipeline.get_logical_llm_service", lambda: FakeLogicalLLM())

    result = process_logical(question, num_consistency_samples=3)

    assert result["inconsistency_detected"] is True
    assert result["contradictions"] == [
        {"subject": "tom", "predicate": "cat", "object": None}
    ]
    assert result["final_answer"] == "The supplied premises are inconsistent."
    assert result["answer_confidence"] is None
    assert result["answer_confidence_status"] == "inconsistent_premises"
    assert result["predicted_error_step"] is None
    assert result["steps"][0]["claims"][0]["calibrated_probability"] is None
    assert result["steps"][0]["claims"][0]["self_verification_score"] is None
    assert result["steps"][0]["sample_count"] == 0