from dataclasses import dataclass


@dataclass
class GSM8KExample:
    question_id: str
    question: str
    reference_answer: str


def parse_gsm8k_example(
    example: dict,
    question_id: str,
) -> GSM8KExample:

    return GSM8KExample(
        question_id=question_id,
        question=example["question"],
        reference_answer=example["answer"],
    )