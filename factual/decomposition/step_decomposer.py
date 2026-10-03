from __future__ import annotations

import re


STEP_PATTERN = re.compile(r"(?:Step\s*)?(\d+)[:.)-]\s*(.+)", re.IGNORECASE)


def decompose_reasoning(reasoning_steps: list[str]) -> list[dict]:
    steps: list[dict] = []
    for index, item in enumerate(reasoning_steps, start=1):
        text = str(item).strip()
        if not text:
            continue
        match = STEP_PATTERN.match(text)
        if match:
            step_id = int(match.group(1))
            parsed_text = match.group(2).strip()
        else:
            step_id = index
            parsed_text = text
        steps.append({"step_id": step_id, "text": parsed_text})
    if not steps:
        steps.append({"step_id": 1, "text": "Identify the key fact being asked."})
    return steps
