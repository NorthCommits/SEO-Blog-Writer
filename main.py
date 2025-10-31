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
from src.content import (
    generate_outline,
    generate_section_text,
    polish_sections,
    select_structure_template,
    choose_micro_style,
    dedupe_and_paraphrase_sections,
    micro_refine_article,
)
from src.export import export_txt, export_docx, export_pdf


OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")


def ensure_output_dir() -> None:
    """Ensure output directory exists and is writable."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
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
@click.option(
    "--font_family", default="Open Sans", show_default=True,
    type=click.Choice(["Open Sans", "Helvetica", "Times-Roman"], case_sensitive=False),
    help="Base font family for DOCX/PDF. 'Open Sans' requires TTFs in fonts/."
)
@click.option("--base_font_size", default=11, show_default=True, type=int, help="Base body font size.")
@click.option("--h1_size", default=18, show_default=True, type=int, help="H1 font size.")
@click.option("--h2_size", default=14, show_default=True, type=int, help="H2 font size.")
@click.option("--h3_size", default=12, show_default=True, type=int, help="H3 font size.")
@click.option("--polish", is_flag=True, default=False, help="Enable editorial polishing and Times New Roman style system.")

def cli(topic: str, heading: str, word_count: int, deep: str, output_format: str, audience: str,
        font_family: str, base_font_size: int, h1_size: int, h2_size: int, h3_size: int, polish: bool) -> None:
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

    # Select a varied structure template once; rotate micro-styles per section
    structure_template = select_structure_template()

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
                structure_template=structure_template,
                micro_style=choose_micro_style(idx - 1),
            )
        except RuntimeError as e:
            print(str(e))
            print("Aborting.")
            sys.exit(1)
        generated_sections.append({"title": section["title"], "level": section["level"], "text": text})

    # Deduplicate and paraphrase prior to polishing
    print("De-duplicating and paraphrasing similar sections...")
    generated_sections = dedupe_and_paraphrase_sections(openai_key, generated_sections, threshold=0.9)

    # Optional polishing
    if polish:
        print("Polishing content and adding Key Takeaways...")
        generated_sections = polish_sections(openai_key, generated_sections)
        print("Applying micro-refinement for opener variety and rhythm...")
        metadata, generated_sections = micro_refine_article(
            openai_key, heading, metadata, generated_sections, audience or None
        )
        font_family = "Times-Roman"
        base_font_size = 11
        h1_size = 20
        h2_size = 15
        h3_size = 13

    slug = metadata["url_slug"] or slugify(heading)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    do_txt = output_format in {"txt", "all"}
    do_docx = output_format in {"docx", "all"}
    do_pdf = output_format in {"pdf", "all"}

    style_opts = {
        "font_family": font_family,
        "base_font_size": base_font_size,
        "h1_size": h1_size,
        "h2_size": h2_size,
        "h3_size": h3_size,
        "polish": polish,
    }

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
            style_options=style_opts,
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
            style_options=style_opts,
        )

    print("Blog generated successfully.")
    print(f"Saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    cli()
