from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Candidate:
    hpo_id: str
    label_pt: str
    label_en: str
    score: float
    rank: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class MappingResult:
    query: str
    method: str
    data_version: str
    latency_ms: float
    candidates: tuple[Candidate, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "query": self.query,
            "method": self.method,
            "data_version": self.data_version,
            "latency_ms": self.latency_ms,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }
