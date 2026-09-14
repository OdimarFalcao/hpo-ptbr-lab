import hashlib
import json
from pathlib import Path

from hpo_ptbr.ontology import load_ontology_index
from hpo_ptbr.phase2_evaluation import load_phase2_dataset

ROOT = Path(__file__).resolve().parents[1]


def _json(relative_path: str) -> dict[str, object]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def _sha256(relative_path: str) -> str:
    return hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()


def test_phase2_baseline_freeze_still_matches_pipeline_and_snapshot():
    baseline = _json("data/protocol/phase2_baseline_freeze.json")

    for relative_path, expected_hash in baseline["sha256"].items():
        assert _sha256(relative_path) == expected_hash
    assert baseline["repository"]["working_tree_clean"] is False
    assert baseline["interpretation"]["method_changes_in_phase2_run"] is False


def test_phase2_development_results_reference_current_frozen_inputs():
    metadata = _json("data/results/phase2_development_metadata.json")
    summary = _json("data/results/phase2_development_summary.json")

    assert metadata["dataset_sha256"] == _sha256(metadata["dataset"])
    assert metadata["protocol_sha256"] == _sha256(metadata["protocol"])
    assert metadata["baseline_sha256"] == _sha256(metadata["baseline"])
    assert metadata["validation_used"] is False
    assert metadata["holdout_used"] is False
    assert summary["status"] == "development_exploratory_not_clinically_validated"
    assert summary["errors_by_category"]["paraphrase_failure"] == 9
    assert summary["review"]["human_elapsed_seconds"] is None


def test_real_phase2_dataset_uses_valid_snapshot_concepts_and_nonliteral_mentions():
    ontology = load_ontology_index(ROOT / "data/processed/hpo_ontology.json.gz")

    dataset = load_phase2_dataset(
        ROOT / "data/eval/phase2_development.json",
        ontology,
        expected_split="development",
    )

    assert len(dataset["cases"]) == 11
    assert sum(len(case["annotations"]) for case in dataset["cases"]) == 9


def test_future_splits_are_reserved_without_exposed_content():
    registry = _json("data/eval/phase2_split_registry.json")

    assert registry["validation"]["status"] == "reserved_not_authored"
    assert registry["validation"]["texts"] == []
    assert registry["holdout"]["status"] == "sealed_not_authored"
    assert registry["holdout"]["texts"] == []
