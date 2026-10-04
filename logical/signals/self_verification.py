from __future__ import annotations

from app.services.llm_service import GeneratedStep, LLMService


def self_verify_step(
    llm: LLMService,
    question: str,
    step: GeneratedStep,
    preceding_steps: list[GeneratedStep],
    sample_count: int,
):
    samples = llm.generate_step_continuations(
        question,
        preceding_steps,
        next_step_number=step.step_number,
        num_samples=sample_count,
    )
    assessment = llm.verify_step(
        question,
        step,
        preceding_steps,
        [sample.text for sample in samples],
    )
    return samples, assessment