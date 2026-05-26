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


def _choose_snapshot_path(console: Console) -> Path:
    snapshots = sorted(SNAPSHOT_DIR.glob("*.jsonl"))
    if not snapshots:
        raise RuntimeError("No snapshots available. Run Scrapper first.")
    selected = Prompt.ask("Choose snapshot path", choices=[str(path) for path in snapshots], console=console)
    return Path(selected)


def _choose_vendor(console: Console):
    vendors = discover_vendors()
    if not vendors:
        raise RuntimeError("No AI vendors available.")
    vendor_name = Prompt.ask("Choose vendor", choices=[vendor.name for vendor in vendors], console=console)
    vendor = next(item for item in vendors if item.name == vendor_name)
    api_key = os.getenv(vendor.api_key_env) if vendor.api_key_env else None
    return vendor.name, api_key


def run_scraper(console: Console) -> None:
    base_url = Prompt.ask("Base URL", console=console)
    page_cap = int(Prompt.ask("Page cap", default="100", console=console))
    allow_extended = Confirm.ask("Enable extended crawl overrides?", default=False, console=console)
    snapshot, pages = crawl_site(base_url, page_cap=page_cap, allow_extended=allow_extended)
    snapshot_path = write_snapshot(SNAPSHOT_DIR, snapshot, pages)
    console.print(f"Saved snapshot to {snapshot_path}")


def run_scanner(console: Console) -> None:
    snapshot_path = _choose_snapshot_path(console)
    snapshot, pages = read_snapshot(snapshot_path)

    vendor_name, api_key = _choose_vendor(console)
    models = list_models_for_vendor(vendor_name, api_key=api_key)
    if not models:
        raise RuntimeError(f"No models available for {vendor_name}.")
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
