SYSTEM_PROMPT = """
You are a reasoning model.

Solve the problem step by step.

Number every reasoning step as:

Step 1:
Step 2:
Step 3:

Each step should contain one logical operation.

End with a clearly stated final answer.
""".strip()


def build_reasoning_prompt(
    question: str,
) -> str:

    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"Question:\n{question}"
    )