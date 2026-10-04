from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class LogicalClaimResult(BaseModel):
    claim_id: str
    text: str
    essential: bool
    verification: dict
    self_verification_score: float | None
    consistency_score: float
    calibrated_probability: float | None


class LogicalStepResult(BaseModel):
    step_id: int
    text: str
    reasoning_operation: str
    premises_used: list[str]
    rules_used: list[str]
    claims: list[LogicalClaimResult]


class LogicalPipelineResult(BaseModel):
    question: str
    premises: list[dict[str, str]]
    rules: list[dict]
    steps: list[LogicalStepResult]
    inconsistency_detected: bool
    contradictions: list[dict]
    unsupported_premises: list[str]
    predicted_error_step: int | None = None
    answer_confidence: float | None = None
    answer_confidence_status: Literal[
        "ok",
        "no_essential_claims",
        "invalid_essential_probability",
        "inconsistent_premises",
    ]
    calibration_status: str