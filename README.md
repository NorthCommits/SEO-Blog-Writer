# SEO Blog Writer

A CLI-based professional SEO blog writer that generates long-form, SEO-optimized, publication-ready articles with optional deep research. It integrates OpenAI for writing, Tavily for web research, and exports to TXT, DOCX, and PDF with professional formatting. A "polish" mode applies Times New Roman tiers and editorial refinement to humanize the output.

## Features
- Professional blog generation with target word counts
- Deep Research Mode (RAG-like): fetches and synthesizes multiple sources
- Evidence tagging: [stat], [quote], [case], [tool] to guide writing
- Anti-templating engine: varied structures and micro-styles per section
- Embedding-based de-duplication and paraphrase to reduce repetition
- SEO metadata generation (title tag, meta description, keywords, slug)
- Exports: TXT, DOCX (headings and styles), PDF (styled headings, bullets, quotes, tables)
- Table of Contents and page numbers for DOCX/PDF
- Polish Mode: Times New Roman tiers + Key Takeaways and micro-refinement (opener variety, rhythm, list/table variation, micro-insights)

## Requirements
- Python 3.8+
- OpenAI API key
- Tavily API key

Install dependencies:
```bash
pip install -r requirements.txt
```

## Project Structure
```
seo-blog-writer/
├── .env
├── requirements.txt
├── README.md
├── main.py
├── src/
│   ├── __init__.py
│   ├── research.py
│   ├── content.py
│   ├── seo.py
│   └── export.py
└── output/
```

## Environment Variables
Create a `.env` file:
```ini
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
```

## Quick Start
Basic run (interactive prompts will request missing options):
```bash
python main.py
```

Recommended full command:
```bash
python main.py \
  --topic "AI coding assistants comparison" \
  --heading "Best AI Coding Assistants for Developers in 2025" \
  --word_count 2500 \
  --deep y \
  --format pdf \
  --audience "software developers"
```

Outputs are saved to the `output/` directory with the pattern `{slug}_{YYYYMMDD_HHMMSS}.{ext}`.

## Modes and Options
- `--deep`: Enables Deep Research Mode (broader Tavily search and richer insights)
- `--format`: `txt`, `docx`, `pdf`, or `all`
- `--audience`: Target audience hint for tone
- Typography options (when not using polish mode):
  - `--font_family` (`Open Sans`, `Helvetica`, `Times-Roman`)
  - `--base_font_size` (default 11)
  - `--h1_size`, `--h2_size`, `--h3_size`
- `--polish`: Enables the editorial pipeline and Times New Roman styles:
  - Enforces Title/Heading/Subheading/Body tiers (Times New Roman: Title 20pt bold centered; Heading 15pt bold; Subheading 13pt bold italic; Body 11pt, line spacing 1.15, spacing after 6pt, justified)
  - Adds varied micro-styles per section, Key Takeaways for major sections, opener variety, cadence/rhythm adjustments, list/table variation, and micro-insights
  - Runs embedding-based dedupe + paraphrase and final micro-refinement

Example with polish mode:
```bash
python main.py \
  --topic "AI coding assistants comparison" \
  --heading "Best AI Coding Assistants for Developers in 2025" \
  --word_count 4300 \
  --deep y \
  --format pdf \
  --audience "software developers" \
  --polish
```

## Fonts
- PDF: If you choose `Open Sans`, place TTF files in `fonts/` for best results:
  - `OpenSans-Regular.ttf`, `OpenSans-Bold.ttf`, `OpenSans-Italic.ttf`, `OpenSans-BoldItalic.ttf`
  - If not present, PDF falls back to Helvetica.
- DOCX: Requests the chosen font name; Word may substitute if the font is not installed on your system.
- Polish mode uses `Times New Roman` tiers (PDF uses `Times-Roman` core font).

## Deep Research
- Normal mode: up to 5 results, basic depth
- Deep mode: up to 15 results, advanced depth, optionally includes raw content
- Evidence lines are tagged ([stat], [quote], [case], [tool]) to guide section micro-styles

## Export Details
- TXT: plain text with metadata and headings
- DOCX: professional headings, paragraph spacing, justification, TOC, page numbers
- PDF: styled headings, line spacing 1.15, paragraph spacing 6pt, justified body; TOC and page numbers; renders bullets, block quotes, and simple `|` tables

## Error Handling
- Missing keys: friendly error and exit
- OpenAI errors: authentication, rate limit, network, and status errors are handled with actionable messages
- Output directory: verified for writability

## Tips for Best Results
- Use Deep Research for competitive topics or long articles (>2000 words)
- Provide a clear audience for better tone control
- Use `--polish` for publication-ready, human-sounding output with anti-templating refinements

## Troubleshooting
- Import warnings (click, dotenv, reportlab, docx, openai): ensure you installed dependencies
- PDF lacks Open Sans: add the TTFs to `fonts/` or select `Times-Roman`/`Helvetica`
- Output looks repetitive: use `--polish` to enable dedupe/paraphrase and micro-refinement
- Authentication failures: recreate your OpenAI key (use a secret key, not a project/browser token)

## Security & Privacy
- API keys are loaded from `.env` and not logged
- Research content is summarized; raw content is optional and not persisted except in a local `.cache/research_cache.json`

## Roadmap
- Keyword density and readability scoring
- Plagiarism check suggestions
- Multi-language support and image suggestions
- Internal linking recommendations

## License
MIT
