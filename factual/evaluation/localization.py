from __future__ import annotations


def localize_riskiest_step(steps: list[dict]) -> int | None:
    if not steps:
        return None
    return min(steps, key=lambda step: float(step.get("calibrated_probability", 1.0)))["step_id"]
