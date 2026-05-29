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

from incluscan.config import REPORT_DIR, RUN_DIR, SNAPSHOT_DIR
from incluscan.models import ReviewFinding, ScanRunSummary, ScrapedPage, SnapshotMetadata


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
