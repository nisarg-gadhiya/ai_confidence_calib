from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4


CALIBRATION_STORE_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "calibration_runs.json"
)
_STORE_LOCK = Lock()


def _response_data(response: Any) -> dict[str, Any]:
    if isinstance(response, dict):
        return response
    model_dump = getattr(response, "model_dump", None)
    if callable(model_dump):
        return model_dump(mode="json")
    raise TypeError("Gateway response must be a mapping or a Pydantic model.")


def _category_for(response: dict[str, Any]) -> str:
    if "reasoning" in response:
        return "arithmetic"
    if "rules" in response:
        return "logical"
    if "steps" in response:
        return "factual"
    raise ValueError("Gateway response does not contain a recognized pipeline shape.")


def _calibration_steps(response: dict[str, Any]) -> list[dict[str, Any]]:
    if "reasoning" in response:
        return [
            {
                "step_id": step["step_number"],
                "text": step["step_text"],
                "step_type": step["step_type"],
                "verification_score": step.get("verification_score"),
                "consistency_score": step.get("consistency_score"),
                "sample_agreement_score": step.get("sample_agreement_score"),
                "fused_confidence": step.get("fused_confidence"),
                "sample_count": step.get("sample_count"),
            }
            for step in response["reasoning"]
        ]

    calibration_steps = []
    for step in response.get("steps", []):
        claims = step.get("claims", [])
        if not claims:
            calibration_steps.append(
                {
                    "step_id": step.get("step_id"),
                    "text": step.get("text"),
                    "reasoning_operation": step.get("reasoning_operation"),
                    "sample_count": step.get("sample_count"),
                }
            )
            continue

        for claim in claims:
            verification = claim.get("verification", {})
            calibration_steps.append(
                {
                    "step_id": step.get("step_id"),
                    "claim_id": claim.get("claim_id"),
                    "text": claim.get("text"),
                    "essential": claim.get("essential"),
                    "verification_verdict": verification.get("verdict"),
                    "logical_validity_score": verification.get("logical_validity_score"),
                    "evidence_score": verification.get("evidence_score"),
                    "self_verification_score": claim.get("self_verification_score"),
                    "consistency_score": claim.get("consistency_score"),
                    "calibrated_probability": claim.get("calibrated_probability"),
                    "sources": [
                        {
                            "source_id": source.get("source_id"),
                            "title": source.get("title"),
                            "url": source.get("url"),
                            "domain": source.get("domain"),
                        }
                        for source in claim.get("sources", [])
                    ],
                    "sample_count": step.get("sample_count"),
                }
            )
    return calibration_steps


def load_calibration_runs() -> list[dict[str, Any]]:
    with _STORE_LOCK:
        if not CALIBRATION_STORE_PATH.exists():
            return []
        records = json.loads(CALIBRATION_STORE_PATH.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("Calibration JSON store must contain an array.")
    return records


def save_calibration_run(question: str, response: Any) -> None:
    response_data = _response_data(response)
    confidence = response_data.get("final_answer_confidence")
    if confidence is None:
        confidence = response_data.get("answer_confidence")
    record = {
        "run_id": str(uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "category": _category_for(response_data),
        "question": question,
        "answer": response_data.get("final_answer"),
        "confidence": confidence,
        "calibration_status": (
            response_data.get("calibration_status")
            or response_data.get("confidence_method")
        ),
        "pipeline_output": response_data,
        "steps": _calibration_steps(response_data),
    }

    with _STORE_LOCK:
        if CALIBRATION_STORE_PATH.exists():
            records = json.loads(CALIBRATION_STORE_PATH.read_text(encoding="utf-8"))
            if not isinstance(records, list):
                raise ValueError("Calibration JSON store must contain an array.")
        else:
            records = []
        records.append(record)

        CALIBRATION_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = CALIBRATION_STORE_PATH.with_suffix(".json.tmp")
        temporary_path.write_text(
            json.dumps(records, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(CALIBRATION_STORE_PATH)
