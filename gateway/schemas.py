from typing import Literal

from pydantic import BaseModel


class QuestionClassification(BaseModel):
    category: Literal["arithmetic", "logical", "factual"]
