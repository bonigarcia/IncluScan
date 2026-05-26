from dataclasses import asdict
import json
from pathlib import Path

from incluscan.models import ReviewFinding, ScanRunSummary


def build_index_page(runs: list[ScanRunSummary]) -> str:
    rows = "".join(
        f"<tr><td>{run.scan_id}</td><td>{run.base_url}</td><td>{run.snapshot_fetched_at}</td><td>{run.vendor}</td><td>{run.model}</td><td>{run.input_tokens or ''}</td><td>{run.output_tokens or ''}</td></tr>"
        for run in runs
    )
    return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>IncluScan Reports</title></head>
<body>
<h1>IncluScan Reports</h1>
<table>
<thead><tr><th>Scan</th><th>Base URL</th><th>Snapshot date</th><th>Vendor</th><th>Model</th><th>Input tokens</th><th>Output tokens</th></tr></thead>
<tbody>{rows}</tbody>
</table>
</body>
</html>"""


def load_run_summaries(report_root: Path) -> list[ScanRunSummary]:
    runs: list[ScanRunSummary] = []
    runs_dir = report_root / "runs"
    if not runs_dir.exists():
        return runs
    for meta_path in sorted(runs_dir.glob("*/meta.json")):
        runs.append(ScanRunSummary(**json.loads(meta_path.read_text(encoding="utf-8"))))
    return runs


def build_run_page(scan: ScanRunSummary, findings_by_url: dict[str, list[ReviewFinding]]) -> str:
    sections = []
    for url, findings in findings_by_url.items():
        rows = "".join(
            f"<tr><td>{finding.original}</td><td>{finding.modified}</td><td>{finding.justification}</td></tr>"
            for finding in findings
        )
        sections.append(f"<section><h2>{url}</h2><table><tbody>{rows}</tbody></table></section>")
    return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>{scan.scan_id}</title></head>
<body>
<h1>{scan.vendor} {scan.model}</h1>
{''.join(sections)}
</body>
</html>"""


def write_reports(report_root: Path, runs: list[ScanRunSummary], run_pages: dict[str, str] | None = None) -> None:
    report_root.mkdir(parents=True, exist_ok=True)
    for scan_id, html in (run_pages or {}).items():
        run_dir = report_root / "runs" / scan_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "index.html").write_text(html, encoding="utf-8")
    for run in runs:
        run_dir = report_root / "runs" / run.scan_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "meta.json").write_text(json.dumps(asdict(run), ensure_ascii=False), encoding="utf-8")
    all_runs = load_run_summaries(report_root)
    (report_root / "index.html").write_text(build_index_page(all_runs), encoding="utf-8")
