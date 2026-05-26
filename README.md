# IncluScan
An AI-powered tool to analyze websites and suggest inclusive, non-sexist language improvements.

## Quickstart

IncluScan is a Python CLI with two modes:

- `Scrapper`: crawl a site from a base URL and store page text as JSONL (JSON Lines).
- `Scanner`: load a saved snapshot and analyze each page with an AI model.

Run it with:

```bash
python -m incluscan
```

### Details

- The Scrapper is conservative by default: same-domain only, `sitemap.xml` preferred when available, `robots.txt` respected, with a default page cap and polite delay.
- The Scrapper supports HTML pages and PDFs with embedded text.
- The Scanner supports OpenAI, Anthropic, Google, and Ollama when the respective API key (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`) or local service (`http://localhost:11434` for Ollama) is available.
- Each scan analyzes pages in the original language and writes static HTML reports under `docs/`.

## Examples
### Scrapper

The Scrapper crawls a site and saves a JSONL snapshot under `docs/snapshots/`.

```text
$ python -m incluscan
? Choose mode (Use arrow keys)
 » Scrapper
   Scanner
? Base URL https://www.uc3m.es/
? Page cap  Maximum number of pages to fetch before stopping. 10
? Enable extended crawl overrides?
Follow extra in-site links beyond sitemap discovery for deeper coverage. (Use arrow keys)
   No
 » Yes
⠦ Crawling site
```

What these choices mean:

- `Base URL`: the site to crawl.
- `Page cap`: the maximum number of pages to save in the snapshot.
- `Enable extended crawl overrides?`: follow extra same-site links beyond the sitemap for deeper coverage.

Example output:

```text
Crawling site
Writing snapshot
Saved snapshot to docs/snapshots/snapshot-005f3ea3.jsonl
```

The JSONL file contains one snapshot record plus one line per crawled page.

### Scanner

The Scanner loads a saved snapshot, lets you choose a vendor and model, then analyzes each page.

```text
$ python -m incluscan
? Choose mode (Use arrow keys)
   Scrapper
 » Scanner
? Choose snapshot (Use arrow keys)
 » UC3M — fetched 2026-05-26 16:29 (200 pages)
   UC3M — fetched 2026-05-26 13:44 (10 pages)
? Choose provider (Use arrow keys)
 » OpenAI
   Anthropic
   Google
   Ollama
? Choose model (Use arrow keys)
 » gpt-4
   gpt-4o
   gpt-4o-mini
   gpt-4.1
   gpt-4.1-mini
   gpt-4.1-nano
   ...
⠧ Analyzing https://www.uc3m.es/
```

What these choices mean:

- `Choose snapshot`: pick the crawl you want to analyze.
- `Choose provider`: select the model provider.
- `Choose model`: select the model that will review the pages.

Example output:

```text
Loading snapshot
Analyzing https://www.uc3m.es/
Analyzing https://www.uc3m.es/grado
Generating report
Writing reports
Wrote report for scan-001
```

The scanner writes two static HTML reports:

- `docs/index.html`: the scan history with one card per scan.
- `docs/runs/<scan_id>/index.html`: the individual scan report.

## Results
The results of the scan are static HTML reports under `docs/`. The main `index.html` shows a card for each scan with metadata and a link to the individual report. Each individual report shows the pages analyzed, the issues found, and suggestions for improvement. These reports are available at this URL: https://bonigarcia.dev/IncluScan/

## Architecture

- `src/incluscan/cli.py` orchestrates prompts and runs.
- `src/incluscan/scraper.py` crawls and extracts text.
- `src/incluscan/scanner.py` calls models and parses JSON.
- `src/incluscan/storage.py` reads and writes JSONL snapshots.
- `src/incluscan/report.py` generates static HTML under `docs/`.

This keeps scraping, analysis, and reporting separate, so one scraped snapshot can be scanned multiple times.

## About

IncluScan (Copyright &copy; 2026) is an open-source project created and maintained by [Boni Garcia](https://bonigarcia.dev/), licensed under the terms of [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0).
