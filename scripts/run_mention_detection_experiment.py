from __future__ import annotations

import csv
import hashlib
import json
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from huggingface_hub import snapshot_download

from hpo_ptbr.mention_evaluation import evaluate_mention_predictions
from hpo_ptbr.mention_ner import (
    DEFAULT_MENTION_MODEL_NAME,
    DEFAULT_MENTION_MODEL_REVISION,
    MODEL_ALLOW_PATTERNS,
    TransformerMentionDetector,
    model_file_manifest,
)


def normalized_text_sha256(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def write_predictions(
    path: Path,
    rows: list[dict[str, object]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "text",
                "start",
                "end",
                "label",
                "score",
                "matches_gold_offsets",
                "target_hpo_id",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    protocol_path = ROOT / "data/protocol/mention_detection_protocol.json"
    cases_path = ROOT / "data/demo/synthetic_review_cases.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    candidate = protocol["candidate_model"]
    if (
        candidate["name"] != DEFAULT_MENTION_MODEL_NAME
        or candidate["revision"] != DEFAULT_MENTION_MODEL_REVISION
    ):
        raise ValueError("O candidato executado diverge do protocolo congelado.")
    if protocol["scope"]["holdout_used"] or protocol["execution"]["holdout_execution"]:
        raise ValueError("O protocolo de menções não permite uso do holdout.")

    snapshot_path = snapshot_download(
        repo_id=DEFAULT_MENTION_MODEL_NAME,
        revision=DEFAULT_MENTION_MODEL_REVISION,
        allow_patterns=list(MODEL_ALLOW_PATTERNS),
        local_files_only=True,
    )
    current_files = model_file_manifest(snapshot_path)
    manifest_path = ROOT / "data/results/mention_detection_model_manifest.json"
    expected_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if current_files != expected_manifest["files"]:
        raise ValueError("Os arquivos locais do modelo divergem do manifesto.")

    detector = TransformerMentionDetector(local_files_only=True)
    predictions = []
    latencies = []
    prediction_rows = []
    for case in cases:
        case_id = str(case["id"])
        text = str(case["text"])
        case_predictions, latency_ms = detector.predict(case_id, text)
        predictions.extend(case_predictions)
        latencies.append(latency_ms)
        gold_by_offsets = {
            (int(mention["start"]), int(mention["end"])): mention
            for mention in case["mentions"]
        }
        for prediction in case_predictions:
            gold = gold_by_offsets.get((prediction.start, prediction.end))
            prediction_rows.append(
                {
                    "case_id": case_id,
                    "text": prediction.text,
                    "start": prediction.start,
                    "end": prediction.end,
                    "label": prediction.label,
                    "score": prediction.score,
                    "matches_gold_offsets": gold is not None,
                    "target_hpo_id": gold["hpo_id"] if gold else "",
                }
            )

    summary = evaluate_mention_predictions(cases, predictions)
    summary["latency_mean_ms"] = round(statistics.fmean(latencies), 3)
    summary["latency_median_ms"] = round(statistics.median(latencies), 3)
    gate = protocol["decision_gate"]
    summary["decision_gate_passed"] = (
        summary["exact_span_recall"] >= gate["exact_span_recall_min"]
        and summary["exact_span_precision"] >= gate["exact_span_precision_min"]
        and summary["critical_paraphrase_recall"]
        >= gate["critical_paraphrase_recall_min"]
        and summary["invalid_predictions"] <= gate["invalid_predictions_max"]
    )

    results_dir = ROOT / "data/results"
    write_predictions(
        results_dir / "mention_detection_ner_predictions.csv",
        prediction_rows,
    )
    (results_dir / "mention_detection_ner_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    metadata = {
        "experiment": "mention-detection-development-1",
        "generated_at": datetime.now(UTC).isoformat(),
        "protocol_version": protocol["protocol_version"],
        "protocol_sha256": normalized_text_sha256(protocol_path),
        "dataset": protocol["scope"]["dataset"],
        "development_cases": len(cases),
        "gold_mentions": sum(len(case["mentions"]) for case in cases),
        "model_name": DEFAULT_MENTION_MODEL_NAME,
        "model_revision": DEFAULT_MENTION_MODEL_REVISION,
        "model_files": current_files,
        "accepted_entity_groups": candidate["accepted_entity_groups"],
        "decoding": candidate["decoding"],
        "confidence_threshold": candidate["confidence_threshold"],
        "holdout_used": False,
    }
    (results_dir / "mention_detection_ner_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
