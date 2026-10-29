"""Live web search via the Tavily Search API.

Used at runtime for (1) the "Fact-check with the web" view and (2) the optional web context in Q&A.
Needs TAVILY_API_KEY; nothing is called without it.
"""
from __future__ import annotations

from typing import Callable

import requests

from .types import Source

TAVILY_URL = "https://api.tavily.com/search"


def tavily_search(query: str, api_key: str, max_results: int = 3, start_label: int = 1, topic: str = "general") -> list[Source]:
    """Run one Tavily search and return the hits as Source objects labelled W{start_label}, W{start_label+1}, …"""
    r = requests.post(
        TAVILY_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"query": query[:380], "max_results": max_results, "search_depth": "basic", "topic": topic},
        timeout=30,
    )
    r.raise_for_status()
    out, seen = [], set()
    items = []
    for item in r.json().get("results", []):
        u = (item.get("url") or "").split("?")[0]
        if u not in seen:
            seen.add(u)
            items.append({**item, "url": u})
    for i, item in enumerate(items[:max_results], start_label):
        out.append(Source(label=f"W{i}", page=None, text=(item.get("content") or "")[:900], url=item.get("url", ""), title=(item.get("title") or "")[:140]))
    return out


SearchFn = Callable[[str, int], list[Source]]  # (query, start_label) -> sources


def make_search(api_key: str, max_results: int = 3) -> SearchFn:
    return lambda q, start=1: tavily_search(q, api_key, max_results=max_results, start_label=start)
