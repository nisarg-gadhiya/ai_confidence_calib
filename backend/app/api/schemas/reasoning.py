from pydantic import BaseModel, Field


class InferenceRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        description="Question to analyze",
    )

    num_consistency_samples: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of samples used for consistency estimation",
    )


class ReasoningStepResponse(BaseModel):
    step_number: int
    step_text: str
    step_type: str

    verification_score: float | None = None
    consistency_score: float | None = None
    sample_agreement_score: float | None = None
    semantic_entropy: float | None = None
    consistency_method: str = "model_semantic_clusters"
    mean_token_logprob: float | None = None
    token_entropy: float | None = None
    fused_confidence: float | None = None
    verification_rationale: str | None = None
    sample_count: int = 0


class InferenceResponse(BaseModel):
    question: str
    reasoning: list[ReasoningStepResponse]
    predicted_error_step: int | None = None
    final_answer: str | None = None
    final_answer_confidence: float | None = None
    confidence_method: str = "type_adaptive_weighted_proxy"