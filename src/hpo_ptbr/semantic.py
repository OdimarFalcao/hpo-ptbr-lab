from __future__ import annotations

from typing import Protocol

import numpy as np

from .data import HpoRecord
from .rankers import BaseMapper

DEFAULT_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_MODEL_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"


class TextEncoder(Protocol):
    def encode_document(
        self,
        sentences: list[str],
        *,
        normalize_embeddings: bool,
        show_progress_bar: bool,
    ) -> np.ndarray: ...

    def encode_query(
        self,
        sentences: list[str],
        *,
        normalize_embeddings: bool,
        show_progress_bar: bool,
    ) -> np.ndarray: ...


class SemanticMapper(BaseMapper):
    method = "semantic"

    def __init__(
        self,
        records: list[HpoRecord],
        data_version: str,
        encoder: TextEncoder,
    ) -> None:
        super().__init__(records, data_version)
        self.encoder = encoder
        self.corpus_embeddings = self._encode_documents([record.label_pt for record in records])

    def _encode_documents(self, labels: list[str]) -> np.ndarray:
        embeddings = np.asarray(
            self.encoder.encode_document(
                labels,
                normalize_embeddings=True,
                show_progress_bar=False,
            ),
            dtype=np.float32,
        )
        if embeddings.ndim != 2 or embeddings.shape[0] != len(labels):
            raise ValueError("O encoder retornou embeddings inválidos para o snapshot HPO.")
        return embeddings

    def _score(self, query: str) -> list[tuple[HpoRecord, float]]:
        query_embeddings = np.asarray(
            self.encoder.encode_query(
                [query],
                normalize_embeddings=True,
                show_progress_bar=False,
            ),
            dtype=np.float32,
        )
        if query_embeddings.shape != (1, self.corpus_embeddings.shape[1]):
            raise ValueError("O encoder retornou um embedding inválido para a consulta.")
        scores = self.score_embeddings(query_embeddings)[0]
        scored = [
            (record, float(score))
            for record, score in zip(self.records, scores, strict=True)
        ]
        return self._ordered(scored)

    def score_embeddings(self, query_embeddings: np.ndarray) -> np.ndarray:
        return query_embeddings @ self.corpus_embeddings.T


class BilingualSemanticMapper(SemanticMapper):
    method = "semantic_bilingual"

    def __init__(
        self,
        records: list[HpoRecord],
        data_version: str,
        encoder: TextEncoder,
    ) -> None:
        BaseMapper.__init__(self, records, data_version)
        self.encoder = encoder
        self.corpus_embeddings = self._encode_documents(
            [record.label_pt for record in records]
        )
        self.english_embeddings = self._encode_documents(
            [record.label_en for record in records]
        )

    def score_embeddings(self, query_embeddings: np.ndarray) -> np.ndarray:
        portuguese_scores = query_embeddings @ self.corpus_embeddings.T
        english_scores = query_embeddings @ self.english_embeddings.T
        return np.maximum(portuguese_scores, english_scores)


def load_default_encoder(*, local_files_only: bool = True) -> TextEncoder:
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(
        DEFAULT_MODEL_NAME,
        revision=DEFAULT_MODEL_REVISION,
        local_files_only=local_files_only,
    )
