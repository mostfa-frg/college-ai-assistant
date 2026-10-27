"""Optional Tavily web search for assignment evidence.

This module is deliberately optional: without TAVILY_API_KEY, callers get no results
and local course-material retrieval continues normally.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from college_assistant.config import TAVILY_API_KEY, WEB_RESEARCH_ENABLED


@dataclass(frozen=True)
class WebEvidence:
    """A concise web result that can be passed through the same evidence pipeline."""
    text: str
    source: str
    location: str


def search_web_evidence(query: str, max_results: int = 3) -> list[WebEvidence]:
    """Search Tavily and return source-labelled snippets; fail closed on service errors."""
    if not WEB_RESEARCH_ENABLED or not TAVILY_API_KEY or not query.strip():
        return []

    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query.strip()[:500],
        "search_depth": "basic",
        "max_results": max(1, min(int(max_results), 5)),
        "include_answer": False,
        "include_raw_content": False,
    }
    request = Request(
        "https://api.tavily.com/search",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=12) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        # Web search is a fallback, not a reason to fail assignment generation.
        return []

    results = []
    for item in data.get("results", [])[:payload["max_results"]]:
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        snippet = str(item.get("content") or "").strip()
        if not title or not url.startswith(("https://", "http://")) or not snippet:
            continue
        results.append(WebEvidence(
            text=snippet[:1800],
            source=title[:180],
            location=url,
        ))
    return results
