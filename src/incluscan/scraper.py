"""
(C) Copyright 2026 Boni Garcia (https://bonigarcia.github.io/)
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
 http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import sleep
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser
from uuid import uuid4
from xml.etree import ElementTree
import unicodedata

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


def _crawl_key(base_url: str, candidate_url: str) -> str:
    base = urlparse(base_url)
    normalized = _normalize_crawl_url(candidate_url)
    return normalized._replace(scheme=base.scheme).geturl()


def _normalize_crawl_url(candidate_url: str):
    candidate = urlparse(candidate_url)
    path = candidate.path or "/"
    if path != "/":
        path = path.rstrip("/") or "/"
    query = [(key, value) for key, value in parse_qsl(candidate.query, keep_blank_values=True) if not (key == "d" and value == "Desktop")]
    return candidate._replace(path=path, query=urlencode(query, doseq=True), fragment="", netloc=candidate.netloc.lower())


def _strip_accents(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def _is_soft_404_document(document: ExtractedDocument) -> bool:
    content = " ".join(part for part in [document.title, document.text] if part)
    normalized = _strip_accents(content).lower()
    return (
        "parece que no existe en la web una pagina con esta direccion" in normalized
        or "pruebe a buscar en nuestro sitio web o a navegar por las principales secciones" in normalized
    )


def _document_signature(document: ExtractedDocument) -> str:
    parts = [document.content_type, document.title or "", document.text or ""]
    payload = "\n".join(parts).strip().encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def extract_html_document(html: str, url: str) -> ExtractedDocument:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else None
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text_parts = [soup.get_text(" ", strip=True)]
    for selector in (("meta", {"name": "description"}), ("meta", {"property": "og:description"})):
        meta = soup.find(*selector)
        if meta and meta.get("content"):
            text_parts.append(meta["content"].strip())
    text = " ".join(part for part in dict.fromkeys(part for part in text_parts if part)).strip()
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
    try:
        response = fetch(sitemap_url, timeout=10, headers={"User-Agent": "IncluScan/0.1"})
    except requests.RequestException:
        return []
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
    queue = deque()
    queued_keys: set[str] = set()
    seen_documents: set[str] = set()
    for candidate_url in [base_url, *sitemap_urls]:
        key = _crawl_key(base_url, candidate_url)
        if key not in queued_keys:
            queue.append(candidate_url)
            queued_keys.add(key)
    seen: set[str] = set()
    pages: list[ScrapedPage] = []

    while queue and len(pages) < page_cap:
        current_url = queue.popleft()
        current_key = _crawl_key(base_url, current_url)
        if current_key in seen or not should_follow_url(base_url, current_url):
            continue
        if not robot_parser.can_fetch("IncluScan/0.1", current_url):
            seen.add(current_key)
            continue

        try:
            response = fetch(current_url, timeout=10, headers={"User-Agent": "IncluScan/0.1"})
            response.raise_for_status()
        except requests.RequestException:
            continue

        final_url = _normalize_crawl_url(response.url or current_url).geturl()
        final_key = _crawl_key(base_url, final_url)
        if final_key in seen:
            seen.add(current_key)
            continue

        seen.add(current_key)
        seen.add(final_key)

        content_type = response.headers.get("content-type", "")
        if "pdf" in content_type.lower() or final_url.lower().endswith(".pdf"):
            with NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(response.content)
                temp_pdf = Path(temp_file.name)
            try:
                document = extract_pdf_document(temp_pdf, final_url)
            finally:
                temp_pdf.unlink(missing_ok=True)
        else:
            document = extract_html_document(response.text, final_url)
            if _is_soft_404_document(document):
                continue
            if allow_extended:
                for discovered_url in discover_urls(final_url, response.text):
                    discovered_key = _crawl_key(base_url, discovered_url)
                    if discovered_key not in seen and discovered_key not in queued_keys:
                        queue.append(discovered_url)
                        queued_keys.add(discovered_key)

        document_signature = _document_signature(document)
        if document_signature in seen_documents:
            continue
        seen_documents.add(document_signature)

        pages.append(
            ScrapedPage(
                snapshot_id=snapshot.snapshot_id,
                url=final_url,
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
