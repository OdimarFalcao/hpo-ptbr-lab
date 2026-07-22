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
from hpo_ptbr.evidence import EvidenceExtractor
from hpo_ptbr.hybrid_evidence import HybridEvidenceExtractor
from hpo_ptbr.rankers import FuzzyMapper
from hpo_ptbr.sapbert import (
    DEFAULT_SAPBERT_MODEL_NAME,
    DEFAULT_SAPBERT_MODEL_REVISION,
    DEFAULT_SAPBERT_MODEL_SHA256,
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


def write_details_csv(path: Path, rows: list[dict[str, object]]) -> None:
    serialized = [
        row | {"top_hpo_ids": json.dumps(row["top_hpo_ids"], ensure_ascii=False)}
        for row in rows
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(serialized[0]))
        writer.writeheader()
        writer.writerows(serialized)


def prediction_rows(
    extractor: SemanticEvidenceExtractor,
    cases: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows = []
    for case in cases:
        gold_by_offsets = {
            (int(mention["start"]), int(mention["end"])): mention
            for mention in case["mentions"]
        }
        result = extractor.map_text(str(case["text"]))
        for span in result.spans:
            gold = gold_by_offsets.get((span.start, span.end))
            top_candidate = span.candidates[0] if span.candidates else None
            rows.append(
                {
                    "case_id": case["id"],
                    "span_text": span.text,
                    "start": span.start,
                    "end": span.end,
                    "detector_score": span.detector_score,
                    "top_hpo_id": top_candidate.hpo_id if top_candidate else "",
                    "top_label_pt": top_candidate.label_pt if top_candidate else "",
                    "matches_gold_offsets": gold is not None,
                    "target_hpo_id": gold["hpo_id"] if gold else "",
                    "top_candidate_is_target": bool(
                        gold
                        and top_candidate
                        and top_candidate.hpo_id == gold["hpo_id"]
                    ),
                }
            )
    return rows


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Avalia detecção semântica de evidências no desenvolvimento."
    )
    parser.add_argument(
        "--encoder",
        choices=("generic", "sapbert", "hybrid-sapbert"),
        default="sapbert",
    )
    parser.add_argument("--threshold", type=float, default=0.8)
    args = parser.parse_args()

    records = load_snapshot(ROOT / "data/processed/hpo_ptbr.csv")
    metadata = load_metadata(ROOT / "data/processed/metadata.json")
    cases = json.loads(
        (ROOT / "data/demo/synthetic_review_cases.json").read_text(encoding="utf-8")
    )
    if args.encoder in {"sapbert", "hybrid-sapbert"}:
        encoder = SapBertEncoder(local_files_only=True)
        model_name = DEFAULT_SAPBERT_MODEL_NAME
        model_revision = DEFAULT_SAPBERT_MODEL_REVISION
    else:
        encoder = load_default_encoder(local_files_only=True)
        model_name = DEFAULT_MODEL_NAME
        model_revision = DEFAULT_MODEL_REVISION

    mapper = SemanticMapper(records, str(metadata["data_version"]), encoder)
    semantic_extractor = SemanticEvidenceExtractor(
        mapper,
        detection_threshold=args.threshold,
    )
    if args.encoder == "hybrid-sapbert":
        extractor = HybridEvidenceExtractor(
            EvidenceExtractor(
                FuzzyMapper(records, str(metadata["data_version"]))
            ),
            semantic_extractor,
        )
    else:
        extractor = semantic_extractor
    details, summary = evaluate_evidence_cases(
        extractor,
        all_mentions_are_targets(cases),
    )

    results_dir = ROOT / "data/results"
    prefix = f"semantic_evidence_{args.encoder.replace('-', '_')}"
    write_details_csv(results_dir / f"{prefix}_details.csv", details)
    write_rows(
        results_dir / f"{prefix}_predictions.csv",
        prediction_rows(extractor, cases),
    )
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
        "model_sha256": (
            DEFAULT_SAPBERT_MODEL_SHA256
            if args.encoder in {"sapbert", "hybrid-sapbert"}
            else None
        ),
        "encoder": args.encoder,
        "detection_threshold": args.threshold,
        "max_span_tokens": semantic_extractor.max_span_tokens,
        "detector": extractor.detector_name,
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
