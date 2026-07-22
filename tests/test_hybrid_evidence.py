from hpo_ptbr.evidence import EvidenceSpan
from hpo_ptbr.hybrid_evidence import HybridEvidenceExtractor
from hpo_ptbr.models import Candidate


def _candidate(hpo_id: str, label: str) -> tuple[Candidate, ...]:
    return (Candidate(hpo_id, label, label, 1.0, 1),)


def _span(
    text: str,
    start: int,
    end: int,
    hpo_id: str,
    source: str,
) -> EvidenceSpan:
    return EvidenceSpan(
        text=text,
        start=start,
        end=end,
        detector_score=1.0,
        candidates=_candidate(hpo_id, text),
        source=source,
    )


def test_hybrid_union_preserves_lexical_and_adds_semantic_span() -> None:
    lexical = (_span("nistagmo", 0, 8, "HP:0000639", "lexical"),)
    semantic = (
        _span("perda de audição de um lado", 11, 38, "HP:0009900", "semantic"),
    )

    merged = HybridEvidenceExtractor._merge(lexical, semantic)

    assert {(span.text, span.source) for span in merged} == {
        ("nistagmo", "lexical"),
        ("perda de audição de um lado", "semantic"),
    }


def test_hybrid_union_prefers_lexical_for_duplicate_offsets() -> None:
    lexical = (_span("ptose", 4, 9, "HP:0000508", "lexical"),)
    semantic = (_span("ptose", 4, 9, "HP:9999999", "semantic"),)

    merged = HybridEvidenceExtractor._merge(lexical, semantic)

    assert len(merged) == 1
    assert merged[0].source == "lexical"
    assert merged[0].candidates[0].hpo_id == "HP:0000508"


def test_hybrid_union_prefers_longer_overlapping_span() -> None:
    lexical = (_span("tosse", 0, 5, "HP:0012735", "lexical"),)
    semantic = (_span("tosse persistente", 0, 17, "HP:0034315", "semantic"),)

    merged = HybridEvidenceExtractor._merge(lexical, semantic)

    assert [span.text for span in merged] == ["tosse persistente"]
    assert merged[0].source == "semantic"
