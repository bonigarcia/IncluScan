import pytest

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
