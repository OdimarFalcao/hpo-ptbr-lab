from hpo_ptbr.hashing import content_sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_candidate_execution_uses_preregistered_development_only():
    protocol = _load("data/protocol/benchmark_v1_candidate_protocol.json")
    metadata = _load("data/results/benchmark_v1_candidate_metadata.json")

    dataset_hash = content_sha256(ROOT / protocol["dataset"])
    assert dataset_hash == protocol["dataset_sha256"]
    assert metadata["protocol_sha256"] == content_sha256(ROOT / metadata["protocol"])
    assert protocol["holdout_used"] is False
    assert metadata["holdout_used"] is False


def test_candidate_gates_preserve_positive_and_negative_results():
    gates = _load("data/results/benchmark_v1_candidate_gates.json")
    summary = _load("data/results/benchmark_v1_candidate_summary.json")

    assert gates["assertion_candidate"]["passed"] is True
    assert gates["semantic_detection_component"]["passed"] is False
    assert gates["combined_candidate"]["passed"] is False
    assert summary["fuzzy_context_cues"]["assertion_macro_f1"] == 0.9592
    assert summary["semantic_context_cues"]["by_surface_form"][
        "clinical_paraphrase"
    ]["exact_span_recall"] == 0.3333
    assert summary["hybrid_context_cues"][
        "negative_control_false_positive_rate"
    ] == 0.5
    assert all(
        result["invalid_hpo_id_rate"] == 0.0 for result in summary.values()
    )


def test_candidate_error_analysis_identifies_failures_without_adjustment():
    analysis = _load("data/results/benchmark_v1_candidate_error_analysis.json")

    assert analysis["context_errors"] == [
        {
            "case_id": "DEV-RES-01",
            "mention_text": "hipoventilacao",
            "expected": "uncertain",
            "predicted": "present",
        }
    ]
    assert len(analysis["semantic_paraphrases_detected_exactly"]) == 4
    assert analysis["semantic_paraphrases_missed_count"] == 8
    assert {
        (row["case_id"], row["prediction_text"], row["top_hpo_id"])
        for row in analysis["negative_control_predictions"]
    } == {("DEV-CTRL-01", "achados fenotípicos", "HP:0000118")}
