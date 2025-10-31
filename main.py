from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

import click
from dotenv import load_dotenv

from src.research import perform_research
from src.seo import generate_metadata, slugify
from src.content import generate_outline, generate_section_text
from src.export import export_txt, export_docx, export_pdf


OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")


def ensure_output_dir() -> None:
    """Ensure output directory exists and is writable."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    # basic writability check
    test_path = os.path.join(OUTPUT_DIR, ".write_test")
    try:
        with open(test_path, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(test_path)
    except Exception as exc:
        raise RuntimeError(f"Output directory not writable: {OUTPUT_DIR}. {exc}")


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing environment variable {name}. Set it in .env or shell."
        )
    return value


@click.command()
@click.option("--topic", prompt="Enter article topic", help="The topic/keyword for the article.")
@click.option("--heading", prompt="Enter article heading", help="The H1 article title.")
@click.option("--word_count", prompt="Target word count", type=int)
@click.option(
    "--deep", prompt="Enable deep research mode? (y/n)",
    type=str, default="n",
)
@click.option(
    "--format", "output_format", prompt="Output format (txt/docx/pdf/all)",
    type=click.Choice(["txt", "docx", "pdf", "all"], case_sensitive=False),
    default="all",
)
@click.option(
    "--audience", prompt="Target audience (optional)", default="",
)
def cli(topic: str, heading: str, word_count: int, deep: str, output_format: str, audience: str) -> None:
    """CLI entry to generate a professional SEO blog post."""
    load_dotenv()

    print("Configuration saved.")
    deep_flag = str(deep).lower().strip() in {"y", "yes", "true", "1"}

    ensure_output_dir()

    try:
        openai_key = require_env("OPENAI_API_KEY")
        tavily_key = require_env("TAVILY_API_KEY")
    except RuntimeError as e:
        print(str(e))
        sys.exit(1)

    print("Starting research...")
    try:
        research = perform_research(topic=topic, tavily_api_key=tavily_key, deep=deep_flag)
    except Exception as e:
        print(f"Research failed: {str(e)}")
        sys.exit(1)

    print(f"Found {len(research.get('sources', []))} sources.")

    print("Building outline and metadata...")
    outline = generate_outline(topic=topic, heading=heading, target_word_count=word_count)

    metadata = generate_metadata(
        topic=topic,
        heading=heading,
        target_audience=audience or None,
        outline_h2=[s["title"] for s in outline if s["level"] == "h2"],
        research_keywords=research.get("keywords"),
    )

    print("Generating content...")
    sections = [s for s in outline if s["level"] in {"h2", "h3"}]

    generated_sections: List[Dict[str, str]] = []
    for idx, section in enumerate(sections, start=1):
        print(f"Writing section {idx}/{len(sections)}: {section['title']}")
        try:
            text = generate_section_text(
                openai_api_key=openai_key,
                topic=topic,
                heading=heading,
                section_title=section["title"],
                level=section["level"],
                target_word_count=section["target_words"],
                research=research,
                audience=audience or None,
            )
        except RuntimeError as e:
            print(str(e))
            print("Aborting.")
            sys.exit(1)
        generated_sections.append({"title": section["title"], "level": section["level"], "text": text})

    # Assemble final text
    full_text_lines: List[str] = []
    full_text_lines.append("SEO Metadata")
    full_text_lines.append(f"Title Tag: {metadata['title_tag']}")
    full_text_lines.append(f"Meta Description: {metadata['meta_description']}")
    full_text_lines.append("Primary Keywords: " + ", ".join(metadata["primary_keywords"]))
    full_text_lines.append("Secondary Keywords: " + ", ".join(metadata["secondary_keywords"]))
    full_text_lines.append(f"URL Slug: {metadata['url_slug']}")
    full_text_lines.append("")

    # Article
    full_text_lines.append(f"H1: {heading}")
    full_text_lines.append("")
    for sec in generated_sections:
        if sec["level"] == "h2":
            full_text_lines.append(f"H2: {sec['title']}")
        else:
            full_text_lines.append(f"H3: {sec['title']}")
        full_text_lines.append(sec["text"].strip())
        full_text_lines.append("")

    if research.get("sources"):
        full_text_lines.append("Sources")
        for s in research["sources"]:
            if s.get("title") and s.get("url"):
                full_text_lines.append(f"- {s['title']} - {s['url']}")

    final_text = "\n".join(full_text_lines).strip()

    # Exports
    slug = metadata["url_slug"] or slugify(heading)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    do_txt = output_format in {"txt", "all"}
    do_docx = output_format in {"docx", "all"}
    do_pdf = output_format in {"pdf", "all"}

    if do_txt:
        print("Exporting to txt...")
        export_txt(
            output_dir=OUTPUT_DIR,
            slug=slug,
            timestamp=timestamp,
            metadata=metadata,
            heading=heading,
            sections=generated_sections,
        )

    if do_docx:
        print("Exporting to docx...")
        export_docx(
            output_dir=OUTPUT_DIR,
            slug=slug,
            timestamp=timestamp,
            metadata=metadata,
            heading=heading,
            sections=generated_sections,
        )

    if do_pdf:
        print("Exporting to pdf...")
        export_pdf(
            output_dir=OUTPUT_DIR,
            slug=slug,
            timestamp=timestamp,
            metadata=metadata,
            heading=heading,
            sections=generated_sections,
        )

    print("Blog generated successfully.")
    print(f"Saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    cli()
