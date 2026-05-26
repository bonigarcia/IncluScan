# Report Presentation Design

## Overview
IncluScan should generate more usable HTML reports with CSS styling and navigation between scan runs and analyzed URLs.

The report output must stay static HTML so it can continue to live under `docs/` and work with GitHub Pages.

## Goals
- Replace raw HTML tables with a more readable presentation.
- Let users navigate from the report index to a specific scan run.
- Let users navigate within a scan run to the analyzed URL section.
- Show the `original`, `modified`, and `justification` fields clearly.
- Include finding counts in the report index.

## Scope
The report system should produce:

- a styled `docs/index.html` overview page
- one styled run detail page per scan under `docs/runs/<scan_id>/index.html`
- anchored URL sections inside each run detail page

## Non-Goals
- No per-URL HTML files.
- No JavaScript application.
- No external CSS assets.
- No database-backed report store.

## Design
### Index page
The index page should act like a report dashboard instead of a plain table.

Each scan entry should display:

- base URL
- snapshot date
- vendor
- model
- token usage when available
- finding count
- link to the run detail page

### Run detail page
Each run detail page should include:

- a summary header for the scan metadata
- a small navigation list of analyzed URLs
- one anchored section per analyzed URL
- a findings table in each section with columns for `original`, `modified`, and `justification`

Each URL section should have a stable anchor so users can jump directly to it from the top of the page.

## Styling
The generated HTML should embed its own CSS.

The CSS should keep the report readable with:

- card-like or sectioned layout on the index page
- clear spacing and typography
- responsive width constraints for long findings
- visible link states and section anchors

## Data Model
The current report data already includes enough information for the design:

- `ScanRunSummary` for the index and run header metadata
- `ReviewFinding` for each table row
- per-URL findings grouped in the existing `findings_by_url` map

The report renderer should compute the finding count from the grouped findings.

## Error Handling
- If a run has no findings, the run detail page should still render with an empty state.
- If a scan run has no findings for a URL, show the URL section with a short "No changes found" message.
- If the report files are regenerated, older scan pages must remain linked and readable.

## Testing
- Test that the index page includes the finding count and link to each run.
- Test that the run page includes anchors for each URL.
- Test that the findings table renders the three required fields.
- Test that a URL with no findings renders an empty-state message.
