from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HpoRecord:
    hpo_id: str
    label_en: str
    label_pt: str
    definition_pt: str = ""


def load_snapshot(path: str | Path) -> list[HpoRecord]:
    snapshot_path = Path(path)
    with snapshot_path.open(encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle)
        records = [
            HpoRecord(
                hpo_id=row["hpo_id"],
                label_en=row["label_en"],
                label_pt=row["label_pt"],
                definition_pt=row.get("definition_pt", ""),
            )
            for row in rows
            if row.get("label_pt", "").strip()
        ]
    if not records:
        raise ValueError(f"Snapshot sem rótulos em português: {snapshot_path}")
    return records


def load_metadata(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
