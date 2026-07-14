from __future__ import annotations

from abc import ABC, abstractmethod
from time import perf_counter

from rapidfuzz import fuzz
from rank_bm25 import BM25Okapi

from .data import HpoRecord
from .models import Candidate, MappingResult
from .normalize import normalize_text, tokenize


class BaseMapper(ABC):
    method: str

    def __init__(self, records: list[HpoRecord], data_version: str) -> None:
        if not records:
            raise ValueError("É necessário fornecer ao menos um termo HPO.")
        self.records = records
        self.data_version = data_version
        self.normalized_labels = [normalize_text(record.label_pt) for record in records]

    def map(self, query: str, top_k: int = 5) -> MappingResult:
        cleaned_query = query.strip()
        if not cleaned_query:
            raise ValueError("Informe uma expressão fenotípica.")
        if len(cleaned_query) > 200:
            raise ValueError("Cada expressão deve ter no máximo 200 caracteres.")
        if top_k < 1 or top_k > 20:
            raise ValueError("top_k deve estar entre 1 e 20.")

        started_at = perf_counter()
        scored_records = self._score(cleaned_query)
        candidates = tuple(
            Candidate(
                hpo_id=record.hpo_id,
                label_pt=record.label_pt,
                label_en=record.label_en,
                score=round(float(score), 6),
                rank=index,
            )
            for index, (record, score) in enumerate(scored_records[:top_k], start=1)
        )
        latency_ms = round((perf_counter() - started_at) * 1000, 3)
        return MappingResult(
            query=cleaned_query,
            method=self.method,
            data_version=self.data_version,
            latency_ms=latency_ms,
            candidates=candidates,
        )

    @abstractmethod
    def _score(self, query: str) -> list[tuple[HpoRecord, float]]:
        raise NotImplementedError

    @staticmethod
    def _ordered(items: list[tuple[HpoRecord, float]]) -> list[tuple[HpoRecord, float]]:
        return sorted(items, key=lambda item: (-item[1], item[0].hpo_id))


class ExactMapper(BaseMapper):
    method = "exact"

    def _score(self, query: str) -> list[tuple[HpoRecord, float]]:
        normalized_query = normalize_text(query)
        matches = [
            (record, 1.0)
            for record, normalized_label in zip(self.records, self.normalized_labels, strict=True)
            if normalized_label == normalized_query
        ]
        return self._ordered(matches)


class FuzzyMapper(BaseMapper):
    method = "fuzzy"

    def _score(self, query: str) -> list[tuple[HpoRecord, float]]:
        normalized_query = normalize_text(query)
        scored = [
            (record, fuzz.WRatio(normalized_query, normalized_label) / 100.0)
            for record, normalized_label in zip(self.records, self.normalized_labels, strict=True)
        ]
        return self._ordered(scored)


class Bm25Mapper(BaseMapper):
    method = "bm25"

    def __init__(self, records: list[HpoRecord], data_version: str) -> None:
        super().__init__(records, data_version)
        self.corpus_tokens = [tokenize(label) for label in self.normalized_labels]
        self.index = BM25Okapi(self.corpus_tokens)

    def _score(self, query: str) -> list[tuple[HpoRecord, float]]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        scores = self.index.get_scores(query_tokens)
        scored = [
            (record, float(score))
            for record, score in zip(self.records, scores, strict=True)
            if score > 0
        ]
        return self._ordered(scored)
