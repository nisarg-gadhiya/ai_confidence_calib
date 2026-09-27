import re
from dataclasses import dataclass


@dataclass
class ParsedStep:
    step_number: int
    text: str
    step_type: str = "unknown"


STEP_PATTERN = re.compile(
    r"^\s*(?:Step\s*)?(\d+)\s*[:.)-]\s*(.+?)\s*$",
    re.IGNORECASE,
)


def decompose_reasoning(
    text: str,
) -> list[ParsedStep]:

    steps: list[ParsedStep] = []

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        match = STEP_PATTERN.match(line)

        if match:

            number = int(match.group(1))

            step_text = match.group(2).strip()

            steps.append(
                ParsedStep(
                    step_number=number,
                    text=step_text,
                    step_type=classify_step(step_text),
                )
            )

    if not steps and text.strip():

        steps.append(
            ParsedStep(
                step_number=1,
                text=text.strip(),
                step_type="unknown",
            )
        )

    return steps


def classify_step(
    text: str,
) -> str:

    lowered = text.lower()

    if any(
        word in lowered
        for word in (
            "calculate",
            "multiply",
            "divide",
            "subtract",
            "add",
        )
    ):
        return "calculation"

    if any(
        word in lowered
        for word in (
            "therefore",
            "answer",
            "result",
        )
    ):
        return "conclusion"

    if any(
        word in lowered
        for word in (
            "given",
            "identify",
            "need",
        )
    ):
        return "setup"

    return "reasoning"