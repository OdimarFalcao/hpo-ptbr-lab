import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_development_results_follow_preregistered_dataset_and_exclude_holdout():
    protocol = _load_json("data/protocol/benchmark_v1_development_baseline.json")
    metadata = _load_json("data/results/benchmark_v1_development_metadata.json")
    dataset_bytes = (ROOT / metadata["dataset"]).read_bytes()

    assert hashlib.sha256(dataset_bytes).hexdigest() == protocol["dataset_sha256"]
    assert metadata["holdout_used"] is False
    assert metadata["methods"] == ["exact", "fuzzy", "bm25"]


def test_development_results_preserve_key_scientific_findings():
    summary = _load_json("data/results/benchmark_v1_development_summary.json")
    errors = _load_json(
        "data/results/benchmark_v1_development_error_analysis.json"
    )

    for method in summary.values():
        assert method["invalid_hpo_id_rate"] == 0.0
        assert method["negative_control_false_positive_rate"] == 0.0
        assert method["by_surface_form"]["clinical_paraphrase"][
            "exact_span_recall"
        ] == 0.0

    fuzzy_surface = summary["fuzzy"]["by_surface_form"]
    assert fuzzy_surface["official_label"]["linking_accuracy_at_1"] == 1.0
    assert fuzzy_surface["orthographic_variation"]["linking_accuracy_at_1"] == 1.0
    assert fuzzy_surface["clinical_paraphrase"]["linking_accuracy_at_1"] == 0.0
    assert summary["bm25"]["by_surface_form"]["clinical_paraphrase"][
        "linking_accuracy_at_5"
    ] == 0.3333
    assert errors["fuzzy"]["missed_exact_spans_by_surface"] == {
        "clinical_paraphrase": 12,
        "orthographic_variation": 1,
    }
    assert errors["fuzzy"]["assertion_errors_by_gold_class"] == {
        "absent": 4,
        "family_history": 4,
        "uncertain": 4,
    }
