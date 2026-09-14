from collections import Counter

import pytest

from hpo_ptbr.benchmark import (
    BenchmarkSummary,
    validate_benchmark,
    validate_benchmark_targets,
)


def _valid_document():
    return {
        "benchmark_version": "test-v1",
        "snapshot": "snapshot-test",
        "cases": [
            {
                "case_id": "DEV-001",
                "split": "development",
                "domain": "neurology",
                "case_type": "phenotype",
                "text": "Há fraqueza nas pernas.",
                "mentions": [
                    {
                        "text": "fraqueza nas pernas",
                        "start": 3,
                        "end": 22,
                        "hpo_id": "HP:0000001",
                        "assertion": "present",
                        "surface_form": "clinical_paraphrase",
                    }
                ],
            },
            {
                "case_id": "HLD-001",
                "split": "holdout",
                "domain": "respiratory",
                "case_type": "negative_control",
                "text": "Texto sintético sem achados fenotípicos.",
                "mentions": [],
            },
        ],
    }


def test_valid_benchmark_preserves_splits_and_context():
    summary = validate_benchmark(_valid_document(), {"HP:0000001"})
    assert summary.case_count == 2
    assert summary.mention_count == 1
    assert summary.negative_control_count == 1
    assert summary.cases_by_split == {"development": 1, "holdout": 1}
    assert summary.assertion_counts == {"present": 1}


def test_benchmark_rejects_offset_mismatch():
    document = _valid_document()
    document["cases"][0]["mentions"][0]["start"] = 4
    with pytest.raises(ValueError, match="offsets divergem"):
        validate_benchmark(document, {"HP:0000001"})


def test_benchmark_rejects_historical_or_repeated_hpo_id():
    with pytest.raises(ValueError, match="avaliação anterior"):
        validate_benchmark(
            _valid_document(),
            {"HP:0000001"},
            excluded_hpo_ids={"HP:0000001"},
        )


def test_benchmark_rejects_mentions_in_negative_control():
    document = _valid_document()
    document["cases"][1]["mentions"] = [
        {
            "text": "sintético",
            "start": 6,
            "end": 15,
            "hpo_id": "HP:0000002",
            "assertion": "absent",
            "surface_form": "official_label",
        }
    ]
    with pytest.raises(ValueError, match="Controle negativo"):
        validate_benchmark(document, {"HP:0000001", "HP:0000002"})


def test_benchmark_rejects_paraphrase_that_repeats_official_label():
    document = _valid_document()
    document["cases"][0]["mentions"][0]["text"] = "fraqueza nas pernas"
    document["cases"][0]["mentions"][0]["label_pt"] = "fraqueza nas pernas"
    with pytest.raises(ValueError, match="Paráfrase repete"):
        validate_benchmark(
            document,
            {"HP:0000001"},
            official_labels={"HP:0000001": "fraqueza nas pernas"},
        )


def test_target_validator_checks_preregistered_distributions():
    summary = BenchmarkSummary(
        case_count=2,
        mention_count=1,
        negative_control_count=1,
        cases_by_split=Counter({"development": 1, "holdout": 1}),
        mentions_by_split=Counter({"development": 1}),
        domains=frozenset({"neurology", "respiratory"}),
        assertion_counts=Counter({"present": 1}),
        surface_form_counts=Counter({"clinical_paraphrase": 1}),
        domain_mention_counts=Counter({"neurology": 1}),
        hpo_ids=frozenset({"HP:0000001"}),
    )
    protocol = {
        "scope": {
            "case_count": 2,
            "mention_count": 1,
            "negative_control_count": 1,
            "splits": {"development": 1, "holdout": 1},
            "mentions_by_split": {"development": 1},
            "minimum_domains": 2,
        },
        "annotation": {
            "assertion_counts": {"present": 1},
            "surface_form_counts": {"clinical_paraphrase": 1},
        },
    }
    validate_benchmark_targets(summary, protocol)

    protocol["scope"]["minimum_domains"] = 3
    with pytest.raises(ValueError, match="Domínios insuficientes"):
        validate_benchmark_targets(summary, protocol)


def test_target_validator_accepts_named_target():
    summary = BenchmarkSummary(
        case_count=2,
        mention_count=1,
        negative_control_count=1,
        cases_by_split=Counter({"development": 2}),
        mentions_by_split=Counter({"development": 1}),
        domains=frozenset({"neurology"}),
        assertion_counts=Counter({"present": 1}),
        surface_form_counts=Counter({"official_label": 1}),
        domain_mention_counts=Counter({"neurology": 1}),
        hpo_ids=frozenset({"HP:0000001"}),
    )
    protocol = {
        "targets": {
            "development": {
                "scope": {
                    "case_count": 2,
                    "mention_count": 1,
                    "negative_control_count": 1,
                    "splits": {"development": 2},
                    "mentions_by_split": {"development": 1},
                    "minimum_domains": 1,
                },
                "annotation": {
                    "assertion_counts": {"present": 1},
                    "surface_form_counts": {"official_label": 1},
                },
            }
        }
    }
    validate_benchmark_targets(summary, protocol, target_name="development")
