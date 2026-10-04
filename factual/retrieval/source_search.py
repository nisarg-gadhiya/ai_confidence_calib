from __future__ import annotations

import ipaddress
import logging
import re
import socket
from functools import lru_cache
from html.parser import HTMLParser
from urllib.parse import urlparse
from urllib.parse import urljoin

import httpx

from factual.generation.reasoning import get_factual_llm_service
from factual.retrieval.evidence_retrieval import _relevance_score

logger = logging.getLogger(__name__)
MAX_PAGE_FETCHES_PER_CLAIM = 2
MAX_PAGE_BYTES = 1_000_000
MAX_PAGE_TEXT_CHARS = 20_000


class _ReadableTextParser(HTMLParser):
    _ignored_tags = {"script", "style", "noscript", "svg", "nav", "footer", "header"}
    _block_tags = {"article", "blockquote", "br", "div", "h1", "h2", "h3", "h4", "li", "p", "section"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored_stack: list[str] = []

    def handle_starttag(self, tag: str, _attrs) -> None:
        if self.ignored_stack:
            if tag in self._ignored_tags:
                self.ignored_stack.append(tag)
            return
        if tag in self._ignored_tags:
            self.ignored_stack.append(tag)
        elif tag in self._block_tags:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self.ignored_stack:
            for index in range(len(self.ignored_stack) - 1, -1, -1):
                if self.ignored_stack[index] == tag:
                    del self.ignored_stack[index:]
                    break
            return
        if tag in self._block_tags:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.ignored_stack:
            self.parts.append(data)


def _is_public_http_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    if parsed.username or parsed.password:
        return False
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        addresses = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
    except (OSError, ValueError):
        return False
    return bool(addresses) and all(
        ipaddress.ip_address(address[4][0].split("%", 1)[0]).is_global
        for address in addresses
    )


@lru_cache(maxsize=128)
def _fetch_page_text(url: str) -> str:
    current_url = url
    headers = {"User-Agent": "FactualEvidenceBot/1.0"}
    try:
        with httpx.Client(timeout=3.0, follow_redirects=False, headers=headers) as client:
            for _ in range(4):
                if not _is_public_http_url(current_url):
                    return ""
                with client.stream("GET", current_url) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            return ""
                        current_url = urljoin(current_url, location)
                        continue
                    if response.status_code < 200 or response.status_code >= 300:
                        return ""
                    content_type = response.headers.get("content-type", "").lower()
                    is_html = "text/html" in content_type or "application/xhtml+xml" in content_type
                    if not is_html and "text/plain" not in content_type:
                        return ""

                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) >= MAX_PAGE_BYTES:
                            del body[MAX_PAGE_BYTES:]
                            break
                    encoding = response.encoding or "utf-8"
                    content = bytes(body).decode(encoding, errors="replace")
                    if is_html:
                        parser = _ReadableTextParser()
                        parser.feed(content)
                        content = "\n".join(
                            line.strip()
                            for line in "".join(parser.parts).splitlines()
                            if line.strip()
                        )
                    return content[:MAX_PAGE_TEXT_CHARS]
    except (httpx.HTTPError, UnicodeError, LookupError, ValueError):
        return ""
    return ""


def _best_claim_excerpt(claim_text: str, page_text: str) -> str:
    fragments = [
        fragment.strip()
        for fragment in re.split(r"(?<=[.!?])\s+|\n+", page_text)
        if len(fragment.strip()) >= 24
    ]
    ranked = sorted(
        (( _relevance_score(claim_text, fragment), index, fragment) for index, fragment in enumerate(fragments)),
        key=lambda item: (-item[0], item[1]),
    )
    selected = [fragment for score, _index, fragment in ranked[:4] if score > 0]
    return " ".join(selected)[:2000]


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
    pages_attempted = 0
    pages_fetched = 0
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
        text_origin = citation.get("text_origin", "search_source_without_citation")
        if (
            pages_attempted < MAX_PAGE_FETCHES_PER_CLAIM
            and _relevance_score(claim_text, text) < 0.2
        ):
            pages_attempted += 1
            page_text = _fetch_page_text(url)
            excerpt = _best_claim_excerpt(claim_text, page_text) if page_text else ""
            if excerpt:
                text = excerpt
                text_origin = "fetched_webpage_content"
                pages_fetched += 1
        title = citation.get("title") or domain
        sources.append(
            {
                "source_id": f"web_{index + 1}",
                "title": title,
                "url": url,
                "domain": domain,
                "source_type": source_type,
                "text": text,
                "text_origin": text_origin,
                "retrieval_score": _relevance_score(claim_text, f"{title} {text}"),
            }
        )

    logger.info(
        "Factual web search returned %d source URLs; %d valid URLs; %d with text; %d pages fetched.",
        len(citations),
        len(sources),
        sum(bool(source["text"]) for source in sources),
        pages_fetched,
    )
    return sources
