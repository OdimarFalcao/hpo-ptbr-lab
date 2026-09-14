from hpo_ptbr.benchmark_evaluation import evaluate_benchmark_method
from hpo_ptbr.data import HpoRecord
from hpo_ptbr.evidence import EvidenceExtractor
from hpo_ptbr.rankers import FuzzyMapper


def test_evaluates_detection_linking_assertion_and_end_to_end_separately():
    records = [
        HpoRecord("HP:0000001", "Paresthesia", "Parestesia"),
        HpoRecord("HP:0000002", "Focal dystonia", "Distonia focal"),
    ]
    text = "O registro menciona Parestesia. O registro nega Distonia focal."
    cases = [
        {
            "case_id": "DEV-001",
            "split": "development",
            "domain": "neurology",
            "case_type": "phenotype",
            "text": text,
            "mentions": [
                {
                    "text": "Parestesia",
                    "start": text.index("Parestesia"),
                    "end": text.index("Parestesia") + len("Parestesia"),
                    "hpo_id": "HP:0000001",
                    "surface_form": "official_label",
                    "assertion": "present",
                },
                {
                    "text": "Distonia focal",
                    "start": text.index("Distonia focal"),
                    "end": text.index("Distonia focal") + len("Distonia focal"),
                    "hpo_id": "HP:0000002",
                    "surface_form": "official_label",
                    "assertion": "absent",
                },
            ],
        },
        {
            "case_id": "DEV-CTRL",
            "split": "development",
            "domain": "general",
            "case_type": "negative_control",
            "text": "Registro sintético sem achados.",
            "mentions": [],
        },
    ]
    extractor = EvidenceExtractor(FuzzyMapper(records, "test"))

    gold_details, predictions, summary = evaluate_benchmark_method(extractor, cases)

    assert len(gold_details) == 2
    assert len(predictions) == 2
    assert summary["exact_span_f1"] == 1.0
    assert summary["linking_accuracy_at_1"] == 1.0
    assert summary["assertion_accuracy"] == 0.5
    assert summary["assertion_macro_f1"] == 0.1667
    assert summary["end_to_end_exact_f1"] == 0.5
    assert summary["negative_control_false_positive_rate"] == 0.0
    assert summary["invalid_hpo_id_rate"] == 0.0
