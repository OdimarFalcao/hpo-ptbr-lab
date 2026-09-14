from __future__ import annotations

import gzip
import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HpoSynonym:
    text: str
    scope: str
    audience: str


@dataclass(frozen=True)
class HpoConcept:
    hpo_id: str
    label_en: str
    label_pt: str
    definition_en: str
    definition_pt: str
    definition_sources: tuple[str, ...]
    synonyms: tuple[HpoSynonym, ...]
    parent_ids: tuple[str, ...]
    child_ids: tuple[str, ...]


class OntologyIndex:
    def __init__(
        self,
        concepts: dict[str, HpoConcept],
        data_version: str,
        root_hpo_id: str = "HP:0000118",
    ) -> None:
        if root_hpo_id not in concepts:
            raise ValueError(f"Raiz HPO ausente no índice: {root_hpo_id}")
        self.concepts = concepts
        self.data_version = data_version
        self.root_hpo_id = root_hpo_id

    def get(self, hpo_id: str) -> HpoConcept | None:
        return self.concepts.get(hpo_id)

    def require(self, hpo_id: str) -> HpoConcept:
        concept = self.get(hpo_id)
        if concept is None:
            raise ValueError(f"HPO ID inexistente no snapshot: {hpo_id}")
        return concept

    def path_to_root(self, hpo_id: str) -> tuple[str, ...]:
        self.require(hpo_id)
        if hpo_id == self.root_hpo_id:
            return (hpo_id,)

        queue: deque[tuple[str, tuple[str, ...]]] = deque([(hpo_id, (hpo_id,))])
        visited = {hpo_id}
        while queue:
            current_id, path = queue.popleft()
            current = self.concepts[current_id]
            for parent_id in sorted(current.parent_ids):
                if parent_id == self.root_hpo_id:
                    return path + (parent_id,)
                if parent_id in self.concepts and parent_id not in visited:
                    visited.add(parent_id)
                    queue.append((parent_id, path + (parent_id,)))
        return ()


def load_ontology_index(path: str | Path) -> OntologyIndex:
    with gzip.open(Path(path), mode="rt", encoding="utf-8") as handle:
        payload = json.load(handle)

    raw_concepts = payload.get("concepts", [])
    if not isinstance(raw_concepts, list) or not raw_concepts:
        raise ValueError("Índice ontológico sem conceitos HPO.")

    children: dict[str, list[str]] = {}
    for raw in raw_concepts:
        hpo_id = str(raw["hpo_id"])
        for parent_id in raw.get("parent_ids", []):
            children.setdefault(str(parent_id), []).append(hpo_id)

    concepts = {}
    for raw in raw_concepts:
        hpo_id = str(raw["hpo_id"])
        concepts[hpo_id] = HpoConcept(
            hpo_id=hpo_id,
            label_en=str(raw.get("label_en", "")),
            label_pt=str(raw.get("label_pt", "")),
            definition_en=str(raw.get("definition_en", "")),
            definition_pt=str(raw.get("definition_pt", "")),
            definition_sources=tuple(raw.get("definition_sources", [])),
            synonyms=tuple(
                HpoSynonym(
                    text=str(synonym["text"]),
                    scope=str(synonym["scope"]),
                    audience=str(synonym["audience"]),
                )
                for synonym in raw.get("synonyms", [])
            ),
            parent_ids=tuple(sorted(raw.get("parent_ids", []))),
            child_ids=tuple(sorted(children.get(hpo_id, []))),
        )

    unknown_relations = sorted(
        {
            related_id
            for concept in concepts.values()
            for related_id in (*concept.parent_ids, *concept.child_ids)
            if related_id not in concepts
        }
    )
    if unknown_relations:
        raise ValueError(
            f"Relações apontam para conceitos ausentes: {unknown_relations[:5]}"
        )

    return OntologyIndex(
        concepts=concepts,
        data_version=str(payload["data_version"]),
        root_hpo_id=str(payload.get("root_hpo_id", "HP:0000118")),
    )
