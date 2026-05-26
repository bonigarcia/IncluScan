from dataclasses import asdict, replace
from datetime import datetime
import json
from html import escape
from pathlib import Path
from urllib.parse import quote

from incluscan.models import ReviewFinding, ScanRunSummary


def _report_css() -> str:
    return """<style>
    body { font-family: system-ui, sans-serif; margin: 0; background: #f7f7f8; color: #1f2937; }
    .page { max-width: 1100px; margin: 0 auto; padding: 24px; }
    .card { background: white; border: 1px solid #e5e7eb; border-radius: 14px; padding: 12px 14px; box-shadow: 0 1px 2px rgba(0,0,0,.04); }
    .list { display: grid; gap: 16px; }
    .entry { display: grid; gap: 8px; }
    .entry h1, .entry h2 { margin: 0; }
    .meta { display: flex; gap: 10px; flex-wrap: wrap; font-size: 0.92rem; color: #4b5563; }
    .badge { display: inline-block; background: #eef2ff; color: #3730a3; border-radius: 999px; padding: 2px 10px; font-size: 0.8rem; }
    .muted { color: #6b7280; }
    .url-list a { display: inline-block; margin-right: 8px; margin-bottom: 8px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid #e5e7eb; vertical-align: top; }
    th { font-size: 0.78rem; text-transform: uppercase; letter-spacing: .04em; color: #6b7280; }
    .section { margin-top: 18px; }
    .finding-empty { padding: 12px; color: #6b7280; font-style: italic; }
    .summary-list { margin: 12px 0 0; padding-left: 18px; }
    .summary-list li { margin: 4px 0; }
    .run-title { margin: 0; font-size: 1.35rem; line-height: 1.2; }
    .run-model { margin: 2px 0 0; font-size: 1.7rem; line-height: 1.15; font-weight: 700; }
    .run-details { display: grid; gap: 8px; }
    a { color: #2563eb; text-decoration: none; }
    a:hover { text-decoration: underline; }
    </style>"""


def _url_anchor(url: str) -> str:
    return "url-" + quote(url, safe="").replace("%", "-").replace(".", "-")


def _friendly_date(iso_text: str) -> str:
    value = datetime.fromisoformat(iso_text.replace("Z", "+00:00"))
    return value.strftime("%b %d, %Y, %I:%M %p")


def build_index_page(
    runs: list[ScanRunSummary],
    run_finding_counts: dict[str, int] | None = None,
    run_page_counts: dict[str, int] | None = None,
) -> str:
    run_finding_counts = run_finding_counts or {}
    run_page_counts = run_page_counts or {}
    entries = []
    for run in runs:
        finding_count = run.finding_count if run.finding_count is not None else run_finding_counts.get(run.scan_id, 0)
        page_count = run.page_count if run.page_count is not None else run_page_counts.get(run.scan_id, 0)
        entries.append(
            f'''<article class="card entry">
              <p class="run-title">{escape(run.base_url)} - {escape(_friendly_date(run.snapshot_fetched_at))}</p>
              <span>{escape(run.vendor)} {escape(run.model)}</span>
              <span class="muted">{page_count} pages analyzed - {finding_count} findings</span>
              <span><a href="runs/{escape(run.scan_id)}/index.html">Report</a></span>
            </article>'''
        )
    body = "".join(entries) if entries else '<p class="muted">No scan runs yet.</p>'
    return f'''<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>IncluScan Reports</title>{_report_css()}</head>
<body>
  <main class="page">
    <header class="card">
      <h1>IncluScan Reports</h1>
      <p class="muted">Historical scan runs and their findings.</p>
    </header>
    <section class="list">{body}</section>
  </main>
</body>
</html>'''


def load_run_summaries(report_root: Path) -> list[ScanRunSummary]:
    runs: list[ScanRunSummary] = []
    runs_dir = report_root / "runs"
    if not runs_dir.exists():
        return runs
    for meta_path in sorted(runs_dir.glob("*/meta.json")):
        runs.append(ScanRunSummary(**json.loads(meta_path.read_text(encoding="utf-8"))))
    return runs


def build_run_page(
    scan: ScanRunSummary,
    findings_by_url: dict[str, list[ReviewFinding]],
    total_pages_analyzed: int | None = None,
) -> str:
    total_pages_analyzed = total_pages_analyzed if total_pages_analyzed is not None else len(findings_by_url)
    sections = []
    analyzed_url_items = []
    for url, findings in findings_by_url.items():
        anchor = _url_anchor(url)
        analyzed_url_items.append(
            f'<li><a href="#{anchor}">{escape(url)}</a> <span class="muted">({len(findings)} findings)</span></li>'
        )
        if not findings:
            continue
        rows = "".join(
            f'''<tr>
                <td>{escape(finding.original)}</td>
                <td>{escape(finding.modified)}</td>
                <td>{escape(finding.justification)}</td>
            </tr>'''
            for finding in findings
        )
        table = f'<table><thead><tr><th>Original</th><th>Modified</th><th>Justification</th></tr></thead><tbody>{rows}</tbody></table>'
        sections.append(
            f'''<section class="card section" id="{anchor}">
              <h2><a href="{escape(url)}">{escape(url)}</a></h2>
              <p class="muted">{len(findings)} findings</p>
              {table}
            </section>'''
        )
    sections_html = "".join(sections) if sections else '<section class="card"><p class="finding-empty">No changes found</p></section>'
    analyzed_urls_html = "".join(analyzed_url_items) if analyzed_url_items else '<li class="muted">No analyzed URLs.</li>'
    return f'''<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>{escape(scan.scan_id)}</title>{_report_css()}</head>
<body>
  <main class="page">
    <header class="card">
      <div class="run-details">
        <h2 class="run-title">{escape(scan.base_url)} - {escape(scan.vendor)} {escape(scan.model)}</h2>
      </div>
      <div class="meta">
        <span class="badge">{escape(scan.scan_id)}</span>
        <span>{escape(_friendly_date(scan.snapshot_fetched_at))}</span>
        <span>{escape(scan.started_at)} → {escape(scan.finished_at)}</span>
        <span>{total_pages_analyzed} pages analyzed</span>
      </div>
      <p class="muted">Input tokens: {scan.input_tokens if scan.input_tokens is not None else ""} | Output tokens: {scan.output_tokens if scan.output_tokens is not None else ""}</p>
    </header>
    <details class="card section">
      <summary>Analyzed URLs ({total_pages_analyzed})</summary>
      <ul class="summary-list">{analyzed_urls_html}</ul>
    </details>
    <section class="list">{sections_html}</section>
  </main>
</body>
</html>'''


def write_reports(
    report_root: Path,
    runs: list[ScanRunSummary],
    run_pages: dict[str, str] | None = None,
    run_finding_counts: dict[str, int] | None = None,
    run_page_counts: dict[str, int] | None = None,
) -> None:
    report_root.mkdir(parents=True, exist_ok=True)
    run_finding_counts = run_finding_counts or {}
    run_page_counts = run_page_counts or {}
    persisted_runs = []
    for run in runs:
        persisted_runs.append(
            replace(
                run,
                finding_count=run_finding_counts.get(run.scan_id, run.finding_count),
                page_count=run_page_counts.get(run.scan_id, run.page_count),
            )
        )
    for run in persisted_runs:
        run_dir = report_root / "runs" / run.scan_id
        run_dir.mkdir(parents=True, exist_ok=True)
        if run_pages and run.scan_id in run_pages:
            (run_dir / "index.html").write_text(run_pages[run.scan_id], encoding="utf-8")
        (run_dir / "meta.json").write_text(json.dumps(asdict(run), ensure_ascii=False), encoding="utf-8")
    all_runs = load_run_summaries(report_root)
    (report_root / "index.html").write_text(build_index_page(all_runs, run_finding_counts=run_finding_counts, run_page_counts=run_page_counts), encoding="utf-8")
