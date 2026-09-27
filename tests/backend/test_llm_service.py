import json
import math
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services.llm_service import GeneratedStep, LLMService


def _completion(*contents: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
            )
            for content in contents
        ],
    )


def test_generate_reasoning_returns_structured_steps():
    client = Mock()
    client.chat.completions.create.return_value = _completion(
        '{"steps":[{"step_number":1,"text":"Add 2 and 3.","step_type":"arithmetic"}],"final_answer":"5"}',
    )
    service = LLMService(client=client)

    result = service.generate_reasoning("What is 2 + 3?")

    assert result.text == "Step 1: Add 2 and 3."
    assert result.final_answer == "5"
    assert result.steps[0].step_type == "arithmetic"
    assert client.chat.completions.create.call_args.kwargs["n"] == 1


def test_step_continuations_share_the_fixed_prefix():
    client = Mock()
    client.chat.completions.create.return_value = _completion(
        '{"step_text":"Multiply 5 by 8."}',
        '{"step_text":"There are 5 groups of 8."}',
    )
    service = LLMService(client=client)

    samples = service.generate_step_continuations(
        "There are 5 bags with 8 apples each.",
        [GeneratedStep(1, "There are 5 bags.", "setup")],
        next_step_number=2,
        num_samples=2,
    )

    assert [sample.text for sample in samples] == [
        "Multiply 5 by 8.",
        "There are 5 groups of 8.",
    ]
    request = client.chat.completions.create.call_args.kwargs
    assert request["n"] == 2
    assert request["temperature"] > 0
    assert request["logprobs"] is True
    assert request["top_logprobs"] == 5
    assert json.loads(request["messages"][1]["content"]) == {
        "question": "There are 5 bags with 8 apples each.",
        "preceding_steps": [
            {"step_number": 1, "text": "There are 5 bags."},
        ],
        "next_step_number": 2,
    }


def test_step_verification_uses_prefix_and_candidate_samples():
    client = Mock()
    client.chat.completions.create.return_value = _completion(
        '{"p_true":0.82,"rationale":"The multiplication matches the quantities.","step_type":"arithmetic_computation","sample_cluster_ids":[0,0,1]}'
    )
    service = LLMService(client=client)

    review = service.verify_step(
        "There are 5 bags with 8 apples each.",
        GeneratedStep(2, "5 x 8 = 40", "arithmetic"),
        [GeneratedStep(1, "There are 5 bags.", "setup")],
        ["Multiply 5 by 8.", "5 groups of 8 is 40.", "Add 5 and 8."],
    )

    assert review.p_true == 0.82
    assert review.step_type == "arithmetic"
    assert review.sample_cluster_ids == [0, 0, 1]
    request = client.chat.completions.create.call_args.kwargs
    payload = json.loads(request["messages"][1]["content"])
    assert payload["preceding_steps"][0]["step_number"] == 1
    assert len(payload["candidate_continuations"]) == 3


def test_step_verification_falls_back_when_cluster_ids_are_malformed():
    client = Mock()
    client.chat.completions.create.return_value = _completion(
        '{"p_true":0.7,"rationale":"Mostly supported.","step_type":"arithmetic","sample_cluster_ids":[0]}'
    )
    service = LLMService(client=client)

    review = service.verify_step(
        "What is 2 + 3?",
        GeneratedStep(1, "2 + 3 = 5", "arithmetic"),
        [],
        ["2 plus 3 is 5", "The sum is 5"],
    )

    assert review.p_true == 0.7
    assert review.sample_cluster_ids is None


def test_service_requires_api_key_without_injected_client():
    with pytest.raises(ValueError, match="LLM_API_KEY"):
        LLMService()


def test_step_token_statistics_excludes_json_wrapper_tokens():
    raw_content = '{"step_text":"42 apples"}'
    prefix = '{"step_text":"'
    suffix = '"}'
    top_logprobs = [
        SimpleNamespace(logprob=math.log(0.75)),
        SimpleNamespace(logprob=math.log(0.25)),
    ]
    token_parts = [
        (prefix, -0.01),
        ("42", -0.2),
        (" apples", -0.4),
        (suffix, -0.02),
    ]
    tokens = [
        SimpleNamespace(
            token=text,
            bytes=list(text.encode("utf-8")),
            logprob=logprob,
            top_logprobs=top_logprobs,
        )
        for text, logprob in token_parts
    ]
    choice = SimpleNamespace(
        logprobs=SimpleNamespace(content=tokens),
    )

    mean_logprob, token_entropy = LLMService._step_token_statistics(
        raw_content,
        choice,
    )

    assert mean_logprob == pytest.approx(-0.3)
    assert token_entropy == pytest.approx(0.811278, abs=1e-5)