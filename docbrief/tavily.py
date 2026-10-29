"""Optional live web context via the Tavily Search API (used only if TAVILY_API_KEY is set)."""
from __future__ import annotations

import requests

from .types import Source


def tavily_search(query: str, api_key: str, max_results: int = 3) -> list[Source]:
    r = requests.post(
        "https://api.tavily.com/search",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"query": query, "max_results": max_results, "search_depth": "basic"},
        timeout=30,
    )
    r.raise_for_status()
    out = []
    for i, item in enumerate(r.json().get("results", [])[:max_results], 1):
        out.append(Source(label=f"W{i}", page=None, text=(item.get("content") or "")[:900], url=item.get("url", "")))
    return out
