import csv
import json
from collections import Counter
from pathlib import Path

import pytest

from hpo_ptbr.data import load_metadata, load_snapshot
from hpo_ptbr.evaluation import load_cases
from hpo_ptbr.protocol import (
    BUCKET_TARGETS,
    ORTHOGRAPHIC_RULES,
    freeze_holdout,
    replace_rejected_concepts,
    select_holdout_concepts,
)

ROOT = Path(__file__).resolve().parents[1]


def test_real_holdout_selection_is_deterministic_and_disjoint():
    records = load_snapshot(ROOT / "data/processed/hpo_ptbr.csv")
    development_cases = load_cases(ROOT / "data/eval/pilot_cases.csv")
    first = select_holdout_concepts(records, development_cases)
    second = select_holdout_concepts(records, development_cases)
    assert first == second
    assert len(first) == 10
    assert Counter(concept.word_bucket for concept in first) == Counter(BUCKET_TARGETS)
    assert tuple(concept.orthographic_rule for concept in first) == ORTHOGRAPHIC_RULES
    development_ids = {case["target_hpo_id"] for case in development_cases}
    assert not development_ids.intersection(concept.record.hpo_id for concept in first)


def test_pending_review_cannot_be_frozen(tmp_path):
    review_path = tmp_path / "pending_review.csv"
    with (ROOT / "data/eval/holdout_review.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0])
    rows[0]["review_status"] = "pending"
    with review_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    records = load_snapshot(ROOT / "data/processed/hpo_ptbr.csv")
    metadata = load_metadata(ROOT / "data/processed/metadata.json")
    with pytest.raises(ValueError, match="aprovados"):
        freeze_holdout(
            review_path=review_path,
            output_path=tmp_path / "holdout.csv",
            manifest_path=tmp_path / "manifest.json",
            records=records,
            development_path=ROOT / "data/eval/pilot_cases.csv",
            data_version=str(metadata["data_version"]),
        )


def test_approved_review_freezes_balanced_holdout(tmp_path):
    review_path = tmp_path / "review.csv"
    with (ROOT / "data/eval/holdout_review.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0])
    for row in rows:
        row["review_status"] = "approved"
    with review_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    records = load_snapshot(ROOT / "data/processed/hpo_ptbr.csv")
    metadata = load_metadata(ROOT / "data/processed/metadata.json")
    output_path = tmp_path / "holdout.csv"
    manifest_path = tmp_path / "manifest.json"
    manifest = freeze_holdout(
        review_path=review_path,
        output_path=output_path,
        manifest_path=manifest_path,
        records=records,
        development_path=ROOT / "data/eval/pilot_cases.csv",
        data_version=str(metadata["data_version"]),
    )
    cases = load_cases(output_path)
    assert len(cases) == 30
    assert Counter(case["stratum"] for case in cases) == {
        "official_label": 10,
        "orthographic_variation": 10,
        "clinical_paraphrase": 10,
    }
    assert manifest["status"] == "frozen"
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["sha256"] == manifest["sha256"]


def test_rejected_concept_gets_deterministic_replacement_and_audit_log(tmp_path):
    review_path = tmp_path / "review.csv"
    original = (ROOT / "data/eval/holdout_review.csv").read_text(encoding="utf-8")
    review_path.write_text(original, encoding="utf-8")
    with review_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0])
    rejected_id = rows[0]["hpo_id"]
    rows[0]["review_status"] = "rejected"
    rows[0]["review_notes"] = "tradução inadequada"
    with review_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    records = load_snapshot(ROOT / "data/processed/hpo_ptbr.csv")
    development_cases = load_cases(ROOT / "data/eval/pilot_cases.csv")
    rejections_path = tmp_path / "rejections.csv"
    assert replace_rejected_concepts(
        review_path,
        rejections_path,
        records,
        development_cases,
    ) == 1
    with review_path.open(encoding="utf-8", newline="") as handle:
        updated = list(csv.DictReader(handle))
    assert updated[0]["hpo_id"] != rejected_id
    assert updated[0]["review_status"] == "pending"
    assert rejected_id in rejections_path.read_text(encoding="utf-8")
