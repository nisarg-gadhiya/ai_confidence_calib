from app.api.routes import inference
from app.api.schemas.reasoning import InferenceRequest
from app.services.llm_service import (
    GeneratedStep,
    LLMResponse,
    StepAssessment,
    StepContinuation,
)


class FakeLLMService:
    def __init__(self, **kwargs):
        self.branch_prefixes = []

    def generate_reasoning(self, question):
        steps = [
            GeneratedStep(1, "There are 5 bags.", "setup"),
            GeneratedStep(2, "5 x 8 = 40 apples.", "arithmetic"),
        ]
        return LLMResponse(
            text="Step 1: There are 5 bags.\nStep 2: 5 x 8 = 40 apples.",
            final_answer="40 apples",
            steps=steps,
        )

    def generate_step_continuations(
        self,
        question,
        preceding_steps,
        next_step_number,
        num_samples,
    ):
        self.branch_prefixes.append(
            ([step.step_number for step in preceding_steps], num_samples)
        )
        return [
            StepContinuation(
                text=f"candidate {index}",
                mean_token_logprob=-0.2 if next_step_number == 1 else -1.0,
                token_entropy=0.3 if next_step_number == 1 else 0.8,
            )
            for index in range(num_samples)
        ]

    def verify_step(self, question, step, preceding_steps, sample_continuations):
        return StepAssessment(
            p_true=0.9 if step.step_number == 1 else 0.5,
            rationale=f"Review for step {step.step_number}",
            step_type=step.step_type,
            sample_cluster_ids=[0, 0, 1],
        )


def test_inference_resamples_each_step_from_its_fixed_prefix(monkeypatch):
    fake_llm = FakeLLMService()
    monkeypatch.setattr(inference, "LLMService", lambda **kwargs: fake_llm)

    response = inference.run_inference(
        InferenceRequest(
            question="There are 5 bags with 8 apples each.",
            num_consistency_samples=3,
        )
    )

    assert fake_llm.branch_prefixes == [([], 3), ([1], 3)]
    assert [step.step_number for step in response.reasoning] == [1, 2]
    assert response.reasoning[1].verification_rationale == "Review for step 2"
    assert response.reasoning[1].mean_token_logprob == -1.0
    assert abs(response.reasoning[1].token_entropy - 0.8) < 1e-9
    assert response.predicted_error_step == 2
    assert response.final_answer_confidence == response.reasoning[1].fused_confidence
    assert response.confidence_method == "type_adaptive_weighted_proxy"


def test_inference_uses_exact_match_fallback_when_clusters_are_invalid(monkeypatch):
    fake_llm = FakeLLMService()
    fake_llm.verify_step = lambda *args: StepAssessment(
        p_true=0.7,
        rationale="Review available; clustering omitted.",
        step_type="arithmetic",
        sample_cluster_ids=None,
    )
    monkeypatch.setattr(inference, "LLMService", lambda **kwargs: fake_llm)

    response = inference.run_inference(
        InferenceRequest(
            question="There are 5 bags with 8 apples each.",
            num_consistency_samples=3,
        )
    )

    assert response.reasoning[0].consistency_method == "exact_match_fallback"
    assert response.reasoning[0].semantic_entropy is None
    assert response.reasoning[0].consistency_score == 1 / 3
