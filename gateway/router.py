from gateway.classifier import classify_question
from app.api.routes.inference import run_inference
from app.api.schemas.reasoning import InferenceRequest
from factual.pipeline import process_factual


class LogicalPipelineNotImplementedError(NotImplementedError):
    """Raised when the Gateway selects the not-yet-implemented logical pipeline."""


def route_question(question: str, num_consistency_samples: int = 5):
    category = classify_question(question)

    if category == "arithmetic":
        return run_inference(
            InferenceRequest(
                question=question,
                num_consistency_samples=num_consistency_samples,
            )
        )
    if category == "factual":
        return process_factual(question)
    if category == "logical":
        raise LogicalPipelineNotImplementedError(
            "The logical reasoning pipeline is not implemented."
        )

    raise ValueError(f"Unsupported question category: {category!r}")
