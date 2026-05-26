import pytest
import requests

from incluscan.config import PROMPT_TEMPLATE_PATH
from incluscan.scanner import build_review_prompt, parse_review_response, scan_snapshot
from incluscan.models import ScrapedPage, SnapshotMetadata
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


def test_prompt_template_is_markdown_file():
    assert PROMPT_TEMPLATE_PATH.name == "review_prompt.md"


def test_parse_review_response_accepts_empty_array():
    assert parse_review_response("[]") == []


def test_parse_review_response_rejects_extra_fields():
    with pytest.raises(ValueError):
        parse_review_response('[{"original":"x","modified":"y","justification":"z","extra":"no"}]')


def test_parse_review_response_extracts_json_from_wrapped_text():
    raw = "Sure, here you go:\n```json\n[{\"original\":\"los alumnos\",\"modified\":\"el estudiantado\",\"justification\":\"Neutraliza el lenguaje de género\"}]\n```"

    findings = parse_review_response(raw)

    assert len(findings) == 1
    assert findings[0].modified == "el estudiantado"


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


def test_scan_snapshot_retries_invalid_json_once():
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

    prompts: list[str] = []

    def fake_completion(prompt: str):
        prompts.append(prompt)
        if len(prompts) == 1:
            return "not json", None, None
        return "[]", None, None

    scan, findings_by_url = scan_snapshot(snapshot, [page], fake_completion, "OpenAI", "gpt-4o-mini")

    assert len(prompts) == 2
    assert findings_by_url[page.url] == []


def test_scan_snapshot_records_timeout_as_empty_findings():
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
        raise requests.ReadTimeout("timed out")

    scan, findings_by_url = scan_snapshot(snapshot, [page], fake_completion, "Ollama", "gemma3:1b")

    assert findings_by_url[page.url] == []


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


def test_scan_snapshot_includes_page_title_in_prompt():
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
        title="Estudiantes de la Unión Europea | UC3M",
        text="Contacta con nosotros",
        language_hint="es",
        status_code=200,
        crawl_depth=0,
        source_type="seed",
    )

    prompts: list[str] = []

    def fake_completion(prompt: str):
        prompts.append(prompt)
        return "[]", None, None

    scan_snapshot(snapshot, [page], fake_completion, "Google", "gemini-2.5-flash")

    assert "Estudiantes de la Unión Europea | UC3M" in prompts[0]
    assert "Contacta con nosotros" in prompts[0]
