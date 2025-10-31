from __future__ import annotations

from typing import Any, Dict, List, Optional

from openai import OpenAI
from openai import AuthenticationError, RateLimitError, APIConnectionError, APIStatusError


def generate_outline(topic: str, heading: str, target_word_count: int) -> List[Dict[str, Any]]:
    """Generate a simple H2/H3 outline sized to the target word count.

    Returns list of items: { level: 'h2'|'h3', title: str, target_words: int }
    """
    min_sections = 5
    max_sections = 10

    # Determine number of H2 sections heuristically
    if target_word_count <= 700:
        num_h2 = min_sections
    elif target_word_count >= 3000:
        num_h2 = max_sections
    else:
        # scale between min and max
        span = max_sections - min_sections
        ratio = (target_word_count - 700) / (3000 - 700)
        num_h2 = min(max_sections, max(min_sections, int(min_sections + ratio * span)))

    # Allocate words: reserve ~12% for intro and ~12% for conclusion
    intro_words = max(120, int(target_word_count * 0.12))
    conclusion_words = max(120, int(target_word_count * 0.12))
    body_words = max(200, target_word_count - intro_words - conclusion_words)

    per_section = max(120, int(body_words / max(1, num_h2)))

    outline: List[Dict[str, Any]] = []
    outline.append({"level": "h2", "title": "Introduction", "target_words": intro_words})

    # Basic section suggestions based on topic
    core_sections = [
        f"Understanding {topic}",
        f"Key Benefits of {topic}",
        f"Core Concepts and Terminology",
        f"How to Get Started with {topic}",
        f"Best Practices for {topic}",
        f"Common Pitfalls and How to Avoid Them",
        f"Tools and Resources for {topic}",
        f"Advanced Tips and Strategies",
        f"Real-World Examples and Case Studies",
    ]
    i = 0
    while len([s for s in outline if s["level"] == "h2"]) - 1 < num_h2:  # minus intro
        title = core_sections[i % len(core_sections)]
        outline.append({"level": "h2", "title": title, "target_words": per_section})
        i += 1

    outline.append({"level": "h2", "title": "Conclusion", "target_words": conclusion_words})

    # Add a small number of H3 subsections under selected H2 sections
    h2_indices = [idx for idx, s in enumerate(outline) if s["level"] == "h2" and s["title"] not in {"Introduction", "Conclusion"}]
    for h2_idx in h2_indices[: max(1, len(h2_indices)//3)]:
        outline.insert(h2_idx + 1, {"level": "h3", "title": "Key Takeaways", "target_words": max(80, int(per_section * 0.35))})

    return outline


def _build_system_prompt() -> str:
    return (
        "You are a professional SEO blog writer. Write engaging, factual, and structured content. "
        "Follow proper heading hierarchy and integrate keywords naturally. Maintain clarity, accuracy, and usefulness."
    )


def _build_user_prompt(
    topic: str,
    heading: str,
    section_title: str,
    level: str,
    target_word_count: int,
    audience: Optional[str],
    research: Dict[str, Any],
) -> str:
    """Build a prompt for a single section using research as context."""
    sources = research.get("sources", [])
    insights = research.get("insights", [])
    keywords = research.get("keywords", [])

    # We include a constrained set of references and insights to guide the model
    ref_lines: List[str] = []
    for s in sources[:6]:
        if s.get("title") and s.get("url"):
            ref_lines.append(f"- {s['title']} ({s['url']})")

    audience_note = f" for {audience}" if audience else ""

    return (
        f"Write a {target_word_count}-word section for the article '{heading}'.\n"
        f"Section: {level.upper()} - {section_title}.\n"
        f"Audience: produce approachable, professional writing{audience_note}.\n"
        f"Incorporate relevant insights and keywords naturally.\n\n"
        f"Insights to consider:\n" + ("\n".join([f"- {i}" for i in insights[:10]]) or "- None") + "\n\n"
        f"Suggested keywords:\n" + (", ".join(keywords[:12]) or "None") + "\n\n"
        f"Cite ideas to sources only when necessary; do not include explicit citation markers.\n"
        f"Avoid fluff. Prefer clear explanations, examples, and step-by-step guidance where appropriate.\n"
    )


def generate_section_text(
    openai_api_key: str,
    topic: str,
    heading: str,
    section_title: str,
    level: str,
    target_word_count: int,
    research: Dict[str, Any],
    audience: Optional[str] = None,
) -> str:
    """Generate one section of the article using OpenAI."""
    client = OpenAI(api_key=openai_api_key)

    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(
        topic=topic,
        heading=heading,
        section_title=section_title,
        level=level,
        target_word_count=target_word_count,
        audience=audience,
        research=research,
    )

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
        )
    except AuthenticationError as e:
        raise RuntimeError(
            "OpenAI authentication failed. Verify OPENAI_API_KEY is correct (create a new secret key if needed)."
        ) from e
    except RateLimitError as e:
        raise RuntimeError(
            "OpenAI rate limit reached. Please wait and try again, or reduce concurrency."
        ) from e
    except APIConnectionError as e:
        raise RuntimeError(
            "Network error communicating with OpenAI API. Check your internet connection and retry."
        ) from e
    except APIStatusError as e:
        raise RuntimeError(
            f"OpenAI API returned an error: {getattr(e, 'message', str(e))}"
        ) from e
    except Exception as e:
        raise RuntimeError("Unexpected error during content generation.") from e

    text = completion.choices[0].message.content or ""
    return text.strip()
