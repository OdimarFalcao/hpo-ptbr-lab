from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hpo_ptbr.data import load_metadata, load_snapshot
from hpo_ptbr.protocol import freeze_holdout


def main() -> None:
    records = load_snapshot(ROOT / "data/processed/hpo_ptbr.csv")
    metadata = load_metadata(ROOT / "data/processed/metadata.json")
    manifest = freeze_holdout(
        review_path=ROOT / "data/eval/holdout_review.csv",
        output_path=ROOT / "data/eval/holdout_cases.csv",
        manifest_path=ROOT / "data/eval/holdout_manifest.json",
        records=records,
        development_path=ROOT / "data/eval/pilot_cases.csv",
        data_version=str(metadata["data_version"]),
        rejections_path=ROOT / "data/eval/holdout_rejections.csv",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
