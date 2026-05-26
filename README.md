# IncluScan
An AI-powered tool to analyze websites and suggest inclusive, non-sexist language improvements.

## Quickstart

IncluScan is a Python CLI with two modes:

- `Scrapper`: crawl a site from a base URL and store page text as JSONL.
- `Scanner`: load a saved snapshot and analyze each page with an AI model.

Run it with:

```bash
python -m incluscan
```

### Scrapper

The scraper is conservative by default:

- same-domain crawling only
- `sitemap.xml` preferred when available
- `robots.txt` respected
- default page cap and polite delay
- HTML pages and PDFs with embedded text supported

Results are written to `docs/snapshots/` as JSONL snapshots.

### Scanner

The scanner supports these vendors when available:

- OpenAI via `OPENAI_API_KEY`
- Anthropic via `ANTHROPIC_API_KEY`
- Google via `GOOGLE_API_KEY`
- Ollama at `http://localhost:11434`

For each scan, the CLI lists available vendors and models, then analyzes each page in its original language.

Reports are written to `docs/` as static HTML:

- `docs/index.html` for the scan history
- `docs/runs/<scan_id>/index.html` for a scan run

## Architecture

- `src/incluscan/cli.py` orchestrates prompts and runs.
- `src/incluscan/scraper.py` crawls and extracts text.
- `src/incluscan/scanner.py` calls models and parses JSON.
- `src/incluscan/storage.py` reads and writes JSONL snapshots.
- `src/incluscan/report.py` generates static HTML under `docs/`.

This keeps scraping, analysis, and reporting separate, so one scraped snapshot can be scanned multiple times.

## About

IncluScan (Copyright &copy; 2026) is an open-source project created and maintained by [Boni Garcia](https://bonigarcia.dev/), licensed under the terms of [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0).
