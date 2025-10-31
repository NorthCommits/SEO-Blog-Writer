from __future__ import annotations

import os
from typing import Dict, List

from docx import Document
from docx.shared import Pt, Inches
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


def _build_filename(output_dir: str, slug: str, timestamp: str, ext: str) -> str:
    return os.path.join(output_dir, f"{slug}_{timestamp}.{ext}")


def export_txt(
    output_dir: str,
    slug: str,
    timestamp: str,
    metadata: Dict[str, object],
    heading: str,
    sections: List[Dict[str, str]],
) -> str:
    """Export blog as plain text with simple formatting."""
    path = _build_filename(output_dir, slug, timestamp, "txt")

    lines: List[str] = []
    lines.append("SEO Metadata")
    lines.append(f"Title Tag: {metadata['title_tag']}")
    lines.append(f"Meta Description: {metadata['meta_description']}")
    lines.append("Primary Keywords: " + ", ".join(metadata["primary_keywords"]))
    lines.append("Secondary Keywords: " + ", ".join(metadata["secondary_keywords"]))
    lines.append(f"URL Slug: {metadata['url_slug']}")
    lines.append("")
    lines.append(f"H1: {heading}")
    lines.append("")

    for s in sections:
        prefix = "H2:" if s["level"] == "h2" else "H3:"
        lines.append(f"{prefix} {s['title']}")
        lines.append(s["text"].strip())
        lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).strip() + "\n")

    return path


def export_docx(
    output_dir: str,
    slug: str,
    timestamp: str,
    metadata: Dict[str, object],
    heading: str,
    sections: List[Dict[str, str]],
) -> str:
    """Export blog as Word document using python-docx."""
    path = _build_filename(output_dir, slug, timestamp, "docx")

    doc = Document()

    # Set margins: 1 inch
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # Title
    title = doc.add_heading(level=0)
    title_run = title.add_run(heading)
    title_run.bold = True

    # Metadata as normal paragraphs
    doc.add_paragraph(f"Title Tag: {metadata['title_tag']}")
    doc.add_paragraph(f"Meta Description: {metadata['meta_description']}")
    doc.add_paragraph("Primary Keywords: " + ", ".join(metadata["primary_keywords"]))
    doc.add_paragraph("Secondary Keywords: " + ", ".join(metadata["secondary_keywords"]))
    doc.add_paragraph(f"URL Slug: {metadata['url_slug']}")

    # Content sections
    for s in sections:
        if s["level"] == "h2":
            doc.add_heading(s["title"], level=1)
        else:
            doc.add_heading(s["title"], level=2)
        for para in s["text"].split("\n\n"):
            doc.add_paragraph(para.strip())

    doc.save(path)
    return path


def export_pdf(
    output_dir: str,
    slug: str,
    timestamp: str,
    metadata: Dict[str, object],
    heading: str,
    sections: List[Dict[str, str]],
) -> str:
    """Export blog as PDF with simple styles using reportlab."""
    path = _build_filename(output_dir, slug, timestamp, "pdf")

    doc = SimpleDocTemplate(
        path,
        pagesize=letter,
        leftMargin=inch,
        rightMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
    )
    styles = getSampleStyleSheet()

    story = []

    # Heading
    story.append(Paragraph(heading, styles["Title"]))

    # Metadata
    story.append(Paragraph(f"Title Tag: {metadata['title_tag']}", styles["Normal"]))
    story.append(Paragraph(f"Meta Description: {metadata['meta_description']}", styles["Normal"]))
    story.append(Paragraph("Primary Keywords: " + ", ".join(metadata["primary_keywords"]), styles["Normal"]))
    story.append(Paragraph("Secondary Keywords: " + ", ".join(metadata["secondary_keywords"]), styles["Normal"]))
    story.append(Paragraph(f"URL Slug: {metadata['url_slug']}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Content
    for s in sections:
        if s["level"] == "h2":
            story.append(Paragraph(s["title"], styles["Heading2"]))
        else:
            story.append(Paragraph(s["title"], styles["Heading3"]))
        for para in s["text"].split("\n\n"):
            story.append(Paragraph(para.strip(), styles["BodyText"]))
            story.append(Spacer(1, 6))
        story.append(Spacer(1, 12))

    # Page number canvas callback
    def _add_page_number(canvas_obj, doc_obj):
        page_num_text = f"{canvas_obj.getPageNumber()}"
        canvas_obj.setFont("Helvetica", 9)
        canvas_obj.drawCentredString(4.25 * inch, 0.5 * inch, page_num_text)

    doc.build(story, onFirstPage=_add_page_number, onLaterPages=_add_page_number)

    return path
