from incluscan.models import ReviewFinding, ScanRunSummary
from incluscan.report import build_index_page, build_run_page, write_reports


def test_build_index_page_includes_dashboard_layout_and_run_link():
    older_run = ScanRunSummary(
        scan_id="scan-000",
        snapshot_id="snapshot-000",
        base_url="https://www.example.com/old",
        snapshot_fetched_at="2026-05-26T09:00:00Z",
        vendor="Google",
        model="gemini-2.5-flash",
        started_at="2026-05-26T09:00:00Z",
        finished_at="2026-05-26T09:10:00Z",
        input_tokens=12,
        output_tokens=4,
    )
    newer_run = ScanRunSummary(
        scan_id="scan-001",
        snapshot_id="snapshot-001",
        base_url="https://www.uc3m.es/",
        snapshot_fetched_at="2026-05-26T10:00:00Z",
        vendor="Google",
        model="gemini-2.5-flash",
        started_at="2026-05-26T11:00:00Z",
        finished_at="2026-05-26T11:05:00Z",
        input_tokens=123,
        output_tokens=45,
    )

    html = build_index_page([newer_run, older_run], run_finding_counts={"scan-000": 1, "scan-001": 4}, run_page_counts={"scan-000": 2, "scan-001": 9})

    assert "IncluScan Reports" in html
    assert "Google gemini-2.5-flash" in html
    assert "May 26, 2026" in html
    assert "10:00 AM" in html
    assert "https://www.uc3m.es/" in html
    assert "9 pages analyzed" in html
    assert "1. https://www.example.com/old" in html
    assert "2. https://www.uc3m.es/" in html
    assert "Scan report" in html
    assert "4 findings" in html
    assert "runs/scan-001/index.html" in html
    assert "<style>" in html
    assert "card entry" in html


def test_build_run_page_shows_total_page_count_and_hidden_url_list():
    scan = ScanRunSummary(
        scan_id="scan-001",
        snapshot_id="snapshot-001",
        base_url="https://www.uc3m.es/",
        snapshot_fetched_at="2026-05-26T10:00:00Z",
        vendor="Google",
        model="gemini-2.5-flash",
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
            ],
            "https://www.uc3m.es/contacto": [],
        },
        total_pages_analyzed=2,
    )

    assert "2 pages analyzed" in html
    assert "Total time" in html
    assert "details" in html
    assert "Analyzed URLs" in html
    assert "https://www.uc3m.es/contacto" in html
    assert "href=\"https://www.uc3m.es/\"" in html
    assert "href=\"https://www.uc3m.es/contacto\"" not in html
    assert "id=\"url-" in html
    assert "Scan report" not in html
    assert "No changes found" not in html


def test_build_run_page_includes_page_link_and_findings_table():
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

    html = build_run_page(scan=scan, findings_by_url={"https://www.uc3m.es/": [ReviewFinding(original="los alumnos", modified="el estudiantado", justification="Neutraliza el lenguaje de género")]}, total_pages_analyzed=1)

    assert "id=\"url-" in html
    assert "href=\"https://www.uc3m.es/\"" in html
    assert "los alumnos" in html
    assert "el estudiantado" in html
    assert "Neutraliza el lenguaje de género" in html
    assert "<style>" in html
    assert "No changes found" not in html


def test_build_run_page_shows_duration_in_metadata():
    scan = ScanRunSummary(
        scan_id="scan-001",
        snapshot_id="snapshot-001",
        base_url="https://www.uc3m.es/",
        snapshot_fetched_at="2026-05-26T10:00:00Z",
        vendor="Google",
        model="gemini-2.5-flash",
        started_at="2026-05-26T11:00:00Z",
        finished_at="2026-05-26T11:12:30Z",
        input_tokens=123,
        output_tokens=45,
        duration_seconds=750.0,
    )

    html = build_run_page(scan=scan, findings_by_url={"https://www.uc3m.es/": []}, total_pages_analyzed=1)

    assert "12m 30s" in html


def test_build_run_page_includes_responsive_overflow_css():
    scan = ScanRunSummary(
        scan_id="scan-001",
        snapshot_id="snapshot-001",
        base_url="https://www.uc3m.es/",
        snapshot_fetched_at="2026-05-26T10:00:00Z",
        vendor="Google",
        model="gemini-2.5-flash",
        started_at="2026-05-26T11:00:00Z",
        finished_at="2026-05-26T11:12:30Z",
        input_tokens=123,
        output_tokens=45,
        duration_seconds=750.0,
    )

    html = build_run_page(
        scan=scan,
        findings_by_url={
            "https://www.uc3m.es/long/very/very/very/very/very/very/very/very/long/url": [
                ReviewFinding(
                    original="los alumnos",
                    modified="el estudiantado",
                    justification="Neutraliza el lenguaje de género",
                )
            ]
        },
        total_pages_analyzed=1,
    )

    assert "overflow-x: hidden" not in html
    assert "table-layout: auto" in html
    assert ".section h2 a { display: block" in html
    assert "overflow-wrap: anywhere" in html


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
    assert "<p class=\"muted\">0 findings</p>" not in html


def test_write_reports_preserves_existing_findings_counts(tmp_path):
    run_one = ScanRunSummary(
        scan_id="scan-001",
        snapshot_id="snapshot-001",
        base_url="https://www.uc3m.es/",
        snapshot_fetched_at="2026-05-26T10:00:00Z",
        vendor="Google",
        model="gemini-2.5-flash",
        started_at="2026-05-26T11:00:00Z",
        finished_at="2026-05-26T11:05:00Z",
        input_tokens=123,
        output_tokens=45,
    )
    run_two = ScanRunSummary(
        scan_id="scan-002",
        snapshot_id="snapshot-002",
        base_url="https://www.example.com/",
        snapshot_fetched_at="2026-05-27T10:00:00Z",
        vendor="Google",
        model="gemini-2.5-flash",
        started_at="2026-05-27T11:00:00Z",
        finished_at="2026-05-27T11:05:00Z",
        input_tokens=111,
        output_tokens=22,
    )

    write_reports(tmp_path, [run_one], {run_one.scan_id: "<html></html>"}, {run_one.scan_id: 3}, {run_one.scan_id: 8})
    write_reports(tmp_path, [run_two], {run_two.scan_id: "<html></html>"}, {run_two.scan_id: 5}, {run_two.scan_id: 2})

    index_html = (tmp_path / "index.html").read_text(encoding="utf-8")

    assert "3 findings" in index_html
    assert "5 findings" in index_html
