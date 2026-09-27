import json
import math
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI


@dataclass
class GeneratedStep:
    step_number: int
    text: str
    step_type: str = "other"


@dataclass
class LLMResponse:
    text: str
    final_answer: str | None = None
    steps: list[GeneratedStep] = field(default_factory=list)


@dataclass
class StepAssessment:
    p_true: float
    rationale: str
    step_type: str
    sample_cluster_ids: list[int] | None


@dataclass
class StepContinuation:
    text: str
    mean_token_logprob: float | None = None
    token_entropy: float | None = None


@dataclass
class JSONCompletion:
    data: dict[str, Any]
    raw_content: str
    choice: Any


class LLMService:
    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        client: OpenAI | None = None,
    ):
        if provider.lower() != "openai":
            raise ValueError(
                f"Unsupported LLM provider: {provider}. Use 'openai'."
            )

        if client is None and not api_key:
            raise ValueError(
                "Set LLM_API_KEY in backend/.env before running inference."
            )

        self.client = client or OpenAI(api_key=api_key)
        self.model = model

    def generate_reasoning(
        self,
        question: str,
    ) -> LLMResponse:
        return self._generate(question, prefix=None)

    def generate_with_prefix(
        self,
        question: str,
        prefix: str,
    ) -> LLMResponse:
        return self._generate(question, prefix=prefix)

    def generate_step_continuations(
        self,
        question: str,
        preceding_steps: list[GeneratedStep],
        next_step_number: int,
        num_samples: int,
    ) -> list[StepContinuation]:
        messages = [
            {
                "role": "system",
                "content": (
                    "Continue a solution from the supplied fixed prefix. "
                    "Generate exactly one next reasoning step and do not "
                    "rewrite or reassess earlier steps. Return JSON with a "
                    "non-empty 'step_text' string. Keep each sample focused "
                    "on the next inference only."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "question": question,
                        "preceding_steps": [
                            {
                                "step_number": step.step_number,
                                "text": step.text,
                            }
                            for step in preceding_steps
                        ],
                        "next_step_number": next_step_number,
                    }
                ),
            },
        ]
        responses = self._create_json_completion(
            messages,
            temperature=0.8,
            num_samples=num_samples,
            include_logprobs=True,
        )

        samples: list[StepContinuation] = []
        for response in responses:
            text = response.data.get("step_text")
            if not isinstance(text, str) or not text.strip():
                raise ValueError("The model returned an empty step continuation.")
            mean_logprob, token_entropy = self._step_token_statistics(
                response.raw_content,
                response.choice,
            )
            samples.append(
                StepContinuation(
                    text=text.strip(),
                    mean_token_logprob=mean_logprob,
                    token_entropy=token_entropy,
                )
            )
        return samples

    def verify_step(
        self,
        question: str,
        step: GeneratedStep,
        preceding_steps: list[GeneratedStep],
        sample_continuations: list[str],
    ) -> StepAssessment:

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an independent step-level verifier. Evaluate the "
                    "proposed step given the question and fixed preceding steps. "
                    "Use the candidate continuations as sample-conditioned "
                    "evidence, not as ground truth. Return JSON containing "
                    "p_true (0 to 1), a concise rationale, step_type chosen "
                    "from arithmetic, unit_conversion, factual_recall, "
                    "logical_inference, setup, conclusion, or other, and "
                    "sample_cluster_ids: one non-negative integer per "
                    "candidate continuation. Assign the same id only when two "
                    "continuations express the same next-step meaning; be "
                    "conservative about merging."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "question": question,
                        "preceding_steps": [
                            {
                                "step_number": prior.step_number,
                                "text": prior.text,
                            }
                            for prior in preceding_steps
                        ],
                        "proposed_step": {
                            "step_number": step.step_number,
                            "text": step.text,
                        },
                        "candidate_continuations": sample_continuations,
                    }
                ),
            },
        ]
        result = self._create_json_completion(
            messages,
            temperature=0,
            num_samples=1,
        )[0].data

        p_true = result.get("p_true")
        cluster_ids = result.get("sample_cluster_ids")
        if not isinstance(p_true, (int, float)) or isinstance(p_true, bool):
            raise ValueError("The model returned no valid p_true score.")
        valid_clusters = (
            isinstance(cluster_ids, list)
            and len(cluster_ids) == len(sample_continuations)
            and all(
                isinstance(cluster_id, int)
                and not isinstance(cluster_id, bool)
                and cluster_id >= 0
                for cluster_id in cluster_ids
            )
        )
        if not valid_clusters:
            cluster_ids = None

        rationale = result.get("rationale")
        if not isinstance(rationale, str):
            rationale = "No verification rationale was returned."

        return StepAssessment(
            p_true=max(0.0, min(1.0, float(p_true))),
            rationale=rationale,
            step_type=normalize_step_type(result.get("step_type")),
            sample_cluster_ids=cluster_ids,
        )

    def _generate(
        self,
        question: str,
        prefix: str | None,
    ) -> LLMResponse:
        user_content = {"question": question}
        if prefix:
            user_content["reasoning_prefix"] = prefix

        messages = [
            {
                "role": "system",
                "content": (
                    "Solve the user's question. Return JSON with a 'steps' "
                    "array of objects containing integer 'step_number' and "
                    "concise user-facing 'text' and 'step_type' chosen from "
                    "arithmetic, unit_conversion, factual_recall, "
                    "logical_inference, setup, conclusion, or other, plus a "
                    "string 'final_answer'. Show brief, verifiable work rather "
                    "than hidden chain-of-thought. Use clear ordered steps."
                ),
            },
            {"role": "user", "content": json.dumps(user_content)},
        ]
        responses = self._create_json_completion(
            messages,
            temperature=0,
            num_samples=1,
        )

        steps, answer = self._parse_reasoning(responses[0].data)
        text = "\n".join(
            f"Step {step.step_number}: {step.text}"
            for step in steps
        )

        return LLMResponse(
            text=text,
            final_answer=answer,
            steps=steps,
        )

    def _create_json_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        num_samples: int,
        include_logprobs: bool = False,
    ) -> list[JSONCompletion]:
        request = {
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": temperature,
            "n": num_samples,
        }
        if include_logprobs:
            request["logprobs"] = True
            request["top_logprobs"] = 5

        completion = self.client.chat.completions.create(
            model=self.model,
            **request,
        )

        results: list[JSONCompletion] = []
        for choice in completion.choices:
            content = choice.message.content
            if not content:
                raise ValueError("The model returned an empty response.")
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                raise ValueError("The model response must be a JSON object.")
            results.append(
                JSONCompletion(
                    data=parsed,
                    raw_content=content,
                    choice=choice,
                )
            )

        if len(results) != num_samples:
            raise ValueError("The model returned an unexpected number of samples.")

        return results

    @staticmethod
    def _step_token_statistics(
        raw_content: str,
        choice: Any,
    ) -> tuple[float | None, float | None]:
        logprobs = getattr(choice, "logprobs", None)
        tokens = getattr(logprobs, "content", None)
        if not tokens:
            return None, None

        raw_bytes = raw_content.encode("utf-8")
        marker = b'"step_text"'
        marker_start = raw_bytes.find(marker)
        if marker_start < 0:
            return None, None
        value_start = raw_bytes.find(b'"', raw_bytes.find(b":", marker_start) + 1)
        if value_start < 0:
            return None, None
        value_start += 1

        value_end = value_start
        escaped = False
        while value_end < len(raw_bytes):
            current_byte = raw_bytes[value_end]
            if escaped:
                escaped = False
            elif current_byte == ord("\\"):
                escaped = True
            elif current_byte == ord('"'):
                break
            value_end += 1

        if value_end >= len(raw_bytes):
            return None, None

        token_logprobs: list[float] = []
        token_entropies: list[float] = []
        byte_offset = 0
        for token in tokens:
            token_bytes = getattr(token, "bytes", None)
            if token_bytes is None:
                token_bytes = list(getattr(token, "token", "").encode("utf-8"))
            token_end = byte_offset + len(token_bytes)
            if token_end > value_start and byte_offset < value_end:
                token_logprob = getattr(token, "logprob", None)
                if isinstance(token_logprob, (int, float)):
                    token_logprobs.append(float(token_logprob))

                alternatives = getattr(token, "top_logprobs", None) or []
                alternative_logprobs = [
                    item.logprob
                    for item in alternatives
                    if isinstance(getattr(item, "logprob", None), (int, float))
                ]
                if len(alternative_logprobs) > 1:
                    probabilities = [math.exp(value) for value in alternative_logprobs]
                    mass = sum(probabilities)
                    if mass > 0:
                        entropy = -sum(
                            (probability / mass) * math.log(probability / mass)
                            for probability in probabilities
                            if probability > 0
                        )
                        token_entropies.append(
                            entropy / math.log(len(probabilities))
                        )
            byte_offset = token_end

        if byte_offset != len(raw_bytes):
            return None, None

        mean_logprob = (
            sum(token_logprobs) / len(token_logprobs)
            if token_logprobs
            else None
        )
        mean_entropy = (
            sum(token_entropies) / len(token_entropies)
            if token_entropies
            else None
        )
        return mean_logprob, mean_entropy

    @staticmethod
    def _parse_reasoning(
        response: dict[str, Any],
    ) -> tuple[list[GeneratedStep], str | None]:
        steps = response.get("steps")
        if not isinstance(steps, list) or not steps:
            raise ValueError("The model returned no reasoning steps.")

        parsed_steps: list[GeneratedStep] = []
        for index, step in enumerate(steps, start=1):
            if not isinstance(step, dict):
                continue
            text = step.get("text")
            if not isinstance(text, str) or not text.strip():
                continue
            number = step.get("step_number", index)
            if not isinstance(number, int):
                number = index
            parsed_steps.append(
                GeneratedStep(
                    step_number=number,
                    text=text.strip(),
                    step_type=normalize_step_type(step.get("step_type")),
                )
            )

        if not parsed_steps:
            raise ValueError("The model returned no usable reasoning steps.")

        answer = response.get("final_answer")
        if not isinstance(answer, str) or not answer.strip():
            answer = None

        return parsed_steps, answer


def normalize_step_type(value: Any) -> str:
    if not isinstance(value, str):
        return "other"

    normalized = value.strip().lower().replace(" ", "_")
    aliases = {
        "calculation": "arithmetic",
        "arithmetic_computation": "arithmetic",
        "fact": "factual_recall",
        "inference": "logical_inference",
        "logic": "logical_inference",
        "unit_conversion": "unit_conversion",
        "setup": "setup",
        "conclusion": "conclusion",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in {
        "arithmetic",
        "unit_conversion",
        "factual_recall",
        "logical_inference",
        "setup",
        "conclusion",
        "other",
    }:
        return "other"
    return normalized


    #mock service for testing purposes