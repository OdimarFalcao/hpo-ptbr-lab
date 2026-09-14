import json
from pathlib import Path

from hpo_ptbr.mention_ner import decode_word_group_mentions

ROOT = Path(__file__).resolve().parents[1]


def _probabilities(*groups):
    mapping = {
        "O": [1.0, 0.0, 0.0],
        "PROBLEM": [0.0, 0.5, 0.5],
        "TEST": [0.0, 0.0, 1.0],
    }
    return [mapping[group] for group in groups]


def test_aggregates_subwords_and_adjacent_problem_words():
    text = "fraqueza muscular"
    mentions = decode_word_group_mentions(
        "case",
        text,
        offsets=[(0, 3), (3, 8), (9, 17)],
        word_ids=[0, 0, 1],
        probabilities=_probabilities("PROBLEM", "PROBLEM", "PROBLEM"),
        id2label={0: "O", 1: "B-PROBLEM", 2: "E-PROBLEM"},
    )

    assert [(mention.text, mention.start, mention.end) for mention in mentions] == [
        ("fraqueza muscular", 0, 17)
    ]


def test_does_not_join_across_punctuation_and_discards_punctuation_token():
    text = "ptose, nistagmo"
    mentions = decode_word_group_mentions(
        "case",
        text,
        offsets=[(0, 5), (5, 6), (7, 15)],
        word_ids=[0, 1, 2],
        probabilities=_probabilities("PROBLEM", "PROBLEM", "PROBLEM"),
        id2label={0: "O", 1: "B-PROBLEM", 2: "E-PROBLEM"},
    )

    assert [mention.text for mention in mentions] == ["ptose", "nistagmo"]


def test_protocol_is_development_only_and_discloses_prior_dry_run():
    protocol = json.loads(
        (
            ROOT
            / "data/protocol/mention_detection_word_aggregation_protocol.json"
        ).read_text(encoding="utf-8")
    )

    assert protocol["status"] == "specified_after_exploratory_dry_run"
    assert protocol["scope"]["holdout_used"] is False
    assert protocol["execution"]["holdout_execution"] is False
    assert protocol["decision_gate"]["dashboard_promotion"] is False


def test_versioned_word_aggregation_result_failed_gate():
    summary = json.loads(
        (
            ROOT
            / "data/results/mention_detection_word_aggregation_summary.json"
        ).read_text(encoding="utf-8")
    )
    metadata = json.loads(
        (
            ROOT
            / "data/results/mention_detection_word_aggregation_metadata.json"
        ).read_text(encoding="utf-8")
    )

    assert summary["exact_span_f1"] == 0.6557
    assert summary["critical_paraphrase_recall"] == 0.4
    assert summary["invalid_predictions"] == 0
    assert summary["decision_gate_passed"] is False
    assert metadata["holdout_used"] is False
