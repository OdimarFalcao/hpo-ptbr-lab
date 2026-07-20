import pytest

from hpo_ptbr.review import build_review_export, highlight_evidence, unmatched_mentions


def test_highlights_evidence_and_escapes_untrusted_text():
    text = "Texto <sintético> com ptose."
    spans = [{"start": 22, "end": 27}]

    highlighted = highlight_evidence(text, spans)

    assert "&lt;sintético&gt;" in highlighted
    assert "<mark>ptose</mark>" in highlighted


def test_lists_gold_mentions_without_exact_span_match():
    case = {
        "mentions": [
            {"text": "ptose", "start": 0, "end": 5},
            {"text": "olhos desalinhados", "start": 8, "end": 26},
        ]
    }

    missed = unmatched_mentions(case, [{"start": 0, "end": 5}])

    assert [mention["text"] for mention in missed] == ["olhos desalinhados"]


def test_review_export_requires_one_decision_per_span():
    analysis = {"text": "ptose", "spans": [{"start": 0, "end": 5}]}

    with pytest.raises(ValueError):
        build_review_export(analysis, [])

    exported = build_review_export(
        analysis,
        [{"selected_hpo_id": "HP:0000508", "review_status": "Pendente"}],
    )
    assert exported["human_review"][0]["selected_hpo_id"] == "HP:0000508"
