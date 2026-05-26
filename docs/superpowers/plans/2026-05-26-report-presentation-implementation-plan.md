# Report Presentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the raw report HTML with styled, navigable pages that link scan runs to anchored URL sections and clearly present each finding.

**Architecture:** Keep report generation inside `src/incluscan/report.py`, but split the HTML into two reusable renderers: one for the dashboard-style index and one for the run detail page with per-URL anchors. Compute counts from the existing `findings_by_url` structure so the CLI does not need new report state.

**Tech Stack:** Python 3.11+, static HTML, embedded CSS, `pytest`

---

### Task 1: Add report rendering tests for styling and navigation

**Files:**
- Modify: `tests/test_report.py`

- [ ] **Step 1: Write the failing test**

```python
from incluscan.models import ReviewFinding, ScanRunSummary
from incluscan.report import build_index_page, build_run_page


def test_build_index_page_includes_dashboard_layout_and_run_link():
    run = ScanRunSummary(
        scan_id="scan-001",
        snapshot_id="snapshot-001",
        base_url="https://www.uc3m.es/",
        snapshot_fetched_at="2026-05-26T10:00:00Z",
        vendor="OpenAI",
        model="gpt-4o-mini",
        started_at="2026-05-26T11:00:00Z",
        finished_at="2026-05-26T11:05:00Z",
        input_tokens=123,
        output_tokens=45,
    )

    html = build_index_page([run], run_finding_counts={"scan-001": 4})

    assert "IncluScan Reports" in html
    assert "scan-001" in html
    assert "4 findings" in html
    assert "runs/scan-001/index.html" in html
    assert "<style>" in html


def test_build_run_page_includes_anchors_and_findings_table():
    scan = ScanRunSummary(
        scan_id="scan-001",
        snapshot_id="snapshot-001",
        base_url="https://www.uc3m.es/",
        snapshot_fetched_at="2026-05-26T10:00:00Z",
        vendor="OpenAI",
        model="gpt-4o-mini",
        started_at="2026-05-26T11:00:00Z",
        finished_at="2026-05-26T11:05:00Z",
        input_tokens=123,
        output_tokens=45,
    )

    html = build_run_page(
        scan=scan,
        findings_by_url={
            "https://www.uc3m.es/": [
                ReviewFinding(
                    original="los alumnos",
                    modified="el estudiantado",
                    justification="Neutraliza el lenguaje de género",
                )
            ]
        },
    )

    assert "href=\"#url-https-www-uc3m-es\"" in html or "#url-https-www-uc3m-es" in html
    assert "id=\"url-https-www-uc3m-es\"" in html or "url-https-www-uc3m-es" in html
    assert "los alumnos" in html
    assert "el estudiantado" in html
    assert "Neutraliza el lenguaje de género" in html
    assert "<style>" in html


def test_build_run_page_shows_empty_state_for_missing_findings():
    scan = ScanRunSummary(
        scan_id="scan-001",
        snapshot_id="snapshot-001",
        base_url="https://www.uc3m.es/",
        snapshot_fetched_at="2026-05-26T10:00:00Z",
        vendor="OpenAI",
        model="gpt-4o-mini",
        started_at="2026-05-26T11:00:00Z",
        finished_at="2026-05-26T11:05:00Z",
        input_tokens=123,
        output_tokens=45,
    )

    html = build_run_page(scan=scan, findings_by_url={"https://www.uc3m.es/": []})

    assert "No changes found" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_report.py -q`

Expected: fail because `build_index_page` does not accept finding counts and the HTML is still raw.

- [ ] **Step 3: Write minimal implementation**

```python
# src/incluscan/report.py
from html import escape
from urllib.parse import quote

from dataclasses import asdict
import json
from pathlib import Path

from incluscan.models import ReviewFinding, ScanRunSummary

def _report_css() -> str:
    return """<style>
    body { font-family: system-ui, sans-serif; margin: 0; background: #f7f7f8; color: #1f2937; }
    .page { max-width: 1100px; margin: 0 auto; padding: 24px; }
    .card { background: white; border: 1px solid #e5e7eb; border-radius: 14px; padding: 16px; box-shadow: 0 1px 2px rgba(0,0,0,.04); }
    .grid { display: grid; gap: 16px; }
    .grid.cols-2 { grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }
    .meta { display: flex; gap: 12px; flex-wrap: wrap; font-size: 0.95rem; color: #4b5563; }
    .badge { display: inline-block; background: #eef2ff; color: #3730a3; border-radius: 999px; padding: 2px 10px; font-size: 0.85rem; }
    .muted { color: #6b7280; }
    .url-list a { display: inline-block; margin-right: 8px; margin-bottom: 8px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid #e5e7eb; vertical-align: top; }
    th { font-size: 0.78rem; text-transform: uppercase; letter-spacing: .04em; color: #6b7280; }
    .section { margin-top: 18px; }
    .finding-empty { padding: 12px; color: #6b7280; font-style: italic; }
    a { color: #2563eb; text-decoration: none; }
    a:hover { text-decoration: underline; }
    </style>"""

def _url_anchor(url: str) -> str:
    return "url-" + quote(url, safe="").replace("%", "-").replace(".", "-")

def build_index_page(runs: list[ScanRunSummary], run_finding_counts: dict[str, int] | None = None) -> str:
    run_finding_counts = run_finding_counts or {}
    cards = []
    for run in runs:
        count = run_finding_counts.get(run.scan_id, 0)
        cards.append(
            f'''<article class="card">
              <div class="meta">
                <span class="badge">{escape(run.vendor)}</span>
                <span>{escape(run.model)}</span>
                <span>{escape(run.base_url)}</span>
                <span>{escape(run.snapshot_fetched_at)}</span>
              </div>
              <h2><a href="runs/{escape(run.scan_id)}/index.html">{escape(run.scan_id)}</a></h2>
              <p class="muted">{count} findings</p>
              <p><a href="runs/{escape(run.scan_id)}/index.html">Open run details</a></p>
            </article>'''
        )
    body = "".join(cards) if cards else '<p class="muted">No scan runs yet.</p>'
    return f'''<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>IncluScan Reports</title>{_report_css()}</head>
<body>
  <main class="page">
    <header class="card">
      <h1>IncluScan Reports</h1>
      <p class="muted">Historical scan runs and their findings.</p>
    </header>
    <section class="grid cols-2">{body}</section>
  </main>
</body>
</html>'''

def build_run_page(scan: ScanRunSummary, findings_by_url: dict[str, list[ReviewFinding]]) -> str:
    nav_items = []
    sections = []
    for url, findings in findings_by_url.items():
        anchor = _url_anchor(url)
        nav_items.append(f'<a href="#{anchor}">{escape(url)}</a>')
        if findings:
            rows = "".join(
                f'''<tr>
                    <td>{escape(finding.original)}</td>
                    <td>{escape(finding.modified)}</td>
                    <td>{escape(finding.justification)}</td>
                </tr>'''
                for finding in findings
            )
            table = f'<table><thead><tr><th>Original</th><th>Modified</th><th>Justification</th></tr></thead><tbody>{rows}</tbody></table>'
        else:
            table = '<div class="finding-empty">No changes found</div>'
        sections.append(
            f'''<section class="card section" id="{anchor}">
              <h2>{escape(url)}</h2>
              <p class="muted">{len(findings)} findings</p>
              {table}
            </section>'''
        )
    nav = "".join(nav_items) if nav_items else '<span class="muted">No analyzed URLs.</span>'
    sections_html = "".join(sections) if sections else '<section class="card"><p class="finding-empty">No changes found</p></section>'
    return f'''<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>{escape(scan.scan_id)}</title>{_report_css()}</head>
<body>
  <main class="page">
    <header class="card">
      <h1>{escape(scan.vendor)} {escape(scan.model)}</h1>
      <div class="meta">
        <span class="badge">{escape(scan.scan_id)}</span>
        <span>{escape(scan.base_url)}</span>
        <span>{escape(scan.snapshot_fetched_at)}</span>
        <span>{escape(scan.started_at)} → {escape(scan.finished_at)}</span>
      </div>
      <p class="muted">Input tokens: {scan.input_tokens if scan.input_tokens is not None else ""} | Output tokens: {scan.output_tokens if scan.output_tokens is not None else ""}</p>
      <div class="url-list">{nav}</div>
    </header>
    <section class="grid">{sections_html}</section>
  </main>
</body>
</html>'''
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_report.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/incluscan/report.py tests/test_report.py
git commit -m "feat: style report pages and add navigation"
```

## Coverage Check
- Styled dashboard index: Task 1.
- Linked run details with URL anchors: Task 1.
- Finding counts in the index: Task 1.
- Empty-state handling for URLs without findings: Task 1.
- The plan intentionally keeps per-URL pages out of scope to preserve the existing output shape.

## Self-Review Notes
- The plan covers the new CSS/styling requirement, the index-to-run navigation requirement, and the within-run URL navigation requirement.
- The only shared data addition is finding counts passed to the index renderer; this does not affect the CLI or scanner.
- Placeholder scan should be re-run during implementation because the report HTML helpers are intentionally shown as partial code blocks in the minimal implementation section.
