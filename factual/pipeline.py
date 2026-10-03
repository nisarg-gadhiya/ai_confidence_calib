from __future__ import annotations

from factual.answer_confidence import calculate_answer_confidence
from factual.calibration.fusion import fuse_step_signals
from factual.calibration.calibrator import calibrate_probability
from factual.decomposition.claim_extractor import extract_claims
from factual.decomposition.step_decomposer import decompose_reasoning
from factual.evaluation.localization import localize_riskiest_step
from factual.generation.reasoning import generate_reasoning_steps, get_factual_llm_service
from factual.retrieval.evidence_retrieval import retrieve_evidence_for_claim
from factual.retrieval.reliability_filter import filter_sources
from factual.retrieval.source_reliability import estimate_source_reliability
from factual.retrieval.source_search import search_sources
from factual.signals.consistency import consistency_score
from factual.signals.evidence_score import aggregate_evidence_score


def process_factual(question: str):
    """Run the factual-question pipeline on the original question."""
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question must be a non-empty string.")

    reasoning_steps = generate_reasoning_steps(question)
    decomposed_steps = decompose_reasoning(reasoning_steps)
    llm = get_factual_llm_service()

    step_results = []
    flat_claims = []
    for step in decomposed_steps:
        claims = extract_claims([step])
        claim_results = []
        for claim in claims:
            sources = search_sources(claim["claim_text"], question)
            ranked_sources = [
                {
                    **source,
                    "reliability_score": estimate_source_reliability(source),
                    "reliability_method": "domain_type_policy",
                }
                for source in sources
            ]
            filtered_sources = filter_sources(ranked_sources)

            evidence = retrieve_evidence_for_claim(claim["claim_text"], filtered_sources)
            assessment = (
                llm.assess_factual_claim(question, claim["claim_text"], evidence)
                if llm is not None
                else {"confidence": 0.0, "essential": False, "source_assessments": []}
            )
            source_verdicts = {
                item["source_id"]: item["verdict"]
                for item in assessment["source_assessments"]
            }
            verdicts = [source_verdicts.get(item["source_id"], "UNKNOWN") for item in evidence]
            support_evidence = [
                item for item, verdict in zip(evidence, verdicts) if verdict == "SUPPORT"
            ]
            contradict_evidence = [
                item for item, verdict in zip(evidence, verdicts) if verdict == "CONTRADICT"
            ]
            unknown_evidence = [
                item for item, verdict in zip(evidence, verdicts) if verdict == "UNKNOWN"
            ]

            evidence_score = aggregate_evidence_score(
                support_evidence=support_evidence,
                contradict_evidence=contradict_evidence,
                unknown_evidence=unknown_evidence,
            )
            claim_consistency = consistency_score(verdicts)
            claim_self_verification = assessment["confidence"]
            fused_confidence = fuse_step_signals(
                self_verification_score=claim_self_verification,
                consistency_score=claim_consistency,
                evidence_score=evidence_score,
            )
            calibrated_probability = calibrate_probability(
                self_verification_score=claim_self_verification,
                consistency_score=claim_consistency,
                evidence_score=evidence_score,
                fused_confidence=fused_confidence,
            )

            essential = assessment["essential"]
            support_weight = sum(
                item["source_reliability"] * item["relevance_score"]
                for item in support_evidence
            )
            contradict_weight = sum(
                item["source_reliability"] * item["relevance_score"]
                for item in contradict_evidence
            )
            if support_weight > contradict_weight:
                claim_verdict = "SUPPORT"
            elif contradict_weight > support_weight:
                claim_verdict = "CONTRADICT"
            else:
                claim_verdict = "UNKNOWN"
            claim_record = {
                "claim_id": claim["claim_id"],
                "text": claim["claim_text"],
                "essential": essential,
                "verification": {
                    "verdict": claim_verdict,
                    "evidence_score": evidence_score,
                },
                "self_verification_score": claim_self_verification,
                "consistency_score": claim_consistency,
                "calibrated_probability": calibrated_probability,
                "sources": [
                    {
                        "source_id": item["source_id"],
                        "title": item["title"],
                        "url": item.get("url"),
                        "domain": item["domain"],
                        "text_origin": item["text_origin"],
                        "reliability_method": item.get("reliability_method", "domain_type_policy"),
                        "reliability_score": item["source_reliability"],
                        "status": item["status"],
                        "text": item["text"],
                    }
                    for item in evidence
                ],
            }
            flat_claims.append(claim_record)
            claim_results.append(claim_record)

        step_results.append(
            {
                "step_id": step["step_id"],
                "text": step["text"],
                "claims": claim_results,
            }
        )

    step_probabilities = {
        step["step_id"]: min(
            (
                claim["calibrated_probability"]
                for claim in step["claims"]
            ),
            default=0.5,
        )
        for step in step_results
    }

    predicted_error_step = localize_riskiest_step(
        [{"step_id": step_id, "calibrated_probability": probability} for step_id, probability in step_probabilities.items()]
    )

    answer_confidence_status = "ok"
    try:
        answer_confidence = calculate_answer_confidence(flat_claims)
    except ValueError:
        answer_confidence = None
        answer_confidence_status = "invalid_essential_probability"
    if answer_confidence is None:
        answer_confidence_status = "no_essential_claims"

    return {
        "question": question,
        "steps": step_results,
        "predicted_error_step": predicted_error_step,
        "answer_confidence": answer_confidence,
        "answer_confidence_status": answer_confidence_status,
        "calibration_status": "fixed_sigmoid_not_empirically_calibrated",
    }
