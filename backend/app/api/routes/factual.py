from fastapi import APIRouter
from pydantic import BaseModel

from factual.pipeline import process_factual


class FactualRequest(BaseModel):
    question: str


router = APIRouter(tags=["factual"])


@router.post("/factual")
def factual_endpoint(payload: FactualRequest):
    return process_factual(payload.question)
