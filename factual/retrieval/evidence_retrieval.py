from __future__ import annotations

import re


STOP_WORDS = {"a", "an", "the", "of", "is", "was", "in", "on", "at", "to", "for", "and", "or", "by", "with", "from"}


def _relevance_score(claim_text: str, source_text: str) -> float:
    claim_terms = {
        token for token in re.findall(r"[\w'-]+", claim_text.lower())
        if token not in STOP_WORDS
    }
    source_terms = {
        token for token in re.findall(r"[\w'-]+", (source_text or "").lower())
        if token not in STOP_WORDS
    }
    if not claim_terms or not source_terms:
        return 0.0
    overlap = len(claim_terms & source_terms)
    if overlap == 0:
        return 0.0
    coverage = overlap / len(claim_terms)
    jaccard = overlap / len(claim_terms | source_terms)
    return min(1.0, (coverage + jaccard) / 2.0)


def retrieve_evidence_for_claim(claim_text: str, sources: list[dict]) -> list[dict]:
    evidence: list[dict] = []
    for source in sources:
        if source.get("status") == "REJECT":
            continue
        text = str(source.get("text") or "").strip()
        relevance = _relevance_score(claim_text, text)
        if relevance < 0.2:
            continue
        evidence.append(
            {
                "evidence_id": f"e_{source.get('source_id', 'x')}",
                "claim_id": f"claim_{source.get('source_id', 'x')}",
                "source_id": source.get("source_id", "unknown"),
                "title": source.get("title", ""),
                "url": source.get("url"),
                "domain": source.get("domain", ""),
                "text": text,
                "text_origin": source.get("text_origin", "unknown"),
                "relevance_score": relevance,
                "source_reliability": float(source.get("reliability_score", 0.0)),
                "status": source.get("status", "KEEP"),
            }
        )
    return evidence
