from __future__ import annotations

import re
from typing import Dict, List, Optional


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug: lowercase, hyphen-separated, alphanumeric.
    Maintains ASCII letters and numbers and replaces spaces/invalid chars with hyphens.
    """
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = text.strip("-")
    return text


def clamp(text: str, max_len: int) -> str:
    """Clamp text to max_len without cutting words mid-way when possible."""
    if len(text) <= max_len:
        return text
    sliced = text[:max_len].rstrip()
    last_space = sliced.rfind(" ")
    if last_space == -1:
        return sliced
    return sliced[:last_space]


def generate_metadata(
    topic: str,
    heading: str,
    target_audience: Optional[str],
    outline_h2: List[str],
    research_keywords: Optional[List[str]] = None,
) -> Dict[str, object]:
    """Generate basic SEO metadata heuristically using inputs and outline.

    This avoids extra model calls and produces sensible defaults. Content generation
    will naturally reinforce keywords again.
    """
    base_keyword = slugify(topic).replace("-", " ")

    # Title tag: 50-60 chars recommended
    title_candidate = heading if heading else topic
    title_tag = clamp(title_candidate, 60)

    # Meta description: 150-160 chars
    audience_note = f" for {target_audience}" if target_audience else ""
    meta_description = clamp(
        f"Comprehensive guide to {topic}{audience_note}. Learn key concepts, best practices, and actionable tips.",
        160,
    )

    # Keywords
    primary_keywords: List[str] = []
    if research_keywords:
        primary_keywords = list(dict.fromkeys(research_keywords))[:5]
    if not primary_keywords:
        primary_keywords = [
            base_keyword,
            f"what is {base_keyword}",
            f"{base_keyword} guide",
        ][:3]

    secondary_keywords = [
        f"{base_keyword} best practices",
        f"{base_keyword} tutorial",
        f"{base_keyword} examples",
        f"{base_keyword} tools",
        f"{base_keyword} checklist",
        f"{base_keyword} tips",
    ][:8]

    # URL slug
    url_slug = slugify(heading or topic)

    # Table of contents from H2 outline
    table_of_contents = outline_h2

    return {
        "title_tag": title_tag,
        "meta_description": meta_description,
        "primary_keywords": primary_keywords,
        "secondary_keywords": secondary_keywords,
        "url_slug": url_slug,
        "table_of_contents": table_of_contents,
    }
