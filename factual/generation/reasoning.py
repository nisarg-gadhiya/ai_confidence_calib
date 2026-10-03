from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.services.llm_service import LLMService


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


def generate_reasoning_steps(question: str) -> list[str]:
    """Generate a short factual reasoning plan using the shared LLM service when available."""
    try:
        llm = get_factual_llm_service()
        if llm is None:
            raise ValueError("LLM_API_KEY is not configured.")
        generated = llm.generate_reasoning(question)
        if getattr(generated, "steps", None):
            return [step.text for step in generated.steps]
    except Exception:
        pass

    return _fallback_reasoning_steps(question)
