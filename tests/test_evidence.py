import csv
import json
from pathlib import Path

import pytest

from hpo_ptbr.data import HpoRecord, load_snapshot
from hpo_ptbr.evidence import EvidenceExtractor
from hpo_ptbr.rankers import FuzzyMapper


@pytest.fixture
def records():
    return [
        HpoRecord("HP:0000252", "Microcephaly", "Microcefalia"),
        HpoRecord("HP:0000822", "Hypertension", "Hipertensão"),
        HpoRecord("HP:0004322", "Short stature", "Baixa estatura"),
    ]


def test_extracts_non_overlapping_evidence_with_offsets(records):
    mapper = FuzzyMapper(records, "test")
    extractor = EvidenceExtractor(mapper)

    result = extractor.map_text(
        "Descrição sintética com microcefalia e baixa estatura.", top_k=2
    )

    assert [span.text for span in result.spans] == ["microcefalia", "baixa estatura"]
    assert [span.candidates[0].hpo_id for span in result.spans] == [
        "HP:0000252",
        "HP:0004322",
    ]
    assert all(result.text[span.start : span.end] == span.text for span in result.spans)


def test_recovers_orthographic_variation_and_removes_nested_span(records):
    mapper = FuzzyMapper(records, "test")
    extractor = EvidenceExtractor(mapper, detection_threshold=0.9)

    result = extractor.map_text("Há micro cefalia no texto.")

    assert len(result.spans) == 1
    assert result.spans[0].text == "micro cefalia"
    assert result.spans[0].candidates[0].hpo_id == "HP:0000252"


def test_detector_breaks_equal_score_ties_by_hpo_id():
    records = [
        HpoRecord("HP:0000002", "Second", "Termo igual"),
        HpoRecord("HP:0000001", "First", "Termo igual"),
    ]
    extractor = EvidenceExtractor(FuzzyMapper(records, "test"))

    result = extractor.map_text("Termo igual")

    assert result.spans[0].candidates[0].hpo_id == "HP:0000001"


def test_export_is_repeatable_ignoring_latency(records):
    extractor = EvidenceExtractor(FuzzyMapper(records, "test"))

    first = extractor.map_text("Hipertensão.").to_dict()
    second = extractor.map_text("Hipertensão.").to_dict()
    first.pop("latency_ms")
    second.pop("latency_ms")

    assert first == second
    assert first["detector"] == "fuzzy_windows"
    assert first["spans"][0]["detector_score"] == 1.0


def test_rejects_realistic_but_unsupported_input_sizes(records):
    extractor = EvidenceExtractor(FuzzyMapper(records, "test"))

    with pytest.raises(ValueError):
        extractor.map_text(" ")
    with pytest.raises(ValueError):
        extractor.map_text("x" * 1001)


def test_demo_cases_reference_only_valid_snapshot_ids():
    root = Path(__file__).resolve().parents[1]
    valid_ids = {
        record.hpo_id for record in load_snapshot(root / "data/processed/hpo_ptbr.csv")
    }
    cases = json.loads(
        (root / "data/demo/synthetic_review_cases.json").read_text(encoding="utf-8")
    )

    with (root / "data/eval/holdout_cases.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        holdout_ids = {
            row["target_hpo_id"] for row in csv.DictReader(handle)
        }

    assert len(cases) == 10
    assert all(case["expected_hpo_ids"] for case in cases)
    assert all(
        case["expected_hpo_ids"]
        == [mention["hpo_id"] for mention in case["mentions"]]
        for case in cases
    )
    assert all(
        case["text"][mention["start"] : mention["end"]] == mention["text"]
        for case in cases
        for mention in case["mentions"]
    )
    assert all(
        hpo_id in valid_ids
        for case in cases
        for hpo_id in case["expected_hpo_ids"]
    )
    assert not (
        holdout_ids
        & {
            hpo_id
            for case in cases
            for hpo_id in case["expected_hpo_ids"]
        }
    )
