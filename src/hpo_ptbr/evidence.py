from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from time import perf_counter

from .models import Candidate
from .rankers import BaseMapper, FuzzyMapper

TOKEN_PATTERN = re.compile(r"\b\w+(?:[-']\w+)*\b", re.UNICODE)


@dataclass(frozen=True)
class EvidenceSpan:
    text: str
    start: int
    end: int
    detector_score: float
    candidates: tuple[Candidate, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "detector_score": self.detector_score,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }


@dataclass(frozen=True)
class TextMappingResult:
    text: str
    method: str
    detector: str
    data_version: str
    latency_ms: float
    spans: tuple[EvidenceSpan, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self) | {
            "spans": [span.to_dict() for span in self.spans],
        }


@dataclass(frozen=True)
class _DetectedSpan:
    text: str
    start: int
    end: int
    token_count: int
    score: float
    hpo_id: str


class EvidenceExtractor:
    detector_name = "fuzzy_windows"

    def __init__(
        self,
        mapper: BaseMapper,
        *,
        detector: FuzzyMapper | None = None,
        max_span_tokens: int = 5,
        detection_threshold: float = 0.92,
    ) -> None:
        if max_span_tokens < 1 or max_span_tokens > 8:
            raise ValueError("max_span_tokens deve estar entre 1 e 8.")
        if detection_threshold <= 0 or detection_threshold > 1:
            raise ValueError("detection_threshold deve estar entre 0 e 1.")

        self.mapper = mapper
        self.detector = detector or FuzzyMapper(mapper.records, mapper.data_version)
        if self.detector.records != mapper.records:
            raise ValueError("Detector e mapper devem usar o mesmo snapshot HPO.")
        if self.detector.data_version != mapper.data_version:
            raise ValueError("Detector e mapper devem usar a mesma versão de dados.")
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
        detected = self._detect(cleaned_text)
        selected = self._remove_overlaps(detected)[:max_spans]
        spans = tuple(
            EvidenceSpan(
                text=span.text,
                start=span.start,
                end=span.end,
                detector_score=round(span.score, 6),
                candidates=self.mapper.map(span.text, top_k=top_k).candidates,
            )
            for span in sorted(selected, key=lambda item: (item.start, item.end))
        )
        latency_ms = round((perf_counter() - started_at) * 1000, 3)
        return TextMappingResult(
            text=cleaned_text,
            method=self.mapper.method,
            detector=self.detector_name,
            data_version=self.mapper.data_version,
            latency_ms=latency_ms,
            spans=spans,
        )

    def _detect(self, text: str) -> list[_DetectedSpan]:
        tokens = list(TOKEN_PATTERN.finditer(text))
        detected: list[_DetectedSpan] = []
        for start_index, start_token in enumerate(tokens):
            maximum = min(len(tokens), start_index + self.max_span_tokens)
            for end_index in range(start_index, maximum):
                end_token = tokens[end_index]
                span_text = text[start_token.start() : end_token.end()]
                if len(span_text) < 3:
                    continue
                result = self.detector.map(span_text, top_k=1)
                if not result.candidates:
                    continue
                candidate = result.candidates[0]
                if candidate.score < self.detection_threshold:
                    continue
                detected.append(
                    _DetectedSpan(
                        text=span_text,
                        start=start_token.start(),
                        end=end_token.end(),
                        token_count=end_index - start_index + 1,
                        score=candidate.score,
                        hpo_id=candidate.hpo_id,
                    )
                )
        return detected

    @staticmethod
    def _remove_overlaps(spans: list[_DetectedSpan]) -> list[_DetectedSpan]:
        ordered = sorted(
            spans,
            key=lambda span: (
                -span.score,
                -span.token_count,
                span.start,
                span.hpo_id,
            ),
        )
        selected: list[_DetectedSpan] = []
        for span in ordered:
            overlaps = any(
                span.start < existing.end and existing.start < span.end
                for existing in selected
            )
            if not overlaps:
                selected.append(span)
        return selected
