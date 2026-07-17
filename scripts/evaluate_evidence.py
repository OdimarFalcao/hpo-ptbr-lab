from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hpo_ptbr.data import load_metadata, load_snapshot
from hpo_ptbr.evidence import EvidenceExtractor
from hpo_ptbr.evidence_evaluation import evaluate_evidence_cases
from hpo_ptbr.rankers import FuzzyMapper


def main() -> None:
    records = load_snapshot(ROOT / "data/processed/hpo_ptbr.csv")
    metadata = load_metadata(ROOT / "data/processed/metadata.json")
    cases = json.loads(
        (ROOT / "data/demo/synthetic_descriptions.json").read_text(encoding="utf-8")
    )
    extractor = EvidenceExtractor(
        FuzzyMapper(records, str(metadata["data_version"]))
    )
    details, summary = evaluate_evidence_cases(extractor, cases)
    results_dir = ROOT / "data/results"
    results_dir.mkdir(parents=True, exist_ok=True)

    csv_rows = [
        row | {"top_hpo_ids": json.dumps(row["top_hpo_ids"], ensure_ascii=False)}
        for row in details
    ]
    with (results_dir / "evidence_evaluation_details.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)
    (results_dir / "evidence_evaluation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
