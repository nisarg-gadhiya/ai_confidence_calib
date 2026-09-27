from fastapi import APIRouter

from app.services.evaluation_service import (
    localization_metrics,
)


router = APIRouter(
    prefix="/evaluation",
    tags=["evaluation"],
)


@router.post("/localization")
def evaluate_localization(
    ranked_steps: list[int],
    true_error_step: int,
):

    return localization_metrics(
        ranked_steps,
        true_error_step,
    )