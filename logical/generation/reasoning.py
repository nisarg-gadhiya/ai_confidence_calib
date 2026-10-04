from __future__ import annotations

from factual.generation.reasoning import get_factual_llm_service


def get_logical_llm_service():
    """Return the shared cached LLM service used by the factual pipeline."""
    return get_factual_llm_service()


def generate_logical_reasoning(question: str):
    service = get_logical_llm_service()
    if service is None:
        raise ValueError("LLM_API_KEY is required for logical reasoning.")
    return service.generate_logical_reasoning(question)