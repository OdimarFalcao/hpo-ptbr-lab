from __future__ import annotations

from .data import HpoRecord
from .rankers import BaseMapper, ExactMapper

RRF_K = 60
SOURCE_TOP_K = 20


class HybridMapper(BaseMapper):
    method = "hybrid"

    def __init__(
        self,
        records: list[HpoRecord],
        data_version: str,
        source_mappers: tuple[BaseMapper, ...],
    ) -> None:
        super().__init__(records, data_version)
        if not source_mappers:
            raise ValueError("Informe ao menos um mapper para a fusão híbrida.")
        if any(mapper.records != records for mapper in source_mappers):
            raise ValueError("Todos os mappers devem usar o mesmo snapshot HPO.")
        if any(mapper.data_version != data_version for mapper in source_mappers):
            raise ValueError("Todos os mappers devem usar a mesma versão de dados.")
        self.exact_mapper = ExactMapper(records, data_version)
        self.source_mappers = source_mappers
        self.records_by_id = {record.hpo_id: record for record in records}

    def _score(self, query: str) -> list[tuple[HpoRecord, float]]:
        exact_matches = self.exact_mapper._score(query)
        if exact_matches:
            return exact_matches

        fused_scores: dict[str, float] = {}
        for mapper in self.source_mappers:
            ranked = mapper._score(query)[:SOURCE_TOP_K]
            for rank, (record, _) in enumerate(ranked, start=1):
                fused_scores[record.hpo_id] = fused_scores.get(record.hpo_id, 0.0) + 1 / (
                    RRF_K + rank
                )

        scored = [
            (self.records_by_id[hpo_id], score)
            for hpo_id, score in fused_scores.items()
        ]
        return self._ordered(scored)
