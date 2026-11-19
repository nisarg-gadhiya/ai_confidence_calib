from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from app.core.config import settings
from app.services.llm_service import LLMService


@dataclass(frozen=True)
class FactualGeneration:
    reasoning_steps: list[str]
    final_answer: str | None


def _fallback_reasoning_steps(question: str) -> list[str]:
    lowered = question.lower()
    if "capital" in lowered:
        return [
            "Identify the country or entity the question is asking about.",
            "Determine the official capital associated with that entity.",
            "Verify the capital against a reliable source before finalizing the answer.",
        ]
    if "who wrote" in lowered or "author" in lowered:
        return [
            "Identify the work or title being queried.",
            "Determine the author associated with that work.",
            "Verify the attribution against a reliable reference source.",
        ]
    if "when did" in lowered or "year" in lowered:
        return [
            "Identify the event or period the question refers to.",
            "Locate the key date or year associated with the event.",
            "Cross-check the date against a dependable historical source.",
        ]
    return [
        "Identify the main factual subject in the question.",
        "Find the specific fact or entity the question asks about.",
        "Verify the claim against a reliable source before concluding.",
    ]


@lru_cache(maxsize=1)
def get_factual_llm_service() -> LLMService | None:
    if not settings.llm_api_key:
        return None
    return LLMService(
        provider=settings.llm_provider,
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        search_model=settings.factual_search_model,
    )


def generate_factual_response(question: str) -> FactualGeneration:
    """Generate factual reasoning steps and preserve the model's direct answer."""
    llm = get_factual_llm_service()
    if llm is None:
        return FactualGeneration(_fallback_reasoning_steps(question), None)

    generated = llm.generate_factual_reasoning(question)
    reasoning_steps = [
        step.text.strip()
        for step in generated.steps
        if isinstance(step.text, str) and step.text.strip()
    ]
    if not reasoning_steps:
        reasoning_steps = _fallback_reasoning_steps(question)

    final_answer = generated.final_answer
    if not isinstance(final_answer, str) or not final_answer.strip():
        final_answer = None
    else:
        final_answer = final_answer.strip()

    return FactualGeneration(reasoning_steps, final_answer)


def generate_reasoning_steps(question: str) -> list[str]:
    """Generate factual reasoning steps using the shared LLM service when available."""
    return generate_factual_response(question).reasoning_steps
