from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas.question import (
    QuestionCreate,
    QuestionResponse,
)

from app.db.database import get_db

from app.db.repositories import (
    create_question,
    get_question,
)


router = APIRouter(
    prefix="/questions",
    tags=["questions"],
)


@router.post(
    "",
    response_model=QuestionResponse,
)
def create_question_endpoint(
    payload: QuestionCreate,
    db: Session = Depends(get_db),
):

    return create_question(
        db=db,
        question_text=payload.question_text,
        reference_answer=payload.reference_answer,
        dataset=payload.dataset,
        dataset_question_id=payload.dataset_question_id,
    )


@router.get(
    "/{question_id}",
    response_model=QuestionResponse,
)
def get_question_endpoint(
    question_id: int,
    db: Session = Depends(get_db),
):

    question = get_question(
        db,
        question_id,
    )

    if question is None:

        raise HTTPException(
            status_code=404,
            detail="Question not found",
        )

    return question