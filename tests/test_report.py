from incluscan.models import ReviewFinding, ScanRunSummary
from incluscan.report import build_index_page, build_run_page, write_reports


def test_build_index_page_lists_scan_metadata():
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

    html = build_index_page([run])

    assert "gpt-4o-mini" in html
    assert "123" in html
    assert "scan-001" in html
    assert "https://www.uc3m.es/" in html
    assert "2026-05-26T10:00:00Z" in html


def test_build_run_page_groups_findings_by_url():
    html = build_run_page(
        scan=ScanRunSummary(
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
        ),
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

    assert "los alumnos" in html
    assert "el estudiantado" in html
    assert "Neutraliza el lenguaje de género" in html


def test_write_reports_preserves_previous_runs(tmp_path):
    first = ScanRunSummary(
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
    second = ScanRunSummary(
        scan_id="scan-002",
        snapshot_id="snapshot-001",
        base_url="https://www.uc3m.es/",
        snapshot_fetched_at="2026-05-26T10:00:00Z",
        vendor="Ollama",
        model="gemma3:4b",
        started_at="2026-05-27T11:00:00Z",
        finished_at="2026-05-27T11:05:00Z",
        input_tokens=None,
        output_tokens=None,
    )

    write_reports(tmp_path, [first])
    write_reports(tmp_path, [second])

    index_html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "scan-001" in index_html
    assert "scan-002" in index_html
