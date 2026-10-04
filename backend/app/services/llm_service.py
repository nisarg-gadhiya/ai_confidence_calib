import json
import math
import re
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


def _response_value(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


class LLMService:
    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        client: OpenAI | None = None,
        search_model: str | None = None,
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
        self.search_model = search_model or model

    def generate_reasoning(
        self,
        question: str,
    ) -> LLMResponse:
        return self._generate(question, prefix=None)

    def generate_logical_reasoning(self, question: str) -> LLMResponse:
        from logical.prompts import LOGICAL_REASONING_SYSTEM_PROMPT

        responses = self._create_json_completion(
            [
                {"role": "system", "content": LOGICAL_REASONING_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps({"question": question})},
            ],
            temperature=0,
            num_samples=1,
        )
        steps, answer = self._parse_reasoning(responses[0].data)
        text = "\n".join(f"Step {step.step_number}: {step.text}" for step in steps)
        return LLMResponse(text=text, final_answer=answer, steps=steps)

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

    def search_web(
        self,
        query: str,
        max_results: int = 5,
        model: str | None = None,
    ) -> list[dict[str, str]]:
        response = self.client.responses.create(
            model=model or self.search_model,
            tools=[{"type": "web_search", "search_context_size": "medium"}],
            tool_choice="required",
            include=["web_search_call.action.sources"],
            input=[
                {
                    "role": "system",
                    "content": (
                        "Search the web for reliable sources relevant to the query. "
                        "Summarize only facts supported by the results and cite each "
                        "source in the response. Do not invent citations."
                    ),
                },
                {"role": "user", "content": query},
            ],
        )

        results_by_url: dict[str, dict[str, str]] = {}
        for output_item in _response_value(response, "output", []) or []:
            item_type = _response_value(output_item, "type")
            if item_type == "web_search_call":
                action = _response_value(output_item, "action", {})
                if _response_value(action, "type") != "search":
                    continue
                for source in _response_value(action, "sources", []) or []:
                    url = _response_value(source, "url", "")
                    if not isinstance(url, str) or not url.startswith(("https://", "http://")):
                        continue
                    results_by_url.setdefault(
                        url,
                        {
                            "title": url,
                            "url": url,
                            "text": "",
                            "text_origin": "search_source_without_citation",
                        },
                    )
                continue
            if item_type != "message":
                continue
            for content in _response_value(output_item, "content", []) or []:
                if _response_value(content, "type") != "output_text":
                    continue
                text = _response_value(content, "text", "")
                for annotation in _response_value(content, "annotations", []) or []:
                    if _response_value(annotation, "type") != "url_citation":
                        continue
                    url = _response_value(annotation, "url", "")
                    title = _response_value(annotation, "title", "")
                    if not isinstance(url, str) or not url.startswith(("https://", "http://")):
                        continue
                    excerpt = self._citation_excerpt(
                        text,
                        _response_value(annotation, "start_index", 0),
                        _response_value(annotation, "end_index", 0),
                    )
                    result = results_by_url.setdefault(
                        url,
                        {
                            "title": str(title or url),
                            "url": url,
                            "text": "",
                            "text_origin": "search_source_without_citation",
                        },
                    )
                    if title:
                        result["title"] = str(title)
                    if excerpt:
                        result["text"] = excerpt
                        result["text_origin"] = "citation_linked_model_summary"
        return list(results_by_url.values())[:max_results]

    @staticmethod
    def _citation_excerpt(text: str, start_index: int, end_index: int) -> str:
        if not isinstance(text, str) or not text.strip():
            return ""
        start_index = max(0, min(len(text), int(start_index or 0)))
        end_index = max(start_index, min(len(text), int(end_index or start_index)))

        prefix = text[:start_index].rstrip()
        boundaries = [prefix.rfind(marker) for marker in (". ", "? ", "! ", "\n")]
        excerpt = prefix[max(boundaries) + 1 :].strip()
        if len(excerpt) < 24:
            right = text.find(". ", end_index)
            if right < 0:
                right = min(len(text), end_index + 280)
            excerpt = text[max(0, start_index - 280) : right].strip()
        excerpt = re.sub(r"\s*\[\d+\]\s*", " ", excerpt).strip()
        return excerpt[:1000]

    def assess_factual_claim(
        self,
        question: str,
        claim_text: str,
        evidence: list[dict[str, Any]],
    ) -> dict[str, Any]:
        messages = [
            {
                "role": "system",
                "content": (
                    "Assess a factual claim using only the supplied citation-linked "
                    "evidence. For each evidence item, return SUPPORT only when it "
                    "directly supports the claim, CONTRADICT only when it directly "
                    "conflicts, otherwise UNKNOWN. Do not use prior knowledge. Also "
                    "say whether the claim is essential to answering the question. "
                    "Return JSON with confidence (0 to 1), essential (boolean), and "
                    "source_assessments (objects with source_id and verdict). The "
                    "confidence is a model estimate, not a statistically calibrated "
                    "probability."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "question": question,
                        "claim": claim_text,
                        "evidence": [
                            {
                                "source_id": item.get("source_id"),
                                "title": item.get("title"),
                                "domain": item.get("domain"),
                                "text": str(item.get("text", ""))[:2000],
                            }
                            for item in evidence
                        ],
                    }
                ),
            },
        ]
        result = self._create_json_completion(
            messages,
            temperature=0,
            num_samples=1,
        )[0].data

        confidence = result.get("confidence")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            raise ValueError("The model returned no valid factual confidence estimate.")
        confidence = float(confidence)
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            raise ValueError("Factual confidence estimate must be between 0 and 1.")
        if not evidence:
            confidence = 0.0

        valid_ids = {str(item.get("source_id")) for item in evidence}
        source_assessments = []
        assessments = result.get("source_assessments", [])
        if not isinstance(assessments, list):
            assessments = []
        for item in assessments:
            if not isinstance(item, dict):
                continue
            source_id = str(item.get("source_id", ""))
            verdict = item.get("verdict")
            if source_id in valid_ids and isinstance(verdict, str) and verdict in {"SUPPORT", "CONTRADICT", "UNKNOWN"}:
                source_assessments.append({"source_id": source_id, "verdict": verdict})

        return {
            "confidence": confidence,
            "essential": result.get("essential") is True,
            "source_assessments": source_assessments,
        }

    def classify_question(self, question: str):
        from gateway.prompts import CLASSIFICATION_SYSTEM_PROMPT
        from gateway.schemas import QuestionClassification

        schema = QuestionClassification.model_json_schema()
        schema["additionalProperties"] = False

        messages = [
            {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "question_classification",
                    "schema": schema,
                    "strict": True,
                },
            },
        )

        content = completion.choices[0].message.content
        if not content:
            raise ValueError("The model returned an empty classification response.")

        try:
            parsed = json.loads(content)
            return QuestionClassification.model_validate(parsed)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("Question classification validation failed.") from exc

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