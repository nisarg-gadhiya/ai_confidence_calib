import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def classify_question(question: str) -> str:
    from app.services.llm_service import LLMService

    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question must be a non-empty string.")

    llm = LLMService(
        provider=settings.llm_provider,
        model=settings.llm_model,
        api_key=settings.llm_api_key,
    )

    try:
        result = llm.classify_question(question)
    except ValueError:
        logger.exception("Question classification validation failed for input: %s", question)
        raise

    return result.category
