from __future__ import annotations

from urllib.parse import urlparse

from factual.generation.reasoning import get_factual_llm_service
from factual.retrieval.evidence_retrieval import _relevance_score


def search_sources(claim_text: str, question: str | None = None) -> list[dict]:
    """Search the web through the shared OpenAI client and return cited sources."""
    claim_text = (claim_text or "").strip()
    if not claim_text:
        return []

    llm = get_factual_llm_service()
    if llm is None:
        return []

    query = f"Question: {question}\nClaim to verify: {claim_text}" if question else claim_text
    citations = llm.search_web(query)
    sources: list[dict] = []
    for index, citation in enumerate(citations):
        url = citation.get("url", "")
        parsed_url = urlparse(url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname:
            continue
        domain = parsed_url.hostname.lower().removeprefix("www.")
        source_type = (
            "government"
            if domain.startswith("gov.") or ".gov." in domain or domain.endswith(".gov")
            else "academic"
            if ".edu" in domain
            else "general"
        )
        text = str(citation.get("text", "")).strip()
        if not text:
            continue
        sources.append(
            {
                "source_id": f"web_{index + 1}",
                "title": citation.get("title") or domain,
                "url": url,
                "domain": domain,
                "source_type": source_type,
                "text": text,
                "text_origin": "citation_linked_model_summary",
                "retrieval_score": _relevance_score(claim_text, f"{citation.get('title', '')} {text}"),
            }
        )

    return sources
