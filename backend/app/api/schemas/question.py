from pydantic import BaseModel


class QuestionCreate(BaseModel):
    question_text: str
    reference_answer: str | None = None
    dataset: str = "gsm8k"
    dataset_question_id: str | None = None


class QuestionResponse(BaseModel):
    id: int
    dataset: str
    dataset_question_id: str | None = None
    question_text: str
    reference_answer: str | None = None