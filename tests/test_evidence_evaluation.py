import pytest

from hpo_ptbr.data import HpoRecord
from hpo_ptbr.evidence import EvidenceExtractor
from hpo_ptbr.evidence_evaluation import (
    evaluate_evidence_cases,
    validate_evidence_cases,
)
from hpo_ptbr.rankers import FuzzyMapper


def test_evaluates_detectable_mentions_and_known_miss():
    records = [
        HpoRecord("HP:0000001", "One", "Microcefalia"),
        HpoRecord("HP:0000002", "Two", "Baixa estatura"),
    ]
    cases = [
        {
            "id": "positive",
            "text": "Microcefalia e baixa estatura.",
            "expected_hpo_ids": ["HP:0000001", "HP:0000002"],
            "mentions": [
                {
                    "text": "Microcefalia",
                    "start": 0,
                    "end": 12,
                    "hpo_id": "HP:0000001",
                    "detectable": True,
                },
                {
                    "text": "baixa estatura",
                    "start": 15,
                    "end": 29,
                    "hpo_id": "HP:0000002",
                    "detectable": True,
                },
            ],
        },
        {
            "id": "known-miss",
            "text": "Cabeça menor que o esperado.",
            "expected_hpo_ids": ["HP:0000001"],
            "mentions": [
                {
                    "text": "Cabeça menor que o esperado",
                    "start": 0,
                    "end": 27,
                    "hpo_id": "HP:0000001",
                    "detectable": False,
                }
            ],
        },
    ]
    extractor = EvidenceExtractor(FuzzyMapper(records, "test"))

    details, summary = evaluate_evidence_cases(extractor, cases)

    assert len(details) == 3
    assert summary["exact_span_recall"] == 1.0
    assert summary["predicted_span_precision"] == 1.0
    assert summary["hpo_accuracy_at_1"] == 1.0
    assert summary["known_miss_reproduction_rate"] == 1.0
    assert summary["invalid_id_rate"] == 0.0


def test_rejects_invalid_offsets_and_hpo_ids():
    cases = [
        {
            "id": "invalid",
            "text": "Microcefalia",
            "expected_hpo_ids": ["HP:9999999"],
            "mentions": [
                {
                    "text": "Microcefalia",
                    "start": 1,
                    "end": 12,
                    "hpo_id": "HP:9999999",
                    "detectable": True,
                }
            ],
        }
    ]

    with pytest.raises(ValueError):
        validate_evidence_cases(cases, {"HP:0000001"})
