import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.schemas.reasoning import InferenceRequest
from app.services.calibration_store import (
    load_calibration_runs,
    save_calibration_run,
)
from gateway.router import route_question


router = APIRouter(tags=["gateway"])
logger = logging.getLogger(__name__)


@router.post("/ask")
def ask_endpoint(payload: InferenceRequest):
    try:
        result = route_question(
            payload.question,
            num_consistency_samples=payload.num_consistency_samples,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive API guard
        raise HTTPException(
            status_code=500,
            detail="Question routing failed.",
        ) from exc

    try:
        save_calibration_run(payload.question, result)
    except (OSError, TypeError, ValueError) as exc:
        logger.exception("Failed to save step calibration data.")
        raise HTTPException(
            status_code=500,
            detail="The question was processed, but calibration data could not be saved.",
        ) from exc

    return result


@router.get("/runs")
def list_runs_endpoint():
    try:
        return load_calibration_runs()
    except (OSError, ValueError) as exc:
        logger.exception("Failed to read step calibration data.")
        raise HTTPException(
            status_code=500,
            detail="Stored calibration data could not be read.",
        ) from exc
