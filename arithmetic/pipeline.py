"""Entry point for the arithmetic reasoning pipeline."""

from backend.app.services.reasoning_service import decompose_reasoning
from backend.app.services.verification_service import verify_step
from arithmetic.generation.generate_reasoning import generate_reasoning


def process_arithmetic(question: str):
    """Run the existing arithmetic generation flow through a single entry point."""
    generated = generate_reasoning(question)
    steps = decompose_reasoning(generated.raw_text)

    step_summaries = [
        {
            "step_number": step.step_number,
            "text": step.text,
            "step_type": step.step_type,
            "verification_score": verify_step(question, step.text),
        }
        for step in steps
    ]

    return {
        "question": question,
        "generated_reasoning": generated.raw_text,
        "final_answer": generated.final_answer,
        "steps": step_summaries,
    }
