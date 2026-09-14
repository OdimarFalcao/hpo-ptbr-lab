from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data/eval/benchmark_v1_development.json"
REVIEW_PATH = ROOT / "data/eval/benchmark_v1_development_review.csv"
REVIEW_LOG_PATH = ROOT / "data/eval/benchmark_v1_development_review_log.json"
MANIFEST_PATH = ROOT / "data/eval/benchmark_v1_development_manifest.json"

CONFIRMED_STATUS = "human_confirmed_for_development_evaluation"
EXPECTED_TECHNICAL_STATUS = "technical_review_complete_pending_human_confirmation"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    document = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    review_log = json.loads(REVIEW_LOG_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if document["status"] not in {EXPECTED_TECHNICAL_STATUS, CONFIRMED_STATUS}:
        raise ValueError(f"Estado inesperado do dataset: {document['status']}")
    if review_log["status"] not in {EXPECTED_TECHNICAL_STATUS, CONFIRMED_STATUS}:
        raise ValueError(f"Estado inesperado da revisão: {review_log['status']}")

    document["status"] = CONFIRMED_STATUS
    for case in document["cases"]:
        for mention in case["mentions"]:
            mention["review_status"] = CONFIRMED_STATUS
    DATASET_PATH.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with REVIEW_PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0])
    for row in rows:
        row["review_status"] = CONFIRMED_STATUS
    with REVIEW_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    review_log["status"] = CONFIRMED_STATUS
    review_log["human_confirmation"] = {
        "confirmed_by": "Odimar",
        "confirmed_at": "2026-08-24",
        "confirmation_text": "confirmo o desenvolvimento V1",
        "scope": "linguistic confirmation and authorization for development-only evaluation",
        "clinical_validation": False,
        "holdout_authorized": False,
    }
    REVIEW_LOG_PATH.write_text(
        json.dumps(review_log, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    manifest.update(
        {
            "status": CONFIRMED_STATUS,
            "dataset_sha256": _sha256(DATASET_PATH),
            "review_sha256": _sha256(REVIEW_PATH),
            "review_log_sha256": _sha256(REVIEW_LOG_PATH),
            "human_confirmation_pending": False,
            "human_confirmed_by": "Odimar",
            "human_confirmed_at": "2026-08-24",
            "development_evaluation_authorized": True,
            "holdout_evaluation_authorized": False,
        }
    )
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
