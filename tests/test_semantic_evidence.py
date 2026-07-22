from __future__ import annotations

import numpy as np
import pytest

from hpo_ptbr.data import HpoRecord
from hpo_ptbr.semantic import BilingualSemanticMapper, SemanticMapper
from hpo_ptbr.semantic_evidence import SemanticEvidenceExtractor


class FakeEncoder:
    vectors = {
        "Ptose": [1.0, 0.0, 0.0],
        "Tosse crônica": [0.0, 1.0, 0.0],
        "Glaucoma": [0.0, 0.0, 1.0],
        "pálpebra caída": [1.0, 0.0, 0.0],
        "tosse persistente": [0.0, 1.0, 0.0],
    }

    def encode_document(
        self,
        sentences: list[str],
        *,
        normalize_embeddings: bool,
        show_progress_bar: bool,
    ) -> np.ndarray:
        return self._encode(sentences)

    def encode_query(
        self,
        sentences: list[str],
        *,
        normalize_embeddings: bool,
        show_progress_bar: bool,
    ) -> np.ndarray:
        return self._encode(sentences)

    def _encode(self, sentences: list[str]) -> np.ndarray:
        return np.asarray(
            [self.vectors.get(sentence, [0.0, 0.0, 0.0]) for sentence in sentences],
            dtype=np.float32,
        )


def _extractor() -> SemanticEvidenceExtractor:
    records = [
        HpoRecord("HP:0000508", "Ptosis", "Ptose"),
        HpoRecord("HP:0034315", "Chronic cough", "Tosse crônica"),
        HpoRecord("HP:0000501", "Glaucoma", "Glaucoma"),
    ]
    mapper = SemanticMapper(records, "test-version", FakeEncoder())
    return SemanticEvidenceExtractor(
        mapper,
        max_span_tokens=3,
        detection_threshold=0.9,
    )


def test_semantic_evidence_finds_paraphrases_with_offsets() -> None:
    result = _extractor().map_text(
        "Paciente com pálpebra caída e tosse persistente.", top_k=2
    )

    assert result.detector == "semantic_windows"
    assert [span.text for span in result.spans] == [
        "pálpebra caída",
        "tosse persistente",
    ]
    assert [(span.start, span.end) for span in result.spans] == [(13, 27), (30, 47)]
    assert [span.candidates[0].hpo_id for span in result.spans] == [
        "HP:0000508",
        "HP:0034315",
    ]


def test_semantic_evidence_returns_no_span_below_threshold() -> None:
    result = _extractor().map_text("Paciente sem achados relevantes.")

    assert result.spans == ()


def test_semantic_evidence_validates_configuration() -> None:
    mapper = _extractor().mapper

    with pytest.raises(ValueError, match="max_span_tokens"):
        SemanticEvidenceExtractor(mapper, max_span_tokens=0)
    with pytest.raises(ValueError, match="detection_threshold"):
        SemanticEvidenceExtractor(mapper, detection_threshold=0.0)


def test_semantic_evidence_breaks_candidate_ties_by_hpo_id() -> None:
    records = [
        HpoRecord("HP:0000002", "Second", "Ptose"),
        HpoRecord("HP:0000001", "First", "Ptose"),
    ]
    mapper = SemanticMapper(records, "test-version", FakeEncoder())
    extractor = SemanticEvidenceExtractor(mapper, detection_threshold=0.9)

    result = extractor.map_text("pálpebra caída", top_k=2)

    assert [candidate.hpo_id for candidate in result.spans[0].candidates] == [
        "HP:0000001",
        "HP:0000002",
    ]


class BilingualFakeEncoder(FakeEncoder):
    vectors = FakeEncoder.vectors | {
        "Ptosis": [0.0, 1.0, 0.0],
        "pálpebra caída": [0.0, 1.0, 0.0],
        "Tosse crônica": [0.0, 0.0, 1.0],
        "Chronic cough": [0.0, 0.0, 1.0],
    }


def test_bilingual_mapper_uses_best_portuguese_or_english_label() -> None:
    records = [
        HpoRecord("HP:0000508", "Ptosis", "Ptose"),
        HpoRecord("HP:0034315", "Chronic cough", "Tosse crônica"),
    ]
    mapper = BilingualSemanticMapper(
        records,
        "test-version",
        BilingualFakeEncoder(),
    )

    result = mapper.map("pálpebra caída", top_k=1)

    assert result.method == "semantic_bilingual"
    assert result.candidates[0].hpo_id == "HP:0000508"
