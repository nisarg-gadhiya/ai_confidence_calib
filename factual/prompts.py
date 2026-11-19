FACTUAL_REASONING_PROMPT = """You answer factual questions using known information.

Return one JSON object with this shape:
{"steps":[{"step_number":1,"text":"...","step_type":"factual_recall"}],
 "final_answer":"..."}
Each step must be an object with an integer "step_number" and non-empty string
"text". Use "factual_recall" as the step_type unless another existing type fits.
Each step must be a concise, verifiable factual statement that supports the answer.
Do not write instructions or plans such as "identify", "recall", or "verify".
The final_answer must directly answer the user's question, not describe how to find
the answer. If you cannot determine the answer, say so plainly.
"""

FACTUAL_CLAIM_PROMPT = """Extract atomic factual claims from the supplied step.
Each claim must be independent and directly verifiable.
Return a list of factual assertions, one per line.
"""
