from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from gateway.router import route_question
from gateway.schemas import QuestionClassification


class ClassificationRequest(BaseModel):
    question: str


router = APIRouter(tags=["gateway"])


@router.post("/classify", response_model=QuestionClassification)
def classify_question_endpoint(payload: ClassificationRequest):
    try:
        category = route_question(payload.question)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive API guard
        raise HTTPException(
            status_code=500,
            detail="Question classification failed.",
        ) from exc

    return QuestionClassification(category=category)
