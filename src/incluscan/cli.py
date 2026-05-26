import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import questionary
from rich.console import Console
from rich.prompt import Prompt

from incluscan.config import REPORT_DIR, SNAPSHOT_DIR
from incluscan.report import build_run_page, write_reports
from incluscan.scraper import crawl_site
from incluscan.scanner import build_request_completion, scan_snapshot
from incluscan.storage import read_snapshot, read_snapshot_metadata, write_snapshot
from incluscan.ui import run_with_spinner
from incluscan.vendors import discover_vendors, list_models_for_vendor


def choose_from_options(message: str, choices: list[str], default: str | None = None) -> str:
    return prompt_choice(message, choices, default=default)


def choose_text(message: str, default: str | None = None) -> str:
    return prompt_input(message, default=default)


def prompt_choice(message: str, choices: list[str], default: str | None = None) -> str | None:
    try:
        return questionary.select(message, choices=choices, default=default).ask()
    except (KeyboardInterrupt, EOFError):
        return None


def prompt_input(message: str, default: str | None = None, **kwargs) -> str | None:
    if default is None:
        try:
            return questionary.text(message, **kwargs).ask()
        except (KeyboardInterrupt, EOFError):
            return None
    try:
        return questionary.text(message, default=default, **kwargs).ask()
    except (KeyboardInterrupt, EOFError):
        return None


def prompt_page_cap() -> int:
    value = prompt_input(
        "Page cap",
        default="100",
        instruction="Maximum number of pages to fetch before stopping.",
    )
    return int(value) if value is not None else 100


def prompt_extended_crawl() -> bool:
    value = prompt_choice(
        "Enable extended crawl overrides?\nFollow extra in-site links beyond sitemap discovery for deeper coverage.",
        ["No", "Yes"],
        default="No",
    )
    return value == "Yes"


def format_snapshot_label(snapshot, page_count: int) -> str:
    fetched_at = datetime.fromisoformat(snapshot.fetched_at.replace("Z", "+00:00"))
    friendly_date = fetched_at.strftime("%Y-%m-%d %H:%M")
    parsed = urlparse(snapshot.base_url)
    hostname = (parsed.hostname or snapshot.base_url).removeprefix("www.")
    label_site = hostname.split(".")[0].upper()
    return f"{label_site} — fetched {friendly_date} ({page_count} pages)"


def ask_mode(console: Console) -> str:
    return choose_from_options("Choose mode", ["Scrapper", "Scanner"], default="Scrapper") or "Scrapper"


def _choose_snapshot_path(console: Console) -> Path:
    snapshots = sorted(SNAPSHOT_DIR.glob("*.jsonl"))
    if not snapshots:
        raise RuntimeError("No snapshots available. Run Scrapper first.")
    labeled_snapshots = []
    for path in snapshots:
        snapshot = read_snapshot_metadata(path)
        page_count = max(len(path.read_text(encoding="utf-8").splitlines()) - 1, 0)
        labeled_snapshots.append((format_snapshot_label(snapshot, page_count), str(path)))
    selected = choose_from_options("Choose snapshot", [label for label, _ in labeled_snapshots])
    if selected is None:
        raise KeyboardInterrupt
    selected = next(path for label, path in labeled_snapshots if label == selected)
    return Path(selected)


def _choose_vendor(console: Console):
    vendors = discover_vendors()
    if not vendors:
        raise RuntimeError("No AI vendors available.")
    vendor_name = choose_from_options("Choose vendor", [vendor.name for vendor in vendors])
    if vendor_name is None:
        raise KeyboardInterrupt
    vendor = next(item for item in vendors if item.name == vendor_name)
    api_key = os.getenv(vendor.api_key_env) if vendor.api_key_env else None
    return vendor.name, api_key


def run_scraper(console: Console) -> None:
    base_url = choose_text("Base URL")
    if base_url is None:
        raise KeyboardInterrupt
    page_cap = prompt_page_cap()
    allow_extended = prompt_extended_crawl()
    snapshot, pages = run_with_spinner(
        console,
        "Crawling site",
        lambda: crawl_site(base_url, page_cap=page_cap, allow_extended=allow_extended),
    )
    snapshot_path = run_with_spinner(console, "Writing snapshot", lambda: write_snapshot(SNAPSHOT_DIR, snapshot, pages))
    console.print(f"Saved snapshot to {snapshot_path}")


def run_scanner(console: Console) -> None:
    snapshot_path = _choose_snapshot_path(console)
    snapshot, pages = run_with_spinner(console, "Loading snapshot", lambda: read_snapshot(snapshot_path))

    vendor_name, api_key = _choose_vendor(console)
    models = list_models_for_vendor(vendor_name, api_key=api_key)
    if not models:
        raise RuntimeError(f"No models available for {vendor_name}.")
    model = choose_from_options("Choose model", models)
    if model is None:
        raise KeyboardInterrupt

    request_completion = build_request_completion(vendor_name, model, api_key=api_key)
    scan, findings_by_url = scan_snapshot(snapshot, pages, request_completion, vendor_name, model, with_spinner=lambda message, fn: run_with_spinner(console, message, fn))
    total_pages_analyzed = len(pages)
    run_html = run_with_spinner(console, "Generating report", lambda: build_run_page(scan, findings_by_url, total_pages_analyzed=total_pages_analyzed))
    finding_count = sum(len(findings) for findings in findings_by_url.values())
    run_with_spinner(console, "Writing reports", lambda: write_reports(REPORT_DIR, [scan], {scan.scan_id: run_html}, {scan.scan_id: finding_count}, {scan.scan_id: total_pages_analyzed}))
    console.print(f"Wrote report for {scan.scan_id}")


def main(argv: list[str] | None = None) -> int:
    console = Console()
    try:
        mode = ask_mode(console)
        if mode == "Scrapper":
            run_scraper(console)
        else:
            run_scanner(console)
        return 0
    except KeyboardInterrupt:
        console.print("Cancelled.")
        return 1
