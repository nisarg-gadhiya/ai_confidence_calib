import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from gateway.schemas import QuestionClassification


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("What is 35% of 800?", "arithmetic"),
        ("A train travels 240 km in 4 hours. What is its speed?", "arithmetic"),
        ("John is taller than Mike. Mike is taller than David. Who is shortest?", "logical"),
        ("If A is greater than B and B is greater than C, which is smallest?", "logical"),
        ("What is the capital of Japan?", "factual"),
        ("Who wrote Romeo and Juliet?", "factual"),
    ],
)
def test_question_classification_schema_accepts_expected_categories(question, expected):
    payload = {"category": expected}
    result = QuestionClassification.model_validate(payload)
    assert result.category == expected


def test_question_classification_schema_rejects_unknown_category():
    with pytest.raises(ValidationError):
        QuestionClassification.model_validate({"category": "unknown"})


def test_gateway_api_returns_category_only(monkeypatch):
    monkeypatch.setattr("gateway.router.classify_question", lambda question: "arithmetic")

    client = TestClient(app)
    response = client.post("/api/classify", json={"question": "What is 10 + 20?"})

    assert response.status_code == 200
    assert response.json() == {"category": "arithmetic"}
