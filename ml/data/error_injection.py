import re
from dataclasses import dataclass
from decimal import Decimal


NUMBER_PATTERN = re.compile(r"(?<![\w.])-?\d+(?:,\d{3})*(?:\.\d+)?")


@dataclass
class InjectedReasoning:
	steps: list[str]
	true_error_step: int
	original_step: str
	corrupted_step: str


def inject_numeric_step_error(
	steps: list[str],
	step_number: int,
	delta: int = 1,
) -> InjectedReasoning:
	if not 1 <= step_number <= len(steps):
		raise ValueError("step_number must identify an existing 1-based step")
	if delta == 0:
		raise ValueError("delta must be non-zero")

	index = step_number - 1
	original = steps[index]
	matches = list(NUMBER_PATTERN.finditer(original))
	if not matches:
		raise ValueError("The selected step contains no numeric value to perturb")

	match = matches[-1]
	original_number = Decimal(match.group().replace(",", ""))
	perturbed_number = original_number + delta
	replacement = format(perturbed_number, "f")
	if "." in replacement:
		replacement = replacement.rstrip("0").rstrip(".")

	corrupted = original[:match.start()] + replacement + original[match.end():]
	corrupted_steps = list(steps)
	corrupted_steps[index] = corrupted
	return InjectedReasoning(
		steps=corrupted_steps,
		true_error_step=step_number,
		original_step=original,
		corrupted_step=corrupted,
	)
