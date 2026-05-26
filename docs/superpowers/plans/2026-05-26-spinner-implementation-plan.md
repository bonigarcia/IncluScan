# Spinner Usability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add textual spinner feedback for every long-running IncluScan step so users can see that the CLI is working and waiting.

**Architecture:** Put the spinner behavior behind one small UI helper in `src/incluscan/ui.py` and keep the CLI as the only place that decides which operations should be wrapped. The scanner gets a narrow optional callback so it can show a spinner per page analysis without importing CLI concerns directly.

**Tech Stack:** Python 3.11+, `rich`, `questionary`, `pytest`

---

### Task 1: Add a reusable spinner helper

**Files:**
- Create: `src/incluscan/ui.py`
- Create: `tests/test_ui.py`

- [ ] **Step 1: Write the failing test**

```python
from rich.console import Console

from incluscan.ui import run_with_spinner


def test_run_with_spinner_returns_callable_result(monkeypatch):
    events = []

    class FakeStatus:
        def __enter__(self):
            events.append("enter")
            return self

        def __exit__(self, exc_type, exc, tb):
            events.append(("exit", exc_type))
            return False

    class FakeConsole:
        def status(self, message, spinner="dots"):
            events.append((message, spinner))
            return FakeStatus()

    result = run_with_spinner(FakeConsole(), "Working", lambda: 42)

    assert result == 42
    assert events == [("Working", "dots"), "enter", ("exit", None)]


def test_run_with_spinner_stops_and_reraises_on_error():
    events = []

    class FakeStatus:
        def __enter__(self):
            events.append("enter")
            return self

        def __exit__(self, exc_type, exc, tb):
            events.append(("exit", exc_type.__name__))
            return False

    class FakeConsole:
        def status(self, message, spinner="dots"):
            events.append((message, spinner))
            return FakeStatus()

    def boom():
        raise RuntimeError("fail")

    try:
        run_with_spinner(FakeConsole(), "Working", boom)
    except RuntimeError as exc:
        assert str(exc) == "fail"

    assert events == [("Working", "dots"), "enter", ("exit", "RuntimeError")]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_ui.py -q`

Expected: import error because `src/incluscan/ui.py` does not exist yet.

- [ ] **Step 3: Write the minimal implementation**

```python
# src/incluscan/ui.py
from collections.abc import Callable
from typing import TypeVar

from rich.console import Console

T = TypeVar("T")


def run_with_spinner(console: Console, message: str, fn: Callable[[], T]) -> T:
    with console.status(message, spinner="dots"):
        return fn()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ui.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/incluscan/ui.py tests/test_ui.py
git commit -m "feat: add reusable spinner helper"
```

### Task 2: Wrap Scrapper and report steps in the CLI

**Files:**
- Modify: `src/incluscan/cli.py`
- Modify: `tests/test_cli_interaction.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from incluscan.cli import run_scraper, run_scanner


def test_run_scraper_wraps_crawl_and_snapshot_write(monkeypatch):
    events = []

    monkeypatch.setattr("incluscan.cli.choose_text", lambda *_args, **_kwargs: "https://www.uc3m.es/")
    monkeypatch.setattr("incluscan.cli.prompt_page_cap", lambda: 100)
    monkeypatch.setattr("incluscan.cli.prompt_extended_crawl", lambda: False)
    monkeypatch.setattr("incluscan.cli.crawl_site", lambda *args, **kwargs: ("snapshot", ["page"]))
    monkeypatch.setattr("incluscan.cli.write_snapshot", lambda *args, **kwargs: Path("docs/snapshots/snapshot.jsonl"))
    monkeypatch.setattr("incluscan.cli.run_with_spinner", lambda console, message, fn: events.append(message) or fn())

    class FakeConsole:
        def print(self, *_args, **_kwargs):
            return None

    run_scraper(FakeConsole())

    assert events == ["Crawling site", "Writing snapshot"]
```

```python
from pathlib import Path

from incluscan.cli import run_scanner


def test_run_scanner_wraps_load_analysis_and_report_steps(monkeypatch):
    events = []

    monkeypatch.setattr("incluscan.cli._choose_snapshot_path", lambda *_args, **_kwargs: Path("docs/snapshots/snapshot.jsonl"))
    monkeypatch.setattr("incluscan.cli.read_snapshot", lambda *_args, **_kwargs: ("snapshot", ["page"]))
    monkeypatch.setattr("incluscan.cli._choose_vendor", lambda *_args, **_kwargs: ("Ollama", None))
    monkeypatch.setattr("incluscan.cli.list_models_for_vendor", lambda *_args, **_kwargs: ["gemma3:1b"])
    monkeypatch.setattr("incluscan.cli.choose_from_options", lambda *_args, **_kwargs: "gemma3:1b")
    monkeypatch.setattr("incluscan.cli.build_request_completion", lambda *_args, **_kwargs: lambda prompt: ("[]", None, None))
    monkeypatch.setattr("incluscan.cli.scan_snapshot", lambda *args, **kwargs: (type("Run", (), {"scan_id": "scan-1"})(), {"url": []}))
    monkeypatch.setattr("incluscan.cli.build_run_page", lambda *_args, **_kwargs: "<html></html>")
    monkeypatch.setattr("incluscan.cli.write_reports", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("incluscan.cli.run_with_spinner", lambda console, message, fn: events.append(message) or fn())

    class FakeConsole:
        def print(self, *_args, **_kwargs):
            return None

    run_scanner(FakeConsole())

    assert events == ["Loading snapshot", "Generating report", "Writing reports"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_cli_interaction.py -q`

Expected: fail because `run_with_spinner` is not used in the CLI yet.

- [ ] **Step 3: Write the minimal implementation**

```python
# src/incluscan/cli.py
from incluscan.ui import run_with_spinner

# inside run_scraper
snapshot, pages = run_with_spinner(console, "Crawling site", lambda: crawl_site(base_url, page_cap=page_cap, allow_extended=allow_extended))
snapshot_path = run_with_spinner(console, "Writing snapshot", lambda: write_snapshot(SNAPSHOT_DIR, snapshot, pages))

# inside run_scanner
snapshot, pages = run_with_spinner(console, "Loading snapshot", lambda: read_snapshot(snapshot_path))
run_html = run_with_spinner(console, "Generating report", lambda: build_run_page(scan, findings_by_url))
run_with_spinner(console, "Writing reports", lambda: write_reports(REPORT_DIR, [scan], {scan.scan_id: run_html}))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli_interaction.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/incluscan/cli.py tests/test_cli_interaction.py
git commit -m "feat: show spinners around CLI work"
```

### Task 3: Add per-page spinner support to scanner analysis

**Files:**
- Modify: `src/incluscan/scanner.py`
- Modify: `tests/test_vendors.py`

- [ ] **Step 1: Write the failing test**

```python
from incluscan.scanner import scan_snapshot
from incluscan.models import ScrapedPage, SnapshotMetadata


def test_scan_snapshot_uses_spinner_for_each_page():
    snapshot = SnapshotMetadata(snapshot_id="snapshot-001", base_url="https://www.uc3m.es/", fetched_at="2026-05-26T10:00:00Z")
    page_one = ScrapedPage(snapshot_id="snapshot-001", url="https://www.uc3m.es/1", fetched_at=snapshot.fetched_at, content_type="text/html", title="1", text="a", language_hint="es", status_code=200, crawl_depth=0, source_type="seed")
    page_two = ScrapedPage(snapshot_id="snapshot-001", url="https://www.uc3m.es/2", fetched_at=snapshot.fetched_at, content_type="text/html", title="2", text="b", language_hint="es", status_code=200, crawl_depth=0, source_type="seed")
    messages = []

    def fake_spinner(message, fn):
        messages.append(message)
        return fn()

    def fake_completion(prompt: str):
        return "[]", None, None

    scan, findings = scan_snapshot(snapshot, [page_one, page_two], fake_completion, "Ollama", "gemma3:1b", with_spinner=fake_spinner)

    assert messages == ["Analyzing https://www.uc3m.es/1", "Analyzing https://www.uc3m.es/2"]
    assert findings[page_one.url] == []
    assert findings[page_two.url] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_vendors.py::test_scan_snapshot_uses_spinner_for_each_page -q`

Expected: fail because `scan_snapshot` does not accept `with_spinner` yet.

- [ ] **Step 3: Write the minimal implementation**

```python
# src/incluscan/scanner.py
def scan_snapshot(
    snapshot: SnapshotMetadata,
    pages: list[ScrapedPage],
    request_completion: Callable[[str], tuple[str, int | None, int | None]],
    vendor_name: str,
    model: str,
    with_spinner: Callable[[str, Callable[[], tuple[str, int | None, int | None]]], tuple[str, int | None, int | None]] | None = None,
) -> tuple[ScanRunSummary, dict[str, list[ReviewFinding]]]:
    runner = with_spinner or (lambda _message, fn: fn())
    for page in pages:
        prompt = build_review_prompt(page.text)
        for attempt in range(2):
            current_prompt = prompt if attempt == 0 else f"{prompt}\n\nReturn only valid JSON that matches the required schema."
            try:
                raw_response, page_input_tokens, page_output_tokens = runner(
                    f"Analyzing {page.url}",
                    lambda: request_completion(current_prompt),
                )
            except requests.RequestException:
                if attempt == 1:
                    parsed_findings = []
                    break
                continue
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_vendors.py::test_scan_snapshot_uses_spinner_for_each_page -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/incluscan/scanner.py tests/test_vendors.py
git commit -m "feat: show spinners during page analysis"
```

## Coverage Check
- Spinner helper and behavior: Task 1.
- Scrapper, snapshot write, load snapshot, report generation: Task 2.
- Per-page analysis spinner: Task 3.
- Cancellation and errors are handled by the existing CLI flow because the spinner helper only wraps the work.

## Self-Review Notes
- No placeholder text remains.
- The plan keeps spinner concerns in the UI layer and only adds a small scanner callback for per-page analysis.
- The plan is scoped to one usability feature and does not change scraping, parsing, or vendor behavior.
