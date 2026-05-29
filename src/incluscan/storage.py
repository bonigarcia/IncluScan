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


def read_snapshot_metadata(path: Path) -> SnapshotMetadata:
    first_line = path.read_text(encoding="utf-8").splitlines()[0]
    return SnapshotMetadata(**json.loads(first_line))
