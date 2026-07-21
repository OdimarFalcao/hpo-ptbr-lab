from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hpo_ptbr.data import load_metadata, load_snapshot
from hpo_ptbr.evidence_evaluation import evaluate_evidence_cases
from hpo_ptbr.sapbert import (
    DEFAULT_SAPBERT_MODEL_NAME,
    DEFAULT_SAPBERT_MODEL_REVISION,
    SapBertEncoder,
)
from hpo_ptbr.semantic import (
    DEFAULT_MODEL_NAME,
    DEFAULT_MODEL_REVISION,
    SemanticMapper,
    load_default_encoder,
)
from hpo_ptbr.semantic_evidence import SemanticEvidenceExtractor


def all_mentions_are_targets(cases: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        case
        | {
            "mentions": [
                mention | {"detectable": True}
                for mention in case["mentions"]
            ]
        }
        for case in cases
    ]


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    serialized = [
        row | {"top_hpo_ids": json.dumps(row["top_hpo_ids"], ensure_ascii=False)}
        for row in rows
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(serialized[0]))
        writer.writeheader()
        writer.writerows(serialized)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Avalia detecção semântica de evidências no desenvolvimento."
    )
    parser.add_argument(
        "--encoder",
        choices=("generic", "sapbert"),
        default="sapbert",
    )
    parser.add_argument("--threshold", type=float, default=0.8)
    args = parser.parse_args()

    records = load_snapshot(ROOT / "data/processed/hpo_ptbr.csv")
    metadata = load_metadata(ROOT / "data/processed/metadata.json")
    cases = json.loads(
        (ROOT / "data/demo/synthetic_review_cases.json").read_text(encoding="utf-8")
    )
    if args.encoder == "sapbert":
        encoder = SapBertEncoder(local_files_only=True)
        model_name = DEFAULT_SAPBERT_MODEL_NAME
        model_revision = DEFAULT_SAPBERT_MODEL_REVISION
    else:
        encoder = load_default_encoder(local_files_only=True)
        model_name = DEFAULT_MODEL_NAME
        model_revision = DEFAULT_MODEL_REVISION

    mapper = SemanticMapper(records, str(metadata["data_version"]), encoder)
    extractor = SemanticEvidenceExtractor(
        mapper,
        detection_threshold=args.threshold,
    )
    details, summary = evaluate_evidence_cases(
        extractor,
        all_mentions_are_targets(cases),
    )

    results_dir = ROOT / "data/results"
    prefix = f"semantic_evidence_{args.encoder}"
    write_csv(results_dir / f"{prefix}_details.csv", details)
    (results_dir / f"{prefix}_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    experiment_metadata = {
        "experiment": "semantic-evidence-development-1",
        "generated_at": datetime.now(UTC).isoformat(),
        "data_version": metadata["data_version"],
        "model_name": model_name,
        "model_revision": model_revision,
        "encoder": args.encoder,
        "detection_threshold": args.threshold,
        "max_span_tokens": extractor.max_span_tokens,
        "development_cases": len(cases),
        "target_mentions": sum(len(case["mentions"]) for case in cases),
        "holdout_used": False,
    }
    (results_dir / f"{prefix}_metadata.json").write_text(
        json.dumps(experiment_metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
