from fastapi import APIRouter
import math

from app.api.schemas.reasoning import (
    InferenceRequest,
    InferenceResponse,
    ReasoningStepResponse,
)

from app.core.config import settings

from app.services.consistency_service import (
    exact_agreement_score,
    semantic_cluster_metrics,
)
from app.services.calibration_service import (
    predict_step_confidence,
)

from app.services.fusion_service import (
    fuse_confidence,
    predict_error_step,
)

from app.services.llm_service import (
    LLMService,
)

router = APIRouter(
    prefix="/inference",
    tags=["inference"],
)


@router.post(
    "",
    response_model=InferenceResponse,
)
def run_inference(
    payload: InferenceRequest,
):

    llm = LLMService(
        provider=settings.llm_provider,
        model=settings.llm_model,
        api_key=settings.llm_api_key,
    )

    generated = llm.generate_reasoning(
        payload.question,
    )

    steps = generated.steps

    results: list[
        ReasoningStepResponse
    ] = []
    confidence_method = "type_adaptive_weighted_proxy"

    for step_index, step in enumerate(steps):
        preceding_steps = steps[:step_index]
        samples = llm.generate_step_continuations(
            payload.question,
            preceding_steps,
            next_step_number=step.step_number,
            num_samples=payload.num_consistency_samples,
        )
        sample_texts = [sample.text for sample in samples]
        assessment = llm.verify_step(
            payload.question,
            step,
            preceding_steps,
            sample_texts,
        )
        if assessment.sample_cluster_ids is None:
            consistency = exact_agreement_score(sample_texts)
            semantic_entropy = None
            consistency_method = "exact_match_fallback"
        else:
            consistency, semantic_entropy = semantic_cluster_metrics(
                assessment.sample_cluster_ids
            )
            consistency_method = "model_semantic_clusters"
        verification = assessment.p_true
        token_logprobs = [
            sample.mean_token_logprob
            for sample in samples
            if sample.mean_token_logprob is not None
        ]
        token_entropies = [
            sample.token_entropy
            for sample in samples
            if sample.token_entropy is not None
        ]
        mean_token_logprob = (
            sum(token_logprobs) / len(token_logprobs)
            if token_logprobs
            else None
        )
        token_probability = (
            math.exp(mean_token_logprob)
            if mean_token_logprob is not None
            else None
        )
        token_entropy = (
            sum(token_entropies) / len(token_entropies)
            if token_entropies
            else None
        )
        proxy_confidence = fuse_confidence(
            verification,
            consistency,
            step_type=assessment.step_type,
            token_probability=token_probability,
        )
        step_features = {
            "step_type": assessment.step_type,
            "verification_score": verification,
            "consistency_score": consistency,
            "sample_agreement_score": exact_agreement_score(sample_texts),
            "semantic_entropy": semantic_entropy,
            "consistency_method": consistency_method,
            "mean_token_logprob": mean_token_logprob,
            "token_entropy": token_entropy,
        }
        calibrated_confidence = predict_step_confidence(
            step_features,
            settings.step_calibrator_path,
        )
        if calibrated_confidence is None:
            fused = proxy_confidence
        else:
            fused = calibrated_confidence
            confidence_method = "xgboost_step_calibrator"

        results.append(
            ReasoningStepResponse(
                step_number=step.step_number,
                step_text=step.text,
                step_type=assessment.step_type,
                verification_score=verification,
                consistency_score=consistency,
                sample_agreement_score=step_features["sample_agreement_score"],
                semantic_entropy=semantic_entropy,
                consistency_method=consistency_method,
                mean_token_logprob=mean_token_logprob,
                token_entropy=token_entropy,
                fused_confidence=fused,
                verification_rationale=assessment.rationale,
                sample_count=len(sample_texts),
            )
        )

    confidence_map = {
        item.step_number: item.fused_confidence
        for item in results
        if item.fused_confidence is not None
    }

    predicted_error = predict_error_step(
        confidence_map
    )

    return InferenceResponse(
        question=payload.question,
        reasoning=results,
        predicted_error_step=predicted_error,
        final_answer=generated.final_answer,
        final_answer_confidence=min(confidence_map.values(), default=None),
        confidence_method=confidence_method,
    )