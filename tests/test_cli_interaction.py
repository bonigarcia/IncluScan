from pathlib import Path

import pytest

from incluscan.cli import choose_from_options, choose_text, prompt_choice
from incluscan.models import SnapshotMetadata


def test_choose_from_options_uses_questionary_select(monkeypatch):
    calls = []

    class FakePrompt:
        def ask(self):
            calls.append("ask")
            return "Scanner"

    def fake_select(message, choices, default=None, **kwargs):
        calls.append((message, tuple(choices), default, kwargs))
        return FakePrompt()

    monkeypatch.setattr("incluscan.cli.questionary.select", fake_select)

    result = choose_from_options("Choose mode", ["Scrapper", "Scanner"], default="Scrapper")

    assert result == "Scanner"
    assert calls == [("Choose mode", ("Scrapper", "Scanner"), "Scrapper", {}), "ask"]


def test_choose_text_uses_questionary_text(monkeypatch):
    calls = []

    class FakePrompt:
        def ask(self):
            calls.append("ask")
            return "https://www.uc3m.es/"

    def fake_text(message, default=None):
        calls.append((message, default))
        return FakePrompt()

    monkeypatch.setattr("incluscan.cli.questionary.text", fake_text)

    result = choose_text("Base URL")

    assert result == "https://www.uc3m.es/"
    assert calls == [("Base URL", None), "ask"]


def test_choose_text_omits_default_when_not_provided(monkeypatch):
    calls = []

    class FakePrompt:
        def ask(self):
            calls.append("ask")
            return "https://www.uc3m.es/"

    def fake_text(message, **kwargs):
        calls.append((message, kwargs))
        return FakePrompt()

    monkeypatch.setattr("incluscan.cli.questionary.text", fake_text)

    result = choose_text("Base URL")

    assert result == "https://www.uc3m.es/"
    assert calls == [("Base URL", {}), "ask"]


def test_choose_text_passes_default_to_questionary_text(monkeypatch):
    calls = []

    class FakePrompt:
        def ask(self):
            calls.append("ask")
            return "https://www.uc3m.es/"

    def fake_text(message, default=None, **kwargs):
        calls.append((message, default, kwargs))
        return FakePrompt()

    monkeypatch.setattr("incluscan.cli.questionary.text", fake_text)

    result = choose_text("Base URL", default="https://www.uc3m.es/")

    assert result == "https://www.uc3m.es/"
    assert calls == [("Base URL", "https://www.uc3m.es/", {}) , "ask"]


def test_prompt_choice_returns_none_when_cancelled(monkeypatch):
    class FakePrompt:
        def ask(self):
            raise KeyboardInterrupt

    monkeypatch.setattr("incluscan.cli.questionary.select", lambda *args, **kwargs: FakePrompt())

    assert prompt_choice("Choose mode", ["Scrapper", "Scanner"], default="Scrapper") is None


def test_format_snapshot_label_shows_base_url_and_friendly_date():
    snapshot = SnapshotMetadata(
        snapshot_id="snapshot-453f5211",
        base_url="https://www.uc3m.es/",
        fetched_at="2026-05-26T10:00:03.791181+00:00",
    )

    from incluscan.cli import format_snapshot_label

    assert format_snapshot_label(snapshot, 42) == "UC3M — fetched 2026-05-26 10:00 (42 pages)"


def test_scraper_prompt_helpers_include_explanations(monkeypatch):
    calls = []

    def fake_text(message, **kwargs):
        calls.append((message, kwargs))

        class FakePrompt:
            def ask(self):
                return "100"

        return FakePrompt()

    def fake_select(message, choices, default=None, **kwargs):
        calls.append((message, tuple(choices), default, kwargs))

        class FakePrompt:
            def ask(self):
                return "No"

        return FakePrompt()

    monkeypatch.setattr("incluscan.cli.questionary.text", fake_text)
    monkeypatch.setattr("incluscan.cli.questionary.select", fake_select)

    from incluscan.cli import prompt_page_cap, prompt_extended_crawl

    assert prompt_page_cap() == 100
    assert prompt_extended_crawl() is False
    assert calls[0][0] == "Page cap"
    assert calls[0][1]["instruction"] == "Maximum number of pages to fetch before stopping."
    assert calls[1][0].startswith("Enable extended crawl overrides?")
    assert "Follow extra in-site links beyond sitemap discovery for deeper coverage." in calls[1][0]


def test_run_scraper_wraps_work_with_spinners(monkeypatch):
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

    from incluscan.cli import run_scraper

    run_scraper(FakeConsole())

    assert events == ["Crawling site", "Writing snapshot"]


def test_run_scraper_uses_default_base_url(monkeypatch):
    calls = []

    monkeypatch.setattr("incluscan.cli.choose_text", lambda message, default=None: calls.append((message, default)) or "https://www.uc3m.es/")
    monkeypatch.setattr("incluscan.cli.prompt_page_cap", lambda: 100)
    monkeypatch.setattr("incluscan.cli.prompt_extended_crawl", lambda: False)
    monkeypatch.setattr("incluscan.cli.crawl_site", lambda *args, **kwargs: ("snapshot", ["page"]))
    monkeypatch.setattr("incluscan.cli.write_snapshot", lambda *args, **kwargs: Path("docs/snapshots/snapshot.jsonl"))
    monkeypatch.setattr("incluscan.cli.run_with_spinner", lambda console, message, fn: fn())

    class FakeConsole:
        def print(self, *_args, **_kwargs):
            return None

    from incluscan.cli import run_scraper

    run_scraper(FakeConsole())

    assert calls == [("Base URL", "https://www.uc3m.es/")]


def test_run_scanner_wraps_work_with_spinners(monkeypatch):
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

    from incluscan.cli import run_scanner

    run_scanner(FakeConsole())

    assert events == ["Loading snapshot", "Generating report", "Writing reports"]
