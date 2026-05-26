from pathlib import Path

from incluscan.models import ReviewFinding, ScanRunSummary, ScrapedPage, SnapshotMetadata
from incluscan.report import write_reports
from incluscan.scanner import scan_snapshot
from incluscan.storage import write_snapshot


def test_end_to_end_scan_smoke(tmp_path: Path):
    snapshot = SnapshotMetadata(
        snapshot_id="snapshot-001",
        base_url="https://www.uc3m.es/",
        fetched_at="2026-05-26T10:00:00Z",
    )
    page = ScrapedPage(
        snapshot_id="snapshot-001",
        url="https://www.uc3m.es/",
        fetched_at="2026-05-26T10:00:00Z",
        content_type="text/html",
        title="UC3M",
        text="Los alumnos deben entregar su solicitud.",
        language_hint="es",
        status_code=200,
        crawl_depth=0,
        source_type="sitemap",
    )

    snapshot_path = write_snapshot(tmp_path / "snapshots", snapshot, [page])
    assert snapshot_path.exists()

    def fake_completion(prompt: str):
        return "[]", None, None

    run, findings_by_url = scan_snapshot(snapshot, [page], fake_completion, "Ollama", "gemma3:4b")

    assert findings_by_url[page.url] == []

    run_html = "<html><body><h1>Ollama gemma3:4b</h1></body></html>"
    write_reports(tmp_path / "docs", [run], {run.scan_id: run_html})

    assert (tmp_path / "docs" / "index.html").exists()
    assert (tmp_path / "docs" / "runs" / run.scan_id / "index.html").exists()
