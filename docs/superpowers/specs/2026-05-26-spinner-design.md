# Spinner Usability Design

## Overview
IncluScan should show a textual spinner during every long-running step so the user can see that work is in progress.

The spinner is a UI concern only. It should not change scraper, scanner, storage, or report behavior.

## Goals
- Show clear progress feedback during slow operations.
- Keep spinner behavior consistent across the CLI.
- Stop the spinner cleanly on success, failure, or user cancellation.

## Scope
Spinner feedback should be shown while the CLI performs long-running work, including:

- crawling the site
- writing the snapshot
- loading snapshot data for scanning
- calling the AI model for each page
- generating static reports

## Non-Goals
- No visual progress bar.
- No estimated time remaining.
- No background job system.
- No changes to the scraping or scanning logic itself.

## Design
Add a small shared helper in the CLI layer, such as `run_with_spinner(message, fn, ...)`, that wraps a callable with a Rich spinner.

The helper should:

- start the spinner before invoking the work
- stop the spinner when the work finishes
- re-raise errors after stopping the spinner
- treat `KeyboardInterrupt` and `EOFError` as cancellations

The CLI should use this helper around each expensive step rather than manually managing spinner state in multiple places.

## Behavior
- Scrapper mode shows a spinner for crawl and snapshot write steps.
- Scanner mode shows a spinner for snapshot loading, model calls, and report generation.
- If the user presses `Esc` or `Ctrl+C`, the current spinner stops and the run exits cleanly.
- If a step fails, the spinner stops and the error is surfaced normally.

## Testing
- Unit test the spinner helper with a fake callable that succeeds.
- Unit test that the helper stops and re-raises on exception.
- Unit test that cancellation is treated as a clean stop.
- Add a CLI test that verifies long-running operations are wrapped by the helper.
