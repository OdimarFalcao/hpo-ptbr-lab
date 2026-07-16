from __future__ import annotations

import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hpo_ptbr.data import load_metadata, load_snapshot
from hpo_ptbr.evaluation import evaluate_cases, load_cases
from hpo_ptbr.semantic import (
    DEFAULT_MODEL_NAME,
    DEFAULT_MODEL_REVISION,
    SemanticMapper,
    load_default_encoder,
)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    records = load_snapshot(ROOT / "data/processed/hpo_ptbr.csv")
    metadata = load_metadata(ROOT / "data/processed/metadata.json")
    version = str(metadata["data_version"])
    cases = load_cases(ROOT / "data/eval/pilot_cases.csv")
    mapper = SemanticMapper(records, version, load_default_encoder())
    details, summary = evaluate_cases({"semantic": mapper}, cases)

    results_dir = ROOT / "data/results"
    write_csv(results_dir / "semantic_evaluation_details.csv", details)
    write_csv(results_dir / "semantic_evaluation_summary.csv", summary)
    (results_dir / "semantic_evaluation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    experiment_metadata = {
        "experiment": "semantic-baseline-1",
        "generated_at": datetime.now(UTC).isoformat(),
        "data_version": version,
        "model_name": DEFAULT_MODEL_NAME,
        "model_revision": DEFAULT_MODEL_REVISION,
        "corpus_field": "label_pt",
        "corpus_terms": len(records),
        "pilot_cases": len(cases),
    }
    (results_dir / "semantic_experiment_metadata.json").write_text(
        json.dumps(experiment_metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
