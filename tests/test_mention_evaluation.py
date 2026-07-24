from __future__ import annotations

import csv
import json
from pathlib import Path

from hpo_ptbr.mention_detection import (
    TokenPrediction,
    decode_bioes_mentions,
)
from hpo_ptbr.mention_evaluation import (
    MentionPrediction,
    evaluate_mention_predictions,
)
from hpo_ptbr.mention_ner import (
    DEFAULT_MENTION_MODEL_NAME,
    DEFAULT_MENTION_MODEL_REVISION,
)

ROOT = Path(__file__).resolve().parents[1]


def _cases() -> list[dict[str, object]]:
    return [
        {
            "id": "case-1",
            "text": "Paciente com pálpebra caída e tosse.",
            "mentions": [
                {
                    "text": "pálpebra caída",
                    "start": 13,
                    "end": 27,
                    "detectable": False,
                },
                {
                    "text": "tosse",
                    "start": 30,
                    "end": 35,
                    "detectable": True,
                },
            ],
        }
    ]


def test_mention_evaluation_separates_exact_and_relaxed_matches() -> None:
    predictions = [
        MentionPrediction(
            case_id="case-1",
            text="com pálpebra caída",
            start=9,
            end=27,
            label="PROBLEM",
        ),
        MentionPrediction(
            case_id="case-1",
            text="tosse",
            start=30,
            end=35,
            label="PROBLEM",
        ),
    ]

    summary = evaluate_mention_predictions(_cases(), predictions)

    assert summary["exact_span_precision"] == 0.5
    assert summary["exact_span_recall"] == 0.5
    assert summary["exact_span_f1"] == 0.5
    assert summary["relaxed_span_f1_iou_0_5"] == 1.0
    assert summary["critical_paraphrase_recall"] == 0.0


def test_mention_evaluation_counts_invalid_and_unsupported_predictions() -> None:
    predictions = [
        MentionPrediction("case-1", "tosse", 30, 35, "PROBLEM"),
        MentionPrediction("case-1", "Paciente", 0, 8, "TREATMENT"),
        MentionPrediction("case-1", "texto divergente", 0, 8, "PROBLEM"),
    ]

    summary = evaluate_mention_predictions(_cases(), predictions)

    assert summary["n_predictions"] == 3
    assert summary["n_valid_predictions"] == 1
    assert summary["unsupported_predictions"] == 1
    assert summary["invalid_predictions"] == 1
    assert summary["invalid_prediction_rate"] == 0.3333


def test_mention_detection_protocol_is_frozen_on_development() -> None:
    protocol = json.loads(
        (
            ROOT / "data/protocol/mention_detection_protocol.json"
        ).read_text(encoding="utf-8")
    )
    cases = json.loads(
        (
            ROOT / "data/demo/synthetic_review_cases.json"
        ).read_text(encoding="utf-8")
    )

    assert protocol["status"] == "preregistered"
    assert protocol["scope"]["dataset"] == (
        "data/demo/synthetic_review_cases.json"
    )
    assert protocol["scope"]["development_cases"] == len(cases) == 10
    assert protocol["scope"]["gold_mentions"] == sum(
        len(case["mentions"]) for case in cases
    ) == 30
    assert protocol["scope"]["critical_paraphrases"] == sum(
        mention["detectable"] is False
        for case in cases
        for mention in case["mentions"]
    ) == 5
    assert protocol["scope"]["holdout_used"] is False
    assert protocol["execution"]["holdout_execution"] is False
    assert len(protocol["candidate_model"]["revision"]) == 40
    assert protocol["candidate_model"]["accepted_entity_groups"] == ["PROBLEM"]
    assert protocol["candidate_model"]["name"] == DEFAULT_MENTION_MODEL_NAME
    assert (
        protocol["candidate_model"]["revision"]
        == DEFAULT_MENTION_MODEL_REVISION
    )


def test_bioes_decoder_preserves_offsets_and_ignores_other_groups() -> None:
    text = "Ptose e tosse crônica após exame."
    tokens = [
        TokenPrediction(0, 5, "S-PROBLEM", 0.9),
        TokenPrediction(6, 7, "O", 0.99),
        TokenPrediction(8, 13, "B-PROBLEM", 0.8),
        TokenPrediction(14, 21, "E-PROBLEM", 0.6),
        TokenPrediction(22, 26, "O", 0.95),
        TokenPrediction(27, 32, "S-TEST", 0.98),
    ]

    mentions = decode_bioes_mentions("case-1", text, tokens)

    assert [
        (mention.text, mention.start, mention.end, mention.label, mention.score)
        for mention in mentions
    ] == [
        ("Ptose", 0, 5, "PROBLEM", 0.9),
        ("tosse crônica", 8, 21, "PROBLEM", 0.7),
    ]


def test_bioes_decoder_repairs_inside_tag_without_begin() -> None:
    text = "Tosse persistente."
    tokens = [
        TokenPrediction(0, 5, "I-PROBLEM", 0.8),
        TokenPrediction(6, 17, "E-PROBLEM", 0.6),
    ]

    mentions = decode_bioes_mentions("case-1", text, tokens)

    assert len(mentions) == 1
    assert mentions[0].text == "Tosse persistente"
    assert mentions[0].score == 0.7


def test_versioned_mention_experiment_failed_without_holdout() -> None:
    summary = json.loads(
        (
            ROOT / "data/results/mention_detection_ner_summary.json"
        ).read_text(encoding="utf-8")
    )
    metadata = json.loads(
        (
            ROOT / "data/results/mention_detection_ner_metadata.json"
        ).read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (
            ROOT / "data/results/mention_detection_model_manifest.json"
        ).read_text(encoding="utf-8")
    )
    with (
        ROOT / "data/results/mention_detection_ner_predictions.csv"
    ).open(encoding="utf-8", newline="") as handle:
        predictions = list(csv.DictReader(handle))

    assert summary["n_predictions"] == len(predictions) == 112
    assert summary["exact_span_f1"] == 0.0
    assert summary["critical_paraphrase_recall"] == 0.0
    assert summary["decision_gate_passed"] is False
    assert metadata["holdout_used"] is False
    assert metadata["model_revision"] == DEFAULT_MENTION_MODEL_REVISION
    assert manifest["model_revision"] == DEFAULT_MENTION_MODEL_REVISION
    model_weights = next(
        file for file in manifest["files"] if file["path"] == "model.safetensors"
    )
    assert len(model_weights["sha256"]) == 64
    assert not any(file["path"].endswith(".bin") for file in manifest["files"])
