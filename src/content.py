from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI
from openai import AuthenticationError, RateLimitError, APIConnectionError, APIStatusError
import random
import re
import json


def generate_outline(topic: str, heading: str, target_word_count: int) -> List[Dict[str, Any]]:
    """Generate a simple H2/H3 outline sized to the target word count.

    Returns list of items: { level: 'h2'|'h3', title: str, target_words: int }
    """
    min_sections = 5
    max_sections = 10

    if target_word_count <= 700:
        num_h2 = min_sections
    elif target_word_count >= 3000:
        num_h2 = max_sections
    else:
        span = max_sections - min_sections
        ratio = (target_word_count - 700) / (3000 - 700)
        num_h2 = min(max_sections, max(min_sections, int(min_sections + ratio * span)))

    intro_words = max(120, int(target_word_count * 0.12))
    conclusion_words = max(120, int(target_word_count * 0.12))
    body_words = max(200, target_word_count - intro_words - conclusion_words)

    per_section = max(120, int(body_words / max(1, num_h2)))

    outline: List[Dict[str, Any]] = []
    outline.append({"level": "h2", "title": "Introduction", "target_words": intro_words})

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
    while len([s for s in outline if s["level"] == "h2"]) - 1 < num_h2:
        title = core_sections[i % len(core_sections)]
        outline.append({"level": "h2", "title": title, "target_words": per_section})
        i += 1

    outline.append({"level": "h2", "title": "Conclusion", "target_words": conclusion_words})

    h3_variants = ["Key Takeaways", "Action Steps", "Quick Checklist", "Pro Tips", "Summary Points"]
    h2_indices = [idx for idx, s in enumerate(outline) if s["level"] == "h2" and s["title"] not in {"Introduction", "Conclusion"}]
    for j, h2_idx in enumerate(h2_indices[: max(1, len(h2_indices)//3)]):
        subtitle = h3_variants[j % len(h3_variants)]
        outline.insert(h2_idx + 1, {"level": "h3", "title": subtitle, "target_words": max(80, int(per_section * 0.35))})

    return outline


# ---------- Evidence tagging (Researcher) ----------

def build_tagged_evidence(research: Dict[str, Any]) -> List[str]:
    items: List[str] = []
    for s in research.get("sources", [])[:12]:
        title = (s.get("title") or "").strip()
        snippet = (s.get("snippet") or "").strip()
        text = f"{title} — {snippet}".strip(" —")
        if not text:
            continue
        tag = ""
        if re.search(r"\b\d{1,3}%|\b\d{4}\b|\b\d+[,.]\d+\b", text):
            tag = "[stat]"
        elif '“' in text or '”' in text or '"' in text:
            tag = "[quote]"
        elif any(k in text.lower() for k in ["case study", "case", "example"]):
            tag = "[case]"
        elif any(k in text.lower() for k in ["tool", "platform", "software", "suite"]):
            tag = "[tool]"
        else:
            tag = "[stat]" if re.search(r"\b\d+\b", text) else "[case]"
        items.append(f"{tag} {text}")
    uniq: List[str] = []
    seen = set()
    for it in items:
        if it not in seen:
            seen.add(it)
            uniq.append(it)
    return uniq[:12]


# ---------- Structure template & micro-styles (Composer) ----------

def select_structure_template(seed: Optional[int] = None) -> str:
    random.seed(seed)
    templates = ["Analytical Guide", "Practical Playbook", "Thought Leadership", "Case Study", "Hybrid Narrative"]
    return random.choice(templates)


def choose_micro_style(idx: int) -> str:
    styles = ["story hook", "stat+insight", "example walkthrough", "micro-interview quote", "guided checklist"]
    return styles[idx % len(styles)]


def _build_system_prompt() -> str:
    return (
        "You are a professional SEO blog writer and editor. Generate human-sounding, non-templated content. "
        "Never output raw Markdown tokens like ## or **. Use plain prose and bullet lines only when needed."
    )


def _build_user_prompt(
    topic: str,
    heading: str,
    section_title: str,
    level: str,
    target_word_count: int,
    audience: Optional[str],
    research: Dict[str, Any],
    structure_template: str,
    micro_style: str,
) -> str:
    evidence = build_tagged_evidence(research)

    audience_note = f" for {audience}" if audience else ""

    guidelines = (
        "Rules: Use an engaging opener; vary sentence openings and lengths; prefer active voice; 2-4 sentence paragraphs; "
        "avoid repeating phrases across sections; no raw Markdown tokens; bullets only when valuable; weave keywords naturally."
    )

    micro_style_note = (
        f"Use micro-style: {micro_style}. If possible, anchor with one of [stat, quote, case, tool] from evidence."
    )

    return (
        f"Article: '{heading}' using template '{structure_template}'.\n"
        f"Section: {level.upper()} - {section_title}. Target ~{target_word_count} words. Audience: professionals{audience_note}.\n"
        f"{guidelines}\n{micro_style_note}\n\n"
        f"Evidence (distinct items):\n" + ("\n".join(evidence) if evidence else "- none") + "\n\n"
        f"Write the section now in clean prose (no markdown symbols)."
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
    structure_template: Optional[str] = None,
    micro_style: Optional[str] = None,
) -> str:
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
        structure_template=structure_template or select_structure_template(),
        micro_style=micro_style or choose_micro_style(0),
    )

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            top_p=0.9,
        )
    except AuthenticationError as e:
        raise RuntimeError("OpenAI authentication failed. Verify OPENAI_API_KEY is correct.") from e
    except RateLimitError as e:
        raise RuntimeError("OpenAI rate limit reached. Please wait and try again.") from e
    except APIConnectionError as e:
        raise RuntimeError("Network error communicating with OpenAI API. Check your connection.") from e
    except APIStatusError as e:
        raise RuntimeError(f"OpenAI API returned an error: {getattr(e, 'message', str(e))}") from e
    except Exception as e:
        raise RuntimeError("Unexpected error during content generation.") from e

    text = completion.choices[0].message.content or ""
    return text.strip()


# ---------- Polishing helpers ----------

def _strip_markdown_headings(text: str) -> str:
    lines = []
    for line in text.splitlines():
        line = re.sub(r"^(#{1,6})\s+", "", line)
        line = line.replace("**", "")
        lines.append(line)
    return "\n".join(lines)


def summarize_key_takeaways(openai_api_key: str, section_title: str, section_text: str) -> List[str]:
    client = OpenAI(api_key=openai_api_key)
    prompt = (
        "Summarize the following section into 3-5 concise, actionable key takeaways. "
        "Return as plain bullets without numbering, each on a new line. No markdown symbols.\n\n"
        f"Section: {section_title}\n\n"
        f"Content:\n{section_text}\n"
    )
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise editor."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            top_p=0.6,
        )
        out = (completion.choices[0].message.content or "").strip()
        bullets = [b.strip("- ") for b in out.splitlines() if b.strip()]
        return [b for b in bullets if b][:5]
    except Exception:
        sents = [s.strip() for s in re.split(r"[.!?]", section_text) if len(s.strip()) > 0]
        return [s for s in sents[:5]]


def polish_sections(openai_api_key: str, sections: List[Dict[str, str]]) -> List[Dict[str, str]]:
    polished: List[Dict[str, str]] = []
    for s in sections:
        clean_text = _strip_markdown_headings(s.get("text", ""))
        polished.append({"title": s["title"], "level": s["level"], "text": clean_text})
        if s["level"] == "h2":
            bullets = summarize_key_takeaways(openai_api_key, s["title"], clean_text)
            if bullets:
                bullet_text = "\n".join([f"- {b}" for b in bullets])
                polished.append({"title": "Key Takeaways", "level": "h3", "text": bullet_text})
    return polished


# ---------- Semantic dedupe/paraphrase (Editor) ----------

def embed_paragraphs(client: OpenAI, texts: List[str]) -> List[List[float]]:
    resp = client.embeddings.create(model="text-embedding-3-small", input=texts)
    return [d.embedding for d in resp.data]


def cosine_sim(a: List[float], b: List[float]) -> float:
    import math
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(y*y for y in b))
    return 0.0 if na == 0 or nb == 0 else dot / (na * nb)


def paraphrase_text(client: OpenAI, text: str) -> str:
    prompt = (
        "Rewrite the following to avoid duplicated phrasing while preserving meaning. "
        "Keep it concise, natural, and professional. No markdown symbols.\n\n" + text
    )
    out = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "You are a senior editor."}, {"role": "user", "content": prompt}],
        temperature=0.4,
        top_p=0.7,
    )
    return (out.choices[0].message.content or text).strip()


def dedupe_and_paraphrase_sections(openai_api_key: str, sections: List[Dict[str, str]], threshold: float = 0.9) -> List[Dict[str, str]]:
    client = OpenAI(api_key=openai_api_key)
    texts = [s["text"] for s in sections]
    embs = embed_paragraphs(client, texts)

    keep: List[Dict[str, str]] = []
    for i, sec in enumerate(sections):
        duplicate = False
        for kept in keep:
            kept_emb = embed_paragraphs(client, [kept["text"]])[0]
            sim = cosine_sim(embs[i], kept_emb)
            if sim >= threshold:
                new_text = paraphrase_text(client, sec["text"])[:]
                sec = {**sec, "text": new_text}
                duplicate = True
                break
        keep.append(sec)
    return keep


# ---------- Micro-refinement pass (global article) ----------

def micro_refine_article(
    openai_api_key: str,
    heading: str,
    metadata: Dict[str, Any],
    sections: List[Dict[str, str]],
    audience: Optional[str] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
    """Apply micro-refinement: opener variety, rhythm, list/table variation, micro-insights, and meta/closing polish.
    Returns potentially updated metadata and refined sections.
    """
    client = OpenAI(api_key=openai_api_key)

    article = {
        "heading": heading,
        "metadata": metadata,
        "audience": audience or "",
        "sections": sections,
    }

    directive = (
        "Apply MICRO-REFINEMENT: \n"
        "A) Section openers: no two share same first 3 words; vary opener types across temporal/rhetorical/contrast/data/story (>=3 styles).\n"
        "B) Rhythm: alternate short/long sentences; add transitions; include one rhetorical question, one contrast phrase, one reflective line.\n"
        "C) Lists/Tables: vary representation (numbered, narrative, 2-col table, checklist); randomize verb starters.\n"
        "D) Micro-insights: insert 1-sentence insights or mini-quotes between sections, not templated.\n"
        "E) Meta/closing: simplify meta to avoid echo; add pre-conclusion bridge; warm human outro.\n"
        "F) Quality: ensure diversity of length/layout; <2 repeated phrases; include one micro-story, one data point, one rhetorical question.\n"
        "Do not use markdown symbols. Return strict JSON with fields: {metadata, sections:[{title, level, text}]}."
    )

    msg = (
        "Here is the article to refine (JSON):\n" + json.dumps(article, ensure_ascii=False) + "\n\n" + directive
    )

    out = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a meticulous senior editor and formatter."},
            {"role": "user", "content": msg},
        ],
        temperature=0.6,
        top_p=0.9,
    )

    content = out.choices[0].message.content or ""
    try:
        data = json.loads(content)
        new_meta = data.get("metadata", metadata)
        new_sections = data.get("sections", sections)
        # Basic validation
        if isinstance(new_meta, dict) and isinstance(new_sections, list):
            return new_meta, new_sections
        return metadata, sections
    except Exception:
        return metadata, sections
