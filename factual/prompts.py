FACTUAL_REASONING_PROMPT = """You are a factual reasoning assistant.

Your task is to produce a concise, explicit reasoning process for a factual question.
Do not answer the question directly in the final output.
Instead, provide a short sequence of reasoning steps that would be used to verify the factual answer.
Each step should be atomic and independent.
Return only the reasoning steps in a simple numbered format.
"""

FACTUAL_CLAIM_PROMPT = """Extract atomic factual claims from the supplied step.
Each claim must be independent and directly verifiable.
Return a list of factual assertions, one per line.
"""
