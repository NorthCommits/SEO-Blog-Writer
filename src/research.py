from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, List, Optional

from tavily import TavilyClient

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cache")
CACHE_FILE = os.path.join(CACHE_DIR, "research_cache.json")


def _ensure_cache() -> None:
    """Ensure cache directory and file exist."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    if not os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)


def _load_cache() -> Dict[str, Any]:
    _ensure_cache()
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(cache: Dict[str, Any]) -> None:
    _ensure_cache()
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _cache_key(topic: str, deep: bool) -> str:
    raw = f"{topic}|{deep}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def perform_research(
    topic: str,
    tavily_api_key: str,
    deep: bool = False,
) -> Dict[str, Any]:
    """Run Tavily search and return structured research data.

    Returns a dict with keys: sources (list), insights (list), keywords (list)
    """
    cache = _load_cache()
    key = _cache_key(topic, deep)
    if key in cache:
        return cache[key]

    client = TavilyClient(api_key=tavily_api_key)

    max_results = 15 if deep else 5
    search_depth = "advanced" if deep else "basic"

    response = client.search(
        query=topic,
        max_results=max_results,
        search_depth=search_depth,
        include_raw_content=deep,
    )

    # Normalize results
    sources: List[Dict[str, Any]] = []
    for item in response.get("results", []):
        sources.append(
            {
                "title": item.get("title") or "",
                "url": item.get("url") or item.get("link") or "",
                "snippet": item.get("content") or item.get("snippet") or "",
                "raw_content": item.get("raw_content") if deep else None,
            }
        )

    # Extract simple insights and keywords heuristically
    insights: List[str] = []
    keywords: List[str] = []
    for s in sources[:8]:
        text = (s.get("title") or "") + " " + (s.get("snippet") or "")
        # crude keyword picks: split and pick mid-long words
        for token in text.split():
            t = token.lower().strip(",.()[]{}:;!?")
            if 5 <= len(t) <= 30 and t.isalpha():
                keywords.append(t)
        if s.get("title"):
            insights.append(s["title"])  # titles often represent key themes

    # de-duplicate while preserving order
    def dedupe(seq: List[str]) -> List[str]:
        seen = set()
        out = []
        for x in seq:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    research = {
        "sources": sources,
        "insights": dedupe(insights)[:20],
        "keywords": dedupe(keywords)[:30],
    }

    cache[key] = research
    _save_cache(cache)

    return research
