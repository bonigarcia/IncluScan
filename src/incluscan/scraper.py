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

from incluscan.models import ScrapedPage, SnapshotMetadata


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
    queue = deque(dict.fromkeys([base_url, *sitemap_urls]))
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
            try:
                document = extract_pdf_document(temp_pdf, current_url)
            finally:
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
