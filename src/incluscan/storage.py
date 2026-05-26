from dataclasses import asdict
import json
from pathlib import Path

from incluscan.models import ScrapedPage, SnapshotMetadata


def write_snapshot(root: Path, snapshot: SnapshotMetadata, pages: list[ScrapedPage]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{snapshot.snapshot_id}.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(snapshot), ensure_ascii=False) + "\n")
        for page in pages:
            handle.write(json.dumps(asdict(page), ensure_ascii=False) + "\n")
    return path


def read_snapshot(path: Path) -> tuple[SnapshotMetadata, list[ScrapedPage]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    snapshot = SnapshotMetadata(**json.loads(lines[0]))
    pages = [ScrapedPage(**json.loads(line)) for line in lines[1:]]
    return snapshot, pages
