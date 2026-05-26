# IncluScan Design

## Overview
IncluScan is a Python CLI that scrapes a website into JSONL snapshots and then scans those snapshots with an AI model to suggest inclusive, non-sexist language improvements.

The tool has two modes:

- `Scrapper`: crawl a site from a base URL and store page text page-by-page.
- `Scanner`: load a previous snapshot, choose a vendor and model, and analyze each page with a fixed prompt template.

The CLI uses `rich` for prompts and terminal output.

## Goals
- Support conservative site crawling by default.
- Prefer `sitemap.xml` when available.
- Support HTML pages and PDFs that already contain extractable text.
- Store scraped content as JSONL, one record per URL.
- Let one scraped snapshot be scanned multiple times with different models.
- Support OpenAI, Anthropic, Google, and local Ollama when available.
- Generate static HTML reports in `docs/` for GitHub Pages.
- Keep Spanish and English content analyzable without translation.

## Non-Goals
- No OCR for scanned PDFs.
- No translation pipeline before analysis.
- No chunking/merge strategy for long documents in the first version.
- No automatic model choice when multiple vendors are available.
- No overwrite behavior for prior scan runs.

## User Flow
### Scrapper mode
1. Ask for the base URL.
2. Crawl same-domain URLs only.
3. Use `sitemap.xml` as the preferred seed if available.
4. Respect `robots.txt`.
5. Apply a default page cap and request delay.
6. Allow optional hybrid overrides for deeper crawling when explicitly enabled.
7. Store the result as a JSONL snapshot.

### Scanner mode
1. List available JSONL snapshots.
2. Let the user choose a snapshot by site/base URL and date.
3. Detect available vendors from environment variables and local Ollama.
4. Require the user to choose a vendor.
5. List available models for the chosen vendor.
6. Require the user to choose a model.
7. Analyze each page in its original language.
8. Save a new historical scan run.
9. Update the static report index and run page.

## Architecture
The code should be split into small modules:

- `cli`: interactive prompts and orchestration.
- `scraper`: crawling and text extraction.
- `storage`: JSONL snapshot writing and loading.
- `scanner`: prompt execution and result parsing.
- `report`: HTML generation for `docs/`.

The modules should communicate through plain Python data structures and files, not shared global state.

## Scraper Design
### Crawl policy
- Start from the user-provided base URL.
- Prefer URLs found in `sitemap.xml`.
- Stay within the same domain as the base URL.
- Respect `robots.txt`.
- De-duplicate URLs before fetching.
- Enforce a default page cap and polite delay.
- Allow an optional extended crawl mode for deeper discovery.

### Supported content
- HTML pages: extract visible text and basic metadata such as title and status code.
- PDFs: extract text only if the PDF already contains embedded text.
- Unsupported or empty content should be recorded with a reason instead of failing the whole crawl.

### Snapshot output
Each crawl writes JSONL records, one per URL. A snapshot should include:

- `base_url`
- `snapshot_id`
- `fetched_at`
- `url`
- `content_type`
- `title`
- `text`
- `language_hint` when detectable
- crawl metadata such as depth, status code, and source type

## Scanner Design
### Model discovery
The scanner should show only vendors that are actually usable in the current environment:

- OpenAI if `OPENAI_API_KEY` exists.
- Anthropic if `ANTHROPIC_API_KEY` exists.
- Google if `GOOGLE_API_KEY` exists.
- Ollama if `http://localhost:11434` responds locally.

For each selected vendor, the CLI should list available models from that vendor’s API or local endpoint.

### Analysis behavior
- Analyze each URL independently.
- Keep the content in its original language.
- Use the prompt template file verbatim apart from inserting the page content.
- Expect strict JSON output only.
- If parsing fails, retry once with the same prompt and stricter JSON-only handling.

### Scan output
Each scan run should be immutable and include:

- `scan_id`
- `snapshot_id`
- `vendor`
- `model`
- `started_at`
- `finished_at`
- token usage when the provider returns it
- per-page findings
- per-page errors when analysis fails

## Prompt Template
The scanner must use a separate template file with this structure:

- request inclusive and non-sexist language review
- require valid JSON array output only
- each object must contain exactly `original`, `modified`, and `justification`
- preserve meaning and avoid changing proper names, brands, direct quotes, or technical terms unless necessary
- return `[]` if no change is needed

The scanner only replaces `{{content}}` with the page text.

## Report Design
The report lives in `docs/` and should be static HTML.

### Index page
The index should list every scan run with:

- base URL
- snapshot date
- scan date
- vendor
- model
- token usage if available
- link to the detailed run report

### Run page
Each scan run should have a report that groups findings by page URL and shows:

- original fragment
- modified fragment
- justification
- location or context when available

### History behavior
- Never overwrite older runs.
- Each new scan adds a new entry.
- The report should let an external user compare runs across models over time.

## Error Handling
- If the crawl is partial, still persist the snapshot and note the failure.
- If a PDF has no extractable text, mark it as skipped.
- If a vendor is unavailable, do not offer it in the menu.
- If a single page scan fails, record the error and continue.
- If the model returns invalid JSON, retry once, then store the failure if parsing still fails.

## Testing Strategy
- Unit test URL filtering, sitemap discovery, and crawl deduplication.
- Unit test HTML and PDF text extraction with fixtures.
- Unit test JSONL snapshot read/write behavior.
- Unit test vendor and model discovery.
- Unit test prompt rendering and JSON parsing.
- Unit test static report rendering.
- Add a small end-to-end smoke test that crawls or scans a tiny fixture snapshot.

## Implementation Notes
- Keep the first version small and direct.
- Prefer simple file-based artifacts over databases.
- Preserve raw page text so future scanner runs can reuse the same snapshot.
- Treat the scanner as the only place where model-specific behavior lives.
