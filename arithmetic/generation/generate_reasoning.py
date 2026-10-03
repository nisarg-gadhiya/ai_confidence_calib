from dataclasses import dataclass


@dataclass
class GeneratedReasoning:
    raw_text: str
    final_answer: str | None = None


def generate_reasoning(
    question: str,
) -> GeneratedReasoning:

    # Temporary development implementation.
    # This will later call the real LLM.

    return GeneratedReasoning(
        raw_text=(
            "Step 1: Identify the quantities in the question.\n"
            "Step 2: Apply the required arithmetic operation.\n"
            "Step 3: State the final result."
        ),
        final_answer=None,
    )