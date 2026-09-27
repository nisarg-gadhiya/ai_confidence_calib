from sqlalchemy.orm import Session

from app.db.models import Question


def create_question(
    db: Session,
    question_text: str,
    reference_answer: str | None = None,
    dataset: str = "gsm8k",
    dataset_question_id: str | None = None,
) -> Question:

    question = Question(
        dataset=dataset,
        dataset_question_id=dataset_question_id,
        question_text=question_text,
        reference_answer=reference_answer,
    )

    db.add(question)
    db.commit()
    db.refresh(question)

    return question


def get_question(
    db: Session,
    question_id: int,
) -> Question | None:

    return db.get(
        Question,
        question_id,
    )