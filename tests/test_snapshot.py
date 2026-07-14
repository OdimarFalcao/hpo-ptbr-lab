import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_snapshot_ids_and_pilot_targets_are_consistent():
    with (ROOT / "data/processed/hpo_ptbr.csv").open(encoding="utf-8", newline="") as handle:
        snapshot_ids = {row["hpo_id"] for row in csv.DictReader(handle) if row["label_pt"]}
    with (ROOT / "data/eval/pilot_cases.csv").open(encoding="utf-8", newline="") as handle:
        cases = list(csv.DictReader(handle))
    assert len(cases) == 30
    assert all(case["target_hpo_id"] in snapshot_ids for case in cases)


def test_metadata_has_reproducibility_fields():
    metadata = json.loads((ROOT / "data/processed/metadata.json").read_text(encoding="utf-8"))
    assert metadata["hpo_release"] != "unknown"
    assert len(metadata["translation_commit"]) == 40
    assert len(metadata["sources"]["hpo"]["sha256"]) == 64
    assert len(metadata["sources"]["hpo_pt"]["sha256"]) == 64
