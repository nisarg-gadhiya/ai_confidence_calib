from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Claim(BaseModel):
    claim_id: str = Field(..., description="Stable identifier for the claim.")
    step_id: int = Field(..., description="Parent reasoning step identifier.")
    claim_text: str = Field(..., description="Atomic factual statement.")


class SourceRecord(BaseModel):
    source_id: str
    title: str
    url: str | None = None
    domain: str | None = None
    source_type: str = "general"
    text: str = ""
    retrieval_score: float = 0.0
    reliability_score: float = 0.0
    status: Literal["KEEP", "DOWN_WEIGHT", "REJECT"] = "KEEP"


class EvidenceRecord(BaseModel):
    evidence_id: str
    claim_id: str
    source_id: str
    text: str
    relevance_score: float = 0.0
    source_reliability: float = 0.0


class VerificationResult(BaseModel):
    verdict: Literal["SUPPORT", "CONTRADICT", "UNKNOWN"]
    evidence_score: float | None = None
    explanation: str | None = None


class FactStepResult(BaseModel):
    step_id: int
    text: str
    claims: list[dict]


class FactualPipelineResult(BaseModel):
    question: str
    steps: list[FactStepResult]
    predicted_error_step: int | None = None
    answer_confidence: float | None = None
    answer_confidence_status: str | None = None
    calibration_status: str | None = None
