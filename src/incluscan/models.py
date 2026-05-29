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
    finding_count: int | None = None
    page_count: int | None = None
    duration_seconds: float | None = None
