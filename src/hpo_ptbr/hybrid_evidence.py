from __future__ import annotations

from time import perf_counter

from .evidence import EvidenceExtractor, EvidenceSpan, TextMappingResult
from .semantic_evidence import SemanticEvidenceExtractor


class HybridEvidenceExtractor:
    detector_name = "lexical_semantic_union"
    method = "hybrid_evidence"

    def __init__(
        self,
        lexical: EvidenceExtractor,
        semantic: SemanticEvidenceExtractor,
    ) -> None:
        if lexical.mapper.records != semantic.mapper.records:
            raise ValueError("Os detectores devem usar o mesmo snapshot HPO.")
        if lexical.mapper.data_version != semantic.mapper.data_version:
            raise ValueError("Os detectores devem usar a mesma versão de dados.")
        self.lexical = lexical
        self.semantic = semantic
        self.mapper = lexical.mapper

    def map_text(
        self,
        text: str,
        *,
        top_k: int = 5,
        max_spans: int = 10,
    ) -> TextMappingResult:
        started_at = perf_counter()
        lexical_result = self.lexical.map_text(
            text,
            top_k=top_k,
            max_spans=max_spans,
        )
        semantic_result = self.semantic.map_text(
            text,
            top_k=top_k,
            max_spans=max_spans,
        )
        selected = self._merge(lexical_result.spans, semantic_result.spans)[:max_spans]
        return TextMappingResult(
            text=lexical_result.text,
            method=self.method,
            detector=self.detector_name,
            data_version=self.mapper.data_version,
            latency_ms=round((perf_counter() - started_at) * 1000, 3),
            spans=tuple(sorted(selected, key=lambda span: (span.start, span.end))),
        )

    @staticmethod
    def _merge(
        lexical_spans: tuple[EvidenceSpan, ...],
        semantic_spans: tuple[EvidenceSpan, ...],
    ) -> list[EvidenceSpan]:
        by_offsets = {(span.start, span.end): span for span in lexical_spans}
        for span in semantic_spans:
            by_offsets.setdefault((span.start, span.end), span)

        ordered = sorted(
            by_offsets.values(),
            key=lambda span: (
                -(span.end - span.start),
                0 if span.source == "lexical" else 1,
                span.start,
                span.candidates[0].hpo_id if span.candidates else "",
            ),
        )
        selected = []
        for span in ordered:
            overlaps = any(
                span.start < existing.end and existing.start < span.end
                for existing in selected
            )
            if not overlaps:
                selected.append(span)
        return selected
