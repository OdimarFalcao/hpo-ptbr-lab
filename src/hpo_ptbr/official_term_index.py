from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from time import perf_counter

import numpy as np
from rapidfuzz import fuzz
from rank_bm25 import BM25Okapi

from .normalize import normalize_text, tokenize
from .ontology import OntologyIndex
from .semantic import TextEncoder


@dataclass(frozen=True)
class OfficialTerm:
    hpo_id: str
    text: str
    language: str
    field: str
    scope: str
    source: str
    source_version: str


@dataclass(frozen=True)
class OfficialTermIndex:
    data_version: str
    scope_root: str
    sources: dict[str, dict[str, str]]
    terms: tuple[OfficialTerm, ...]


@dataclass(frozen=True)
class OfficialTermCandidate:
    hpo_id: str
    label_pt: str
    label_pt_status: str
    label_en: str
    score: float
    rank: int
    matched_term: str
    matched_term_language: str
    matched_term_field: str
    matched_term_scope: str
    term_source: str
    term_source_version: str
    human_review_required: bool = True

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class OfficialTermMappingResult:
    query: str
    method: str
    data_version: str
    latency_ms: float
    candidates: tuple[OfficialTermCandidate, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "query": self.query,
            "method": self.method,
            "data_version": self.data_version,
            "latency_ms": self.latency_ms,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }


def build_official_term_index(
    ontology: OntologyIndex,
    metadata: dict[str, object],
) -> OfficialTermIndex:
    if str(metadata.get("data_version", "")) != ontology.data_version:
        raise ValueError("Metadados e índice ontológico usam versões diferentes.")
    sources = metadata.get("sources")
    if not isinstance(sources, dict):
        raise ValueError("Metadados sem fontes terminológicas.")
    hpo_source = sources.get("hpo")
    translation_source = sources.get("hpo_pt")
    if not isinstance(hpo_source, dict) or not isinstance(translation_source, dict):
        raise ValueError("Metadados incompletos para HPO e tradução portuguesa.")

    hpo_release = str(metadata.get("hpo_release", ""))
    translation_commit = str(metadata.get("translation_commit", ""))
    if not hpo_release or not translation_commit:
        raise ValueError("Versões das fontes terminológicas ausentes.")

    terms: list[OfficialTerm] = []
    seen: set[tuple[str, str, str, str]] = set()

    def add(term: OfficialTerm) -> None:
        normalized = normalize_text(term.text)
        key = (term.hpo_id, term.language, term.field, normalized)
        if not normalized or key in seen:
            return
        seen.add(key)
        terms.append(term)

    for hpo_id in sorted(ontology.phenotypic_abnormality_ids):
        concept = ontology.require_phenotypic_abnormality(hpo_id)
        if concept.label_pt:
            add(
                OfficialTerm(
                    hpo_id=hpo_id,
                    text=concept.label_pt,
                    language="pt-BR",
                    field="official_label_pt",
                    scope="label",
                    source="hpo_pt",
                    source_version=translation_commit,
                )
            )
        if concept.label_en:
            add(
                OfficialTerm(
                    hpo_id=hpo_id,
                    text=concept.label_en,
                    language="en",
                    field="official_label_en",
                    scope="label",
                    source="hpo",
                    source_version=hpo_release,
                )
            )
        for synonym in concept.synonyms:
            if synonym.scope != "exact":
                continue
            add(
                OfficialTerm(
                    hpo_id=hpo_id,
                    text=synonym.text,
                    language="en",
                    field="official_exact_synonym_en",
                    scope=synonym.scope,
                    source="hpo",
                    source_version=hpo_release,
                )
            )

    if not terms:
        raise ValueError("Índice oficial sem termos fenotípicos.")
    terms.sort(
        key=lambda term: (
            term.hpo_id,
            term.language,
            term.field,
            normalize_text(term.text),
            term.text,
        )
    )
    return OfficialTermIndex(
        data_version=ontology.data_version,
        scope_root=ontology.root_hpo_id,
        sources={
            "hpo": {
                "url": str(hpo_source.get("url", "")),
                "sha256": str(hpo_source.get("sha256", "")),
                "version": hpo_release,
            },
            "hpo_pt": {
                "url": str(translation_source.get("url", "")),
                "sha256": str(translation_source.get("sha256", "")),
                "version": translation_commit,
            },
        },
        terms=tuple(terms),
    )


class OfficialTermRanker(ABC):
    method: str

    def __init__(self, index: OfficialTermIndex, ontology: OntologyIndex) -> None:
        if index.data_version != ontology.data_version:
            raise ValueError("Ranker e ontologia usam versões diferentes.")
        self.index = index
        self.ontology = ontology
        self.normalized_terms = [normalize_text(term.text) for term in index.terms]

    def map(self, query: str, top_k: int = 5) -> OfficialTermMappingResult:
        cleaned_query = query.strip()
        if not cleaned_query:
            raise ValueError("Informe uma expressão fenotípica.")
        if len(cleaned_query) > 200:
            raise ValueError("Cada expressão deve ter no máximo 200 caracteres.")
        if top_k < 1 or top_k > 20:
            raise ValueError("top_k deve estar entre 1 e 20.")
        started_at = perf_counter()
        candidates = self._aggregate(self._score(cleaned_query), top_k)
        return OfficialTermMappingResult(
            query=cleaned_query,
            method=self.method,
            data_version=self.index.data_version,
            latency_ms=round((perf_counter() - started_at) * 1000, 3),
            candidates=candidates,
        )

    @abstractmethod
    def _score(self, query: str) -> list[tuple[int, float]]:
        raise NotImplementedError

    def _aggregate(
        self,
        scored_terms: list[tuple[int, float]],
        top_k: int,
    ) -> tuple[OfficialTermCandidate, ...]:
        best_by_hpo_id: dict[str, tuple[float, OfficialTerm]] = {}
        for term_index, score in scored_terms:
            term = self.index.terms[term_index]
            previous = best_by_hpo_id.get(term.hpo_id)
            if previous is None or score > previous[0]:
                best_by_hpo_id[term.hpo_id] = (float(score), term)
        ordered = sorted(
            best_by_hpo_id.items(),
            key=lambda item: (-item[1][0], item[0]),
        )[:top_k]
        candidates = []
        for rank, (hpo_id, (score, term)) in enumerate(ordered, start=1):
            concept = self.ontology.require_phenotypic_abnormality(hpo_id)
            candidates.append(
                OfficialTermCandidate(
                    hpo_id=hpo_id,
                    label_pt=concept.label_pt,
                    label_pt_status="official" if concept.label_pt else "unavailable",
                    label_en=concept.label_en,
                    score=round(score, 6),
                    rank=rank,
                    matched_term=term.text,
                    matched_term_language=term.language,
                    matched_term_field=term.field,
                    matched_term_scope=term.scope,
                    term_source=term.source,
                    term_source_version=term.source_version,
                )
            )
        return tuple(candidates)


class OfficialExactRanker(OfficialTermRanker):
    method = "official_terms_exact"

    def _score(self, query: str) -> list[tuple[int, float]]:
        normalized_query = normalize_text(query)
        return [
            (index, 1.0)
            for index, term in enumerate(self.normalized_terms)
            if term == normalized_query
        ]


class OfficialFuzzyRanker(OfficialTermRanker):
    method = "official_terms_fuzzy"

    def _score(self, query: str) -> list[tuple[int, float]]:
        normalized_query = normalize_text(query)
        return [
            (index, fuzz.WRatio(normalized_query, term) / 100.0)
            for index, term in enumerate(self.normalized_terms)
        ]


class OfficialBm25Ranker(OfficialTermRanker):
    method = "official_terms_bm25"

    def __init__(self, index: OfficialTermIndex, ontology: OntologyIndex) -> None:
        super().__init__(index, ontology)
        self.corpus_tokens = [tokenize(term) for term in self.normalized_terms]
        self.bm25 = BM25Okapi(self.corpus_tokens)

    def _score(self, query: str) -> list[tuple[int, float]]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        return [
            (index, float(score))
            for index, score in enumerate(self.bm25.get_scores(query_tokens))
            if score > 0
        ]


class OfficialSemanticRanker(OfficialTermRanker):
    method = "official_terms_sapbert"

    def __init__(
        self,
        index: OfficialTermIndex,
        ontology: OntologyIndex,
        encoder: TextEncoder,
    ) -> None:
        super().__init__(index, ontology)
        self.encoder = encoder
        self.corpus_embeddings = np.asarray(
            encoder.encode_document(
                [term.text for term in index.terms],
                normalize_embeddings=True,
                show_progress_bar=False,
            ),
            dtype=np.float32,
        )
        if self.corpus_embeddings.ndim != 2 or self.corpus_embeddings.shape[0] != len(index.terms):
            raise ValueError("O encoder retornou embeddings inválidos para o índice oficial.")

    def _score(self, query: str) -> list[tuple[int, float]]:
        query_embedding = np.asarray(
            self.encoder.encode_query(
                [query],
                normalize_embeddings=True,
                show_progress_bar=False,
            ),
            dtype=np.float32,
        )
        if query_embedding.shape != (1, self.corpus_embeddings.shape[1]):
            raise ValueError("O encoder retornou embedding inválido para a consulta.")
        scores = query_embedding[0] @ self.corpus_embeddings.T
        return [(index, float(score)) for index, score in enumerate(scores)]
