from incluscan.models import ReviewFinding, ScanRunSummary
from incluscan.report import build_index_page, build_run_page, write_reports


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

    assert "#url-" in html
    assert "id=\"url-" in html
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
