from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.schemas.reasoning import InferenceRequest
from gateway.router import LogicalPipelineNotImplementedError, route_question


router = APIRouter(tags=["gateway"])


@router.post("/ask")
def ask_endpoint(payload: InferenceRequest):
    try:
        return route_question(
            payload.question,
            num_consistency_samples=payload.num_consistency_samples,
        )
    except LogicalPipelineNotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive API guard
        raise HTTPException(
            status_code=500,
            detail="Question routing failed.",
        ) from exc
