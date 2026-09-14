import csv
import hashlib

from hpo_ptbr.hashing import content_sha256
import json
from pathlib import Path

from hpo_ptbr.benchmark import validate_benchmark, validate_benchmark_targets
from hpo_ptbr.data import load_snapshot
from hpo_ptbr.evaluation import load_cases

ROOT = Path(__file__).resolve().parents[1]


def _historical_ids():
    historical = {
        case["target_hpo_id"]
        for path in (
            ROOT / "data/eval/pilot_cases.csv",
            ROOT / "data/eval/holdout_cases.csv",
        )
        for case in load_cases(path)
    }
    demo_cases = json.loads(
        (ROOT / "data/demo/synthetic_review_cases.json").read_text(encoding="utf-8")
    )
    historical.update(
        mention["hpo_id"]
        for case in demo_cases
        for mention in case["mentions"]
    )
    return historical


def test_development_dataset_matches_protocol_and_historical_exclusions():
    document = json.loads(
        (ROOT / "data/eval/benchmark_v1_development.json").read_text(encoding="utf-8")
    )
    protocol = json.loads(
        (ROOT / "data/protocol/benchmark_v1_protocol.json").read_text(encoding="utf-8")
    )
    records = load_snapshot(ROOT / "data/processed/hpo_ptbr.csv")
    labels = {record.hpo_id: record.label_pt for record in records}
    summary = validate_benchmark(
        document,
        labels,
        excluded_hpo_ids=_historical_ids(),
        official_labels=labels,
    )
    validate_benchmark_targets(summary, protocol, target_name="development")


def test_development_manifest_hashes_and_review_form_are_consistent():
    dataset_path = ROOT / "data/eval/benchmark_v1_development.json"
    review_path = ROOT / "data/eval/benchmark_v1_development_review.csv"
    manifest = json.loads(
        (ROOT / "data/eval/benchmark_v1_development_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["dataset_sha256"] == content_sha256(dataset_path)
    assert manifest["review_sha256"] == content_sha256(review_path)
    review_log_path = ROOT / manifest["review_log"]
    assert manifest["review_log_sha256"] == content_sha256(review_log_path)
    with review_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 38
    assert all(
        row["review_status"] == "human_confirmed_for_development_evaluation"
        for row in rows
    )
    assert sum(not row["hpo_id"] for row in rows) == 2


def test_technical_review_is_blind_and_records_source_based_decisions():
    review_log = json.loads(
        (ROOT / "data/eval/benchmark_v1_development_review_log.json").read_text(
            encoding="utf-8"
        )
    )
    assert review_log["rankings_consulted"] is False
    assert review_log["methods_executed"] is False
    assert review_log["human_clinical_review"] is False
    assert len(review_log["decisions"]) == 36
    paraphrases = [
        decision
        for decision in review_log["decisions"]
        if decision["surface_form"] == "clinical_paraphrase"
    ]
    assert len(paraphrases) == 12
    assert len(review_log["corrections"]) == 1
    assert review_log["human_confirmation"]["confirmed_by"] == "Odimar"
    assert review_log["human_confirmation"]["holdout_authorized"] is False
