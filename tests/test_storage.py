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

from pathlib import Path

from incluscan.models import ScrapedPage, SnapshotMetadata
from incluscan.scraper import extract_html_document, extract_pdf_document, should_follow_url, crawl_site
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
