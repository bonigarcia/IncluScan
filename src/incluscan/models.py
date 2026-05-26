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
