from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

import numpy as np

from .evidence import EvidenceSpan, TOKEN_PATTERN, TextMappingResult
from .models import Candidate
from .semantic import SemanticMapper


@dataclass(frozen=True)
class _SemanticWindow:
    text: str
    start: int
    end: int
    token_count: int
    score: float
    hpo_id: str
    row_index: int


class SemanticEvidenceExtractor:
    detector_name = "semantic_windows"

    def __init__(
        self,
        mapper: SemanticMapper,
        *,
        max_span_tokens: int = 6,
        detection_threshold: float = 0.8,
    ) -> None:
        if max_span_tokens < 1 or max_span_tokens > 8:
            raise ValueError("max_span_tokens deve estar entre 1 e 8.")
        if detection_threshold <= 0 or detection_threshold > 1:
            raise ValueError("detection_threshold deve estar entre 0 e 1.")
        self.mapper = mapper
        self.max_span_tokens = max_span_tokens
        self.detection_threshold = detection_threshold

    def map_text(
        self,
        text: str,
        *,
        top_k: int = 5,
        max_spans: int = 10,
    ) -> TextMappingResult:
        cleaned_text = text.strip()
        if not cleaned_text:
            raise ValueError("Informe uma descrição sintética.")
        if len(cleaned_text) > 1000:
            raise ValueError("A descrição deve ter no máximo 1000 caracteres.")
        if top_k < 1 or top_k > 10:
            raise ValueError("top_k deve estar entre 1 e 10.")
        if max_spans < 1 or max_spans > 20:
            raise ValueError("max_spans deve estar entre 1 e 20.")

        started_at = perf_counter()
        windows = self._windows(cleaned_text)
        if not windows:
            return TextMappingResult(
                text=cleaned_text,
                method=self.mapper.method,
                detector=self.detector_name,
                data_version=self.mapper.data_version,
                latency_ms=round((perf_counter() - started_at) * 1000, 3),
                spans=(),
            )

        embeddings = np.asarray(
            self.mapper.encoder.encode_query(
                [window[0] for window in windows],
                normalize_embeddings=True,
                show_progress_bar=False,
            ),
            dtype=np.float32,
        )
        expected_shape = (len(windows), self.mapper.corpus_embeddings.shape[1])
        if embeddings.shape != expected_shape:
            raise ValueError("O encoder retornou embeddings inválidos para os trechos.")
        scores = self.mapper.score_embeddings(embeddings)
        detected = self._score_windows(windows, scores)
        selected = self._remove_overlaps(detected)[:max_spans]
        spans = tuple(
            EvidenceSpan(
                text=window.text,
                start=window.start,
                end=window.end,
                detector_score=round(window.score, 6),
                candidates=self._candidates(scores[window.row_index], top_k),
                source="semantic",
            )
            for window in sorted(selected, key=lambda item: (item.start, item.end))
        )
        return TextMappingResult(
            text=cleaned_text,
            method=self.mapper.method,
            detector=self.detector_name,
            data_version=self.mapper.data_version,
            latency_ms=round((perf_counter() - started_at) * 1000, 3),
            spans=spans,
        )

    def _windows(self, text: str) -> list[tuple[str, int, int, int]]:
        tokens = list(TOKEN_PATTERN.finditer(text))
        windows = []
        for start_index, start_token in enumerate(tokens):
            maximum = min(len(tokens), start_index + self.max_span_tokens)
            for end_index in range(start_index, maximum):
                end_token = tokens[end_index]
                span_text = text[start_token.start() : end_token.end()]
                if len(span_text) >= 3:
                    windows.append(
                        (
                            span_text,
                            start_token.start(),
                            end_token.end(),
                            end_index - start_index + 1,
                        )
                    )
        return windows

    def _score_windows(
        self,
        windows: list[tuple[str, int, int, int]],
        scores: np.ndarray,
    ) -> list[_SemanticWindow]:
        hpo_ids = np.asarray([record.hpo_id for record in self.mapper.records])
        detected = []
        for row_index, (text, start, end, token_count) in enumerate(windows):
            order = np.lexsort((hpo_ids, -scores[row_index]))
            record_index = int(order[0])
            score = float(scores[row_index, record_index])
            if score < self.detection_threshold:
                continue
            record = self.mapper.records[record_index]
            detected.append(
                _SemanticWindow(
                    text=text,
                    start=start,
                    end=end,
                    token_count=token_count,
                    score=score,
                    hpo_id=record.hpo_id,
                    row_index=row_index,
                )
            )
        return detected

    def _candidates(self, scores: np.ndarray, top_k: int) -> tuple[Candidate, ...]:
        hpo_ids = np.asarray([record.hpo_id for record in self.mapper.records])
        order = np.lexsort((hpo_ids, -scores))[:top_k]
        return tuple(
            Candidate(
                hpo_id=self.mapper.records[int(record_index)].hpo_id,
                label_pt=self.mapper.records[int(record_index)].label_pt,
                label_en=self.mapper.records[int(record_index)].label_en,
                score=round(float(scores[int(record_index)]), 6),
                rank=rank,
            )
            for rank, record_index in enumerate(order, start=1)
        )

    @staticmethod
    def _remove_overlaps(
        windows: list[_SemanticWindow],
    ) -> list[_SemanticWindow]:
        ordered = sorted(
            windows,
            key=lambda window: (
                -window.score,
                -window.token_count,
                window.start,
                window.hpo_id,
            ),
        )
        selected = []
        for window in ordered:
            overlaps = any(
                window.start < existing.end and existing.start < window.end
                for existing in selected
            )
            if not overlaps:
                selected.append(window)
        return selected
