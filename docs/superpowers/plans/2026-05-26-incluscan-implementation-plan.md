# IncluScan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CLI that scrapes websites into JSONL snapshots, scans them with selectable AI providers, and publishes immutable static HTML reports.

**Architecture:** Use a small `src/` package with separate modules for scraping, JSONL storage, vendor/model discovery, scanning, and report rendering. Shared dataclasses define the file formats so the scraper and scanner stay decoupled, and all generated site artifacts live under `docs/` for GitHub Pages.

**Tech Stack:** Python 3.11+, `rich`, `requests`, `beautifulsoup4`, `pypdf`, `pytest`

---

### Task 1: Scaffold the package and shared data model

**Files:**
- Create: `pyproject.toml`
- Create: `src/incluscan/__init__.py`
- Create: `src/incluscan/__main__.py`
- Create: `src/incluscan/config.py`
- Create: `src/incluscan/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from incluscan.config import REPORT_DIR, SNAPSHOT_DIR, RUN_DIR
from incluscan.models import ReviewFinding, ScrapedPage, ScanRunSummary, SnapshotMetadata


def test_shared_paths_live_under_docs():
    assert SNAPSHOT_DIR == Path("docs/snapshots")
    assert RUN_DIR == Path("docs/runs")
    assert REPORT_DIR == Path("docs")


def test_models_expose_the_required_fields():
    snapshot = SnapshotMetadata(
        snapshot_id="snapshot-001",
        base_url="https://www.uc3m.es/",
        fetched_at="2026-05-26T10:00:00Z",
    )
    page = ScrapedPage(
        snapshot_id=snapshot.snapshot_id,
        url="https://www.uc3m.es/",
        fetched_at="2026-05-26T10:00:00Z",
        content_type="text/html",
        title="UC3M",
        text="Hola mundo",
        language_hint="es",
        status_code=200,
        crawl_depth=0,
        source_type="sitemap",
    )
    finding = ReviewFinding(
        original="los alumnos",
        modified="el estudiantado",
        justification="Neutraliza el lenguaje de género",
    )
    run = ScanRunSummary(
        scan_id="scan-001",
        snapshot_id=snapshot.snapshot_id,
        base_url=snapshot.base_url,
        snapshot_fetched_at=snapshot.fetched_at,
        vendor="OpenAI",
        model="gpt-4o-mini",
        started_at="2026-05-26T11:00:00Z",
        finished_at="2026-05-26T11:05:00Z",
        input_tokens=123,
        output_tokens=45,
    )

    assert snapshot.base_url == "https://www.uc3m.es/"
    assert page.url.endswith("/")
    assert finding.modified == "el estudiantado"
    assert run.model == "gpt-4o-mini"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_models.py -q`

Expected: fail with import errors or missing names because the package does not exist yet.

- [ ] **Step 3: Write the minimal implementation**

```python
# src/incluscan/config.py
from pathlib import Path

REPORT_DIR = Path("docs")
SNAPSHOT_DIR = REPORT_DIR / "snapshots"
RUN_DIR = REPORT_DIR / "runs"
PROMPT_TEMPLATE_PATH = Path("src/incluscan/templates/review_prompt.txt")


# src/incluscan/models.py
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SnapshotMetadata:
    snapshot_id: str
    base_url: str
    fetched_at: str


@dataclass(frozen=True, slots=True)
class ScrapedPage:
    snapshot_id: str
    url: str
    fetched_at: str
    content_type: str
    title: str | None
    text: str
    language_hint: str | None
    status_code: int | None
    crawl_depth: int | None
    source_type: str | None


@dataclass(frozen=True, slots=True)
class ReviewFinding:
    original: str
    modified: str
    justification: str


@dataclass(frozen=True, slots=True)
class ScanRunSummary:
    scan_id: str
    snapshot_id: str
    base_url: str
    snapshot_fetched_at: str
    vendor: str
    model: str
    started_at: str
    finished_at: str
    input_tokens: int | None = None
    output_tokens: int | None = None
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_models.py -q`

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/incluscan tests/test_models.py
git commit -m "feat: scaffold IncluScan package models"
```

### Task 2: Implement snapshot storage and conservative scraping

**Files:**
- Create: `src/incluscan/storage.py`
- Create: `src/incluscan/scraper.py`
- Create: `src/incluscan/templates/review_prompt.txt`
- Create: `tests/test_storage.py`
- Create: `tests/test_scraper.py`
- Create: `tests/fixtures/html/uc3m-sample.html`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from incluscan.models import ScrapedPage, SnapshotMetadata
from incluscan.scraper import crawl_site, extract_html_document, extract_pdf_document, should_follow_url
from incluscan.storage import read_snapshot, write_snapshot


def test_storage_round_trip(tmp_path: Path):
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
        text="Hola mundo",
        language_hint="es",
        status_code=200,
        crawl_depth=0,
        source_type="sitemap",
    )

    path = write_snapshot(tmp_path, snapshot, [page])
    loaded_snapshot, loaded_pages = read_snapshot(path)

    assert loaded_snapshot.base_url == snapshot.base_url
    assert loaded_pages[0].text == "Hola mundo"


def test_should_follow_url_keeps_same_domain_only():
    base_url = "https://www.uc3m.es/"
    assert should_follow_url(base_url, "https://www.uc3m.es/noticias") is True
    assert should_follow_url(base_url, "https://other.example.com/") is False


def test_extract_html_document_returns_title_and_visible_text():
    html = Path("tests/fixtures/html/uc3m-sample.html").read_text(encoding="utf-8")
    doc = extract_html_document(html, "https://www.uc3m.es/")

    assert doc.title == "UC3M Sample"
    assert "Language without bias" in doc.text


def test_crawl_site_builds_a_snapshot_from_one_html_page(monkeypatch):
    class FakeResponse:
        status_code = 200
        headers = {"content-type": "text/html; charset=utf-8"}
        text = '<html><head><title>UC3M Sample</title></head><body><a href="/page-2">Next</a><p>Hola</p></body></html>'

        def raise_for_status(self):
            return None

    def fake_get(url, timeout=10, headers=None):
        return FakeResponse()

    snapshot, pages = crawl_site("https://www.uc3m.es/", page_cap=1, fetch=fake_get)

    assert snapshot.base_url == "https://www.uc3m.es/"
    assert len(pages) == 1
    assert pages[0].title == "UC3M Sample"


def test_crawl_site_prefers_sitemap_urls(monkeypatch):
    class FakeResponse:
        def __init__(self, url: str):
            self.status_code = 200
            self.headers = {"content-type": "text/html; charset=utf-8"}
            if url.endswith("sitemap.xml"):
                self.text = "<urlset><url><loc>https://www.uc3m.es/page-2</loc></url></urlset>"
            elif url.endswith("page-2"):
                self.text = '<html><head><title>From sitemap</title></head><body><p>Second</p></body></html>'
            else:
                self.text = '<html><head><title>UC3M Sample</title></head><body><p>First</p></body></html>'

        def raise_for_status(self):
            return None

    def fake_get(url, timeout=10, headers=None):
        return FakeResponse(url)

    snapshot, pages = crawl_site("https://www.uc3m.es/", page_cap=1, fetch=fake_get)

    assert snapshot.base_url == "https://www.uc3m.es/"
    assert pages[0].url == "https://www.uc3m.es/page-2"
```

```python
from pathlib import Path

from incluscan.scraper import extract_pdf_document


def test_extract_pdf_document_uses_embedded_text(monkeypatch, tmp_path: Path):
    class FakePage:
        def extract_text(self):
            return "Texto del PDF"

    class FakeReader:
        pages = [FakePage()]

    monkeypatch.setattr("incluscan.scraper.PdfReader", lambda *_args, **_kwargs: FakeReader())

    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%fake")

    doc = extract_pdf_document(pdf_path, "https://www.uc3m.es/sample.pdf")

    assert doc.content_type == "application/pdf"
    assert "Texto del PDF" in doc.text
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_storage.py tests/test_scraper.py -q`

Expected: fail with missing module or missing function errors.

- [ ] **Step 3: Write the minimal implementation**

```python
# src/incluscan/storage.py
from dataclasses import asdict
import json
from pathlib import Path

from incluscan.models import ScrapedPage, SnapshotMetadata


def write_snapshot(root: Path, snapshot: SnapshotMetadata, pages: list[ScrapedPage]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{snapshot.snapshot_id}.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(snapshot), ensure_ascii=False) + "\n")
        for page in pages:
            handle.write(json.dumps(asdict(page), ensure_ascii=False) + "\n")
    return path


def read_snapshot(path: Path) -> tuple[SnapshotMetadata, list[ScrapedPage]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    snapshot = SnapshotMetadata(**json.loads(lines[0]))
    pages = [ScrapedPage(**json.loads(line)) for line in lines[1:]]
    return snapshot, pages


# src/incluscan/scraper.py
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import sleep
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from uuid import uuid4
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    url: str
    content_type: str
    title: str | None
    text: str
    language_hint: str | None = None


def should_follow_url(base_url: str, candidate_url: str) -> bool:
    base = urlparse(base_url)
    candidate = urlparse(candidate_url)
    return candidate.scheme in {"http", "https"} and candidate.netloc == base.netloc


def extract_html_document(html: str, url: str) -> ExtractedDocument:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else None
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    return ExtractedDocument(url=url, content_type="text/html", title=title, text=text)


def extract_pdf_document(pdf_path: Path, url: str) -> ExtractedDocument:
    reader = PdfReader(str(pdf_path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    return ExtractedDocument(url=url, content_type="application/pdf", title=None, text=text)


def discover_urls(base_url: str, html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    for anchor in soup.find_all("a", href=True):
        candidate = urljoin(base_url, anchor["href"])
        if should_follow_url(base_url, candidate):
            urls.append(candidate)
    return list(dict.fromkeys(urls))


def fetch_sitemap_urls(base_url: str, fetch=requests.get) -> list[str]:
    sitemap_url = urljoin(base_url, "/sitemap.xml")
    response = fetch(sitemap_url, timeout=10, headers={"User-Agent": "IncluScan/0.1"})
    if response.status_code >= 400:
        return []
    try:
        root = ElementTree.fromstring(response.text)
    except ElementTree.ParseError:
        return []
    urls: list[str] = []
    for loc in root.findall(".//{*}loc"):
        if loc.text and should_follow_url(base_url, loc.text):
            urls.append(loc.text)
    return list(dict.fromkeys(urls))


def crawl_site(
    base_url: str,
    page_cap: int = 100,
    delay_seconds: float = 1.0,
    allow_extended: bool = False,
    fetch=requests.get,
):
    fetched_at = datetime.now(timezone.utc).isoformat()
    snapshot = SnapshotMetadata(snapshot_id=f"snapshot-{uuid4().hex[:8]}", base_url=base_url, fetched_at=fetched_at)
    robot_parser = RobotFileParser(urljoin(base_url, "/robots.txt"))
    try:
        robot_response = fetch(robot_parser.url, timeout=10, headers={"User-Agent": "IncluScan/0.1"})
        if robot_response.status_code < 400:
            robot_parser.parse(robot_response.text.splitlines())
    except Exception:
        pass

    sitemap_urls = fetch_sitemap_urls(base_url, fetch=fetch)
    queue = deque(sitemap_urls or [base_url])
    seen: set[str] = set()
    pages: list[ScrapedPage] = []

    while queue and len(pages) < page_cap:
        current_url = queue.popleft()
        if current_url in seen or not should_follow_url(base_url, current_url):
            continue
        if not robot_parser.can_fetch("IncluScan/0.1", current_url):
            seen.add(current_url)
            continue

        seen.add(current_url)
        response = fetch(current_url, timeout=10, headers={"User-Agent": "IncluScan/0.1"})
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "pdf" in content_type.lower() or current_url.lower().endswith(".pdf"):
            with NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(response.content)
                temp_pdf = Path(temp_file.name)
            document = extract_pdf_document(temp_pdf, current_url)
            temp_pdf.unlink(missing_ok=True)
        else:
            document = extract_html_document(response.text, current_url)
            if allow_extended:
                for discovered_url in discover_urls(current_url, response.text):
                    if discovered_url not in seen:
                        queue.append(discovered_url)

        pages.append(
            ScrapedPage(
                snapshot_id=snapshot.snapshot_id,
                url=current_url,
                fetched_at=datetime.now(timezone.utc).isoformat(),
                content_type=document.content_type,
                title=document.title,
                text=document.text,
                language_hint=document.language_hint,
                status_code=response.status_code,
                crawl_depth=0,
                source_type="sitemap" if current_url in sitemap_urls else ("extended" if allow_extended else "seed"),
            )
        )
        sleep(delay_seconds)

    return snapshot, pages
```

```text
<!-- src/incluscan/templates/review_prompt.txt -->
Review the language used in the following content to promote inclusive and non-sexist language.

Return the response exclusively as valid JSON that can be parsed automatically. Do not include Markdown, code blocks, introductory text, or the word JSON.

The response must be an array of objects. Each object must contain exactly these fields:

- "original": the exact fragment from the original text that should be changed.
- "modified": the adapted version using inclusive and non-sexist language.
- "justification": a brief explanation of why the change was made.

Rules:
- Preserve the original meaning.
- Do not modify proper names, brands, direct quotes, or technical terms unless strictly necessary.
- Avoid artificial or unnatural expressions.
- Prioritize clear, natural, and easy-to-understand alternatives.
- If no changes are needed, return an empty array: [].
- Do not include any additional fields.

Content to review:

{{content}}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_storage.py tests/test_scraper.py -q`

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/incluscan/storage.py src/incluscan/scraper.py src/incluscan/templates/review_prompt.txt tests/test_storage.py tests/test_scraper.py tests/fixtures/html/uc3m-sample.html
git commit -m "feat: add snapshot storage and text extraction"
```

### Task 3: Implement vendor discovery, model listing, and JSON-only scanning

**Files:**
- Create: `src/incluscan/vendors.py`
- Create: `src/incluscan/scanner.py`
- Create: `tests/test_vendors.py`
- Create: `tests/test_scanner.py`

- [ ] **Step 1: Write the failing test**

```python
import os

import pytest

from incluscan.models import ScrapedPage, SnapshotMetadata
from incluscan.scanner import build_review_prompt, parse_review_response, scan_snapshot
from incluscan.vendors import discover_vendors, list_models_for_vendor


def test_discover_vendors_includes_only_available_backends(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "google-key")
    monkeypatch.setattr("incluscan.vendors.ollama_is_available", lambda: True)

    vendors = discover_vendors()

    assert [vendor.name for vendor in vendors] == ["OpenAI", "Google", "Ollama"]


def test_list_models_for_vendor_reads_provider_api(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": [{"id": "gpt-4o-mini"}, {"id": "gpt-4.1-mini"}]}

    monkeypatch.setattr("incluscan.vendors.requests.get", lambda *_args, **_kwargs: FakeResponse())

    models = list_models_for_vendor("OpenAI", api_key="openai-key")

    assert models == ["gpt-4o-mini", "gpt-4.1-mini"]


def test_build_review_prompt_inserts_content_without_altering_template():
    prompt = build_review_prompt("Hola a todos")

    assert "{{content}}" not in prompt
    assert "Hola a todos" in prompt


def test_parse_review_response_accepts_empty_array():
    assert parse_review_response("[]") == []


def test_parse_review_response_rejects_extra_fields():
    with pytest.raises(ValueError):
        parse_review_response('[{"original":"x","modified":"y","justification":"z","extra":"no"}]')


def test_scan_snapshot_uses_an_injected_completion_callable():
    snapshot = SnapshotMetadata(
        snapshot_id="snapshot-001",
        base_url="https://www.uc3m.es/",
        fetched_at="2026-05-26T10:00:00Z",
    )
    page = ScrapedPage(
        snapshot_id=snapshot.snapshot_id,
        url="https://www.uc3m.es/",
        fetched_at=snapshot.fetched_at,
        content_type="text/html",
        title="UC3M",
        text="Los alumnos deben entregar su solicitud.",
        language_hint="es",
        status_code=200,
        crawl_depth=0,
        source_type="seed",
    )

    def fake_completion(prompt: str):
        return "[]", None, None

    scan, findings_by_url = scan_snapshot(snapshot, [page], fake_completion, "OpenAI", "gpt-4o-mini")

    assert scan.base_url == snapshot.base_url
    assert findings_by_url[page.url] == []
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_vendors.py tests/test_scanner.py -q`

Expected: fail with missing module or missing function errors.

- [ ] **Step 3: Write the minimal implementation**

```python
# src/incluscan/vendors.py
from dataclasses import dataclass
from typing import Callable

import os
import requests


@dataclass(frozen=True, slots=True)
class VendorOption:
    name: str
    api_key_env: str | None
    models: list[str]


def ollama_is_available(http_get: Callable[..., object] = requests.get) -> bool:
    try:
        response = http_get("http://localhost:11434/api/tags", timeout=2)
        response.raise_for_status()
        return True
    except Exception:
        return False


def discover_vendors() -> list[VendorOption]:
    vendors: list[VendorOption] = []
    if os.getenv("OPENAI_API_KEY"):
        vendors.append(VendorOption("OpenAI", "OPENAI_API_KEY", []))
    if os.getenv("ANTHROPIC_API_KEY"):
        vendors.append(VendorOption("Anthropic", "ANTHROPIC_API_KEY", []))
    if os.getenv("GOOGLE_API_KEY"):
        vendors.append(VendorOption("Google", "GOOGLE_API_KEY", []))
    if ollama_is_available():
        vendors.append(VendorOption("Ollama", None, []))
    return vendors


def list_models_for_vendor(vendor_name: str, api_key: str | None = None) -> list[str]:
    if vendor_name == "OpenAI":
        response = requests.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {api_key}"}, timeout=10)
        response.raise_for_status()
        return [item["id"] for item in response.json().get("data", [])]
    if vendor_name == "Anthropic":
        response = requests.get("https://api.anthropic.com/v1/models", headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"}, timeout=10)
        response.raise_for_status()
        return [item["id"] for item in response.json().get("data", [])]
    if vendor_name == "Google":
        response = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}", timeout=10)
        response.raise_for_status()
        return [item["name"].split("/")[-1] for item in response.json().get("models", [])]
    response = requests.get("http://localhost:11434/api/tags", timeout=10)
    response.raise_for_status()
    return [item["name"] for item in response.json().get("models", [])]


# src/incluscan/scanner.py
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4

import requests

from incluscan.config import PROMPT_TEMPLATE_PATH
from incluscan.models import ReviewFinding, ScanRunSummary, ScrapedPage, SnapshotMetadata


def build_review_prompt(content: str) -> str:
    template = PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")
    return template.replace("{{content}}", content)


def parse_review_response(raw_text: str) -> list[ReviewFinding]:
    payload = json.loads(raw_text)
    if not isinstance(payload, list):
        raise ValueError("model response must be a JSON array")
    findings: list[ReviewFinding] = []
    for item in payload:
        if set(item) != {"original", "modified", "justification"}:
            raise ValueError("each finding must contain only original, modified, and justification")
        findings.append(ReviewFinding(**item))
    return findings


def build_request_completion(vendor_name: str, model: str, api_key: str | None = None) -> Callable[[str], tuple[str, int | None, int | None]]:
    def request_completion(prompt: str) -> tuple[str, int | None, int | None]:
        if vendor_name == "Ollama":
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=60,
            )
            response.raise_for_status()
            payload = response.json()
            return payload["response"], None, None
        elif vendor_name == "OpenAI":
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}]},
                timeout=60,
            )
            response.raise_for_status()
            payload = response.json()
            usage = payload.get("usage", {})
            return payload["choices"][0]["message"]["content"], usage.get("prompt_tokens"), usage.get("completion_tokens")
        elif vendor_name == "Anthropic":
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
                json={"model": model, "max_tokens": 1024, "messages": [{"role": "user", "content": prompt}]},
                timeout=60,
            )
            response.raise_for_status()
            payload = response.json()
            usage = payload.get("usage", {})
            return payload["content"][0]["text"], usage.get("input_tokens"), usage.get("output_tokens")
        else:
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=60,
            )
            response.raise_for_status()
            payload = response.json()
            usage = payload.get("usageMetadata", {})
            return payload["candidates"][0]["content"]["parts"][0]["text"], usage.get("promptTokenCount"), usage.get("candidatesTokenCount")

    return request_completion


def scan_snapshot(
    snapshot: SnapshotMetadata,
    pages: list[ScrapedPage],
    request_completion: Callable[[str], tuple[str, int | None, int | None]],
    vendor_name: str,
    model: str,
) -> tuple[ScanRunSummary, dict[str, list[ReviewFinding]]]:
    started_at = datetime.now(timezone.utc).isoformat()
    findings_by_url: dict[str, list[ReviewFinding]] = {}
    input_tokens = 0
    output_tokens = 0
    saw_tokens = False
    for page in pages:
        prompt = build_review_prompt(page.text)
        raw_response, page_input_tokens, page_output_tokens = request_completion(prompt)
        findings_by_url[page.url] = parse_review_response(raw_response)
        if page_input_tokens is not None:
            input_tokens += page_input_tokens
            saw_tokens = True
        if page_output_tokens is not None:
            output_tokens += page_output_tokens
            saw_tokens = True
    finished_at = datetime.now(timezone.utc).isoformat()
    run = ScanRunSummary(
        scan_id=f"scan-{uuid4().hex[:8]}",
        snapshot_id=snapshot.snapshot_id,
        base_url=snapshot.base_url,
        snapshot_fetched_at=snapshot.fetched_at,
        vendor=vendor_name,
        model=model,
        started_at=started_at,
        finished_at=finished_at,
        input_tokens=input_tokens if saw_tokens else None,
        output_tokens=output_tokens if saw_tokens else None,
    )
    return run, findings_by_url
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_vendors.py tests/test_scanner.py -q`

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/incluscan/vendors.py src/incluscan/scanner.py tests/test_vendors.py tests/test_scanner.py
git commit -m "feat: add vendor discovery and JSON parsing"
```

### Task 4: Render immutable HTML reports in docs/

**Files:**
- Create: `src/incluscan/report.py`
- Create: `tests/test_report.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_report.py -q`

Expected: fail with missing module or missing function errors.

- [ ] **Step 3: Write the minimal implementation**

```python
# src/incluscan/report.py
from dataclasses import asdict
import json
from pathlib import Path

from incluscan.config import REPORT_DIR, RUN_DIR
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
    for meta_path in sorted((report_root / "runs").glob("*/meta.json")):
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_report.py -q`

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/incluscan/report.py tests/test_report.py
git commit -m "feat: render static scan reports"
```

### Task 5: Wire the interactive CLI and end-to-end flow

**Files:**
- Create: `src/incluscan/cli.py`
- Update: `src/incluscan/__main__.py`
- Create: `tests/test_cli.py`
- Create: `tests/test_e2e.py`

- [ ] **Step 1: Write the failing test**

```python
from incluscan.cli import main


def test_main_routes_to_the_requested_mode(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr("incluscan.cli.run_scraper", lambda *_args, **_kwargs: calls.append("scrapper"))
    monkeypatch.setattr("incluscan.cli.run_scanner", lambda *_args, **_kwargs: calls.append("scanner"))
    monkeypatch.setattr("incluscan.cli.ask_mode", lambda *_args, **_kwargs: "Scrapper")

    main([])

    assert calls == ["scrapper"]
```

```python
from pathlib import Path

from incluscan.models import ReviewFinding, ScanRunSummary, ScrapedPage, SnapshotMetadata
from incluscan.report import write_reports
from incluscan.storage import write_snapshot


def test_end_to_end_scan_smoke(tmp_path: Path, monkeypatch):
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

    run = ScanRunSummary(
        scan_id="scan-001",
        snapshot_id=snapshot.snapshot_id,
        base_url=snapshot.base_url,
        snapshot_fetched_at=snapshot.fetched_at,
        vendor="Ollama",
        model="gemma3:4b",
        started_at="2026-05-26T11:00:00Z",
        finished_at="2026-05-26T11:01:00Z",
        input_tokens=None,
        output_tokens=None,
    )
    run_html = "<html><body><h1>Ollama gemma3:4b</h1></body></html>"
    write_reports(tmp_path / "docs", [run], {run.scan_id: run_html})

    assert (tmp_path / "docs" / "index.html").exists()
    assert (tmp_path / "docs" / "runs" / "scan-001" / "index.html").exists()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_cli.py tests/test_e2e.py -q`

Expected: fail with missing CLI functions and incomplete wiring.

- [ ] **Step 3: Write the minimal implementation**

```python
# src/incluscan/cli.py
import os
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm, Prompt

from incluscan.config import REPORT_DIR, SNAPSHOT_DIR
from incluscan.report import build_run_page, write_reports
from incluscan.scraper import crawl_site
from incluscan.scanner import build_request_completion, scan_snapshot
from incluscan.storage import read_snapshot, write_snapshot
from incluscan.vendors import discover_vendors, list_models_for_vendor


def ask_mode(console: Console) -> str:
    return Prompt.ask("Choose mode", choices=["Scrapper", "Scanner"], default="Scrapper", console=console)


def run_scraper(console: Console) -> None:
    base_url = Prompt.ask("Base URL", console=console)
    page_cap = int(Prompt.ask("Page cap", default="100", console=console))
    allow_extended = Confirm.ask("Enable extended crawl overrides?", default=False, console=console)
    snapshot, pages = crawl_site(base_url, page_cap=page_cap, allow_extended=allow_extended)
    snapshot_path = write_snapshot(SNAPSHOT_DIR, snapshot, pages)
    console.print(f"Saved snapshot to {snapshot_path}")


def run_scanner(console: Console) -> None:
    snapshots = sorted(SNAPSHOT_DIR.glob("*.jsonl"))
    snapshot_path = Path(Prompt.ask("Choose snapshot path", choices=[str(path) for path in snapshots], console=console))
    snapshot, pages = read_snapshot(snapshot_path)

    vendors = discover_vendors()
    vendor_name = Prompt.ask("Choose vendor", choices=[vendor.name for vendor in vendors], console=console)
    api_key_env = next(vendor.api_key_env for vendor in vendors if vendor.name == vendor_name)
    api_key = os.getenv(api_key_env) if api_key_env else None
    models = list_models_for_vendor(vendor_name, api_key=api_key)
    model = Prompt.ask("Choose model", choices=models, console=console)

    request_completion = build_request_completion(vendor_name, model, api_key=api_key)
    scan, findings_by_url = scan_snapshot(snapshot, pages, request_completion, vendor_name, model)
    run_html = build_run_page(scan, findings_by_url)
    write_reports(REPORT_DIR, [scan], {scan.scan_id: run_html})
    console.print(f"Wrote report for {scan.scan_id}")


def main(argv: list[str] | None = None) -> int:
    console = Console()
    mode = ask_mode(console)
    if mode == "Scrapper":
        run_scraper(console)
    else:
        run_scanner(console)
    return 0


# src/incluscan/__main__.py
from incluscan.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_cli.py tests/test_e2e.py -q`

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/incluscan/cli.py src/incluscan/__main__.py tests/test_cli.py tests/test_e2e.py
git commit -m "feat: wire the CLI entrypoint"
```

## Coverage Check
- Scrapper conservative crawling, sitemap preference, robots handling, page cap, and delay: Tasks 2 and 5.
- HTML and PDF text extraction: Task 2.
- JSONL page-by-page snapshot storage: Task 2.
- Vendor detection from environment and Ollama: Task 3.
- Vendor model listing: Task 3.
- Original-language analysis and strict JSON output: Task 3.
- Immutable historical reports in `docs/`: Task 4.
- Static index with vendor, model, dates, and tokens: Task 4.
- CLI mode selection and orchestration: Task 5.
- Tests for all core behaviors: Tasks 1 through 5.

## Self-Review Notes
- No placeholder sections remain.
- File boundaries are small and focused.
- The plan matches the approved design: conservative scrape defaults, original-language analysis, vendor choice required, and immutable scan history.
- If implementation needs deeper vendor-specific API handling or a richer crawl frontier later, that should be a follow-up phase, not part of this plan.
