import hashlib

from hpo_ptbr.hashing import content_sha256
import json
from pathlib import Path

from hpo_ptbr.ontology import load_ontology_index
from hpo_ptbr.phase2_evaluation import load_phase2_dataset

ROOT = Path(__file__).resolve().parents[1]


def _json(relative_path: str) -> dict[str, object]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def _sha256(relative_path: str) -> str:
    return content_sha256(ROOT / relative_path)


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


def test_iteration2_offline_index_has_traceable_full_phenotype_scope():
    manifest = _json("data/results/phase2_iteration2_term_index_manifest.json")
    metadata = _json("data/processed/metadata.json")

    assert manifest["phenotype_concepts"] == 19119
    assert manifest["concepts_with_official_label_pt"] == 6980
    assert manifest["concepts_without_official_label_pt"] == 12139
    assert manifest["terms"] == 49218
    assert manifest["scope_root_included"] is False
    assert manifest["official_dataset_modified"] is False
    assert manifest["sources"]["hpo"]["sha256"] == metadata["sources"]["hpo"]["sha256"]
    assert manifest["sources"]["hpo_pt"]["version"] == metadata["translation_commit"]


def test_iteration2_result_rejects_integration_and_does_not_use_future_splits():
    summary = _json("data/results/phase2_iteration2_offline_summary.json")
    details = _json("data/results/phase2_iteration2_offline_details.json")
    errors = _json("data/results/phase2_iteration2_offline_error_analysis.json")
    sapbert = next(
        method
        for method in summary["methods"]
        if method["method"] == "official_terms_sapbert"
    )

    assert summary["protocol_sha256"] == _sha256(summary["protocol"])
    assert summary["dataset_sha256"] == _sha256(summary["dataset"])
    assert summary["validation_used"] is False
    assert summary["holdout_used"] is False
    assert summary["decision"]["status"] == "do_not_integrate"
    assert summary["decision"]["application_changed"] is False
    assert sapbert["overall"]["targets_retrieved_at_5"] == 1
    assert sapbert["by_label_pt_status"]["unavailable"]["targets_retrieved_at_5"] == 0
    assert errors["counts"]["target_not_retrieved_at_5"] == 8
    assert errors["counts"]["portuguese_coverage_unresolved"] == 4
    assert errors["clinical_adjudication"] is False
    assert all(
        candidate["human_review_required"] is True
        for row in details
        for candidate in row["candidates"]
    )
    assert all(
        candidate["label_pt"] == ""
        for row in details
        for candidate in row["candidates"]
        if candidate["label_pt_status"] == "unavailable"
    )
