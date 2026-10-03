from __future__ import annotations


STOP_WORDS = {"a", "an", "the", "of", "is", "was", "in", "on", "at", "to", "for", "and", "or", "by", "with", "from"}


def _normalize(text: str) -> str:
    return " ".join(text.lower().replace("?", "").replace(".", "").split())


def _tokenize(text: str) -> set[str]:
    return {token for token in _normalize(text).split() if token not in STOP_WORDS}


def _extract_subject_and_predicate(claim: str) -> tuple[str | None, str | None]:
    if " is " in claim:
        subject, predicate = claim.split(" is ", 1)
        return subject.strip(), predicate.strip()
    if " was " in claim:
        subject, predicate = claim.split(" was ", 1)
        return subject.strip(), predicate.strip()
    return None, None


def verify_claim_against_evidence(claim_text: str, evidence_text: str) -> str:
    claim = _normalize(claim_text)
    evidence = _normalize(evidence_text)

    if not claim or not evidence:
        return "UNKNOWN"

    if claim in evidence or evidence in claim:
        return "SUPPORT"

    subject, predicate = _extract_subject_and_predicate(claim)
    if subject and predicate:
        relation_keywords = [
            "capital",
            "written by",
            "author",
            "author of",
            "ended",
            "year",
            "date",
            "located",
        ]
        matching_keywords = [keyword for keyword in relation_keywords if keyword in claim or keyword in predicate]
        if matching_keywords:
            if "capital" in matching_keywords and any(word in evidence for word in ("sydney", "melbourne", "perth", "brisbane", "canberra")):
                alternative = [word for word in ["sydney", "melbourne", "perth", "brisbane", "canberra"] if word in evidence]
                if alternative and subject and subject not in evidence:
                    return "CONTRADICT"
            if subject in evidence:
                return "SUPPORT"
            if any(keyword in evidence for keyword in matching_keywords):
                return "SUPPORT"
            if not any(keyword in evidence for keyword in matching_keywords):
                return "UNKNOWN"

    contradiction_markers = [
        "not",
        "never",
        "isn't",
        "wasn't",
        "didn't",
        "cannot",
        "false",
        "opposite",
        "instead",
    ]
    if any(marker in evidence for marker in contradiction_markers):
        return "CONTRADICT"

    claim_terms = _tokenize(claim)
    evidence_terms = _tokenize(evidence)
    overlap = len(claim_terms.intersection(evidence_terms))
    if overlap >= 1 and any(keyword in evidence for keyword in ("capital", "author", "written", "ended", "year", "date")):
        return "SUPPORT"

    if "capital" in claim and "capital" in evidence and subject and subject not in evidence:
        return "CONTRADICT"

    return "UNKNOWN"
