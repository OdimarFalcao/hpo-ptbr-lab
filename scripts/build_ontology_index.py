from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hpo_ptbr.data import load_metadata

HPO_ID_PATTERN = re.compile(r"HP_(\d+)$")
SCOPE_NAMES = {
    "hasExactSynonym": "exact",
    "hasRelatedSynonym": "related",
    "hasBroadSynonym": "broad",
    "hasNarrowSynonym": "narrow",
}


def hpo_id_from_iri(iri: str) -> str | None:
    match = HPO_ID_PATTERN.search(iri)
    return f"HP:{match.group(1)}" if match else None


def normalized_space(value: object) -> str:
    return " ".join(str(value or "").split())


def synonym_audience(synonym_type: str) -> str:
    return "layperson" if synonym_type.endswith("#layperson") else "clinical"


def build_index(
    hp_json_path: str | Path,
    translations_path: str | Path,
    metadata_path: str | Path,
) -> dict[str, object]:
    metadata = load_metadata(metadata_path)
    translations = {}
    import csv

    with Path(translations_path).open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            translations[row["hpo_id"]] = row

    payload = json.loads(Path(hp_json_path).read_text(encoding="utf-8"))
    graph = payload["graphs"][0]
    active_ids = {
        hpo_id
        for node in graph.get("nodes", [])
        if node.get("type") == "CLASS" and not node.get("meta", {}).get("deprecated")
        if (hpo_id := hpo_id_from_iri(str(node.get("id", ""))))
    }
    parents: dict[str, set[str]] = {hpo_id: set() for hpo_id in active_ids}
    for edge in graph.get("edges", []):
        if edge.get("pred") != "is_a":
            continue
        child_id = hpo_id_from_iri(str(edge.get("sub", "")))
        parent_id = hpo_id_from_iri(str(edge.get("obj", "")))
        if child_id in active_ids and parent_id in active_ids:
            parents[child_id].add(parent_id)

    concepts = []
    for node in graph.get("nodes", []):
        if node.get("type") != "CLASS" or node.get("meta", {}).get("deprecated"):
            continue
        hpo_id = hpo_id_from_iri(str(node.get("id", "")))
        if not hpo_id:
            continue
        meta = node.get("meta", {})
        definition = meta.get("definition", {})
        translated = translations.get(hpo_id, {})
        synonyms = []
        seen_synonyms = set()
        for synonym in meta.get("synonyms", []):
            text = normalized_space(synonym.get("val"))
            scope = SCOPE_NAMES.get(str(synonym.get("pred", "")))
            key = (text.casefold(), scope)
            if not text or scope is None or key in seen_synonyms:
                continue
            seen_synonyms.add(key)
            synonyms.append(
                {
                    "text": text,
                    "scope": scope,
                    "audience": synonym_audience(str(synonym.get("synonymType", ""))),
                }
            )
        synonyms.sort(key=lambda item: (item["text"].casefold(), item["scope"]))
        sources = sorted(
            {
                str(source)
                for source in definition.get("xrefs", [])
                if str(source).startswith("PMID:")
            }
        )
        concepts.append(
            {
                "hpo_id": hpo_id,
                "label_en": normalized_space(node.get("lbl")),
                "label_pt": normalized_space(translated.get("label_pt")),
                "definition_en": normalized_space(definition.get("val")),
                "definition_pt": normalized_space(translated.get("definition_pt")),
                "definition_sources": sources,
                "synonyms": synonyms,
                "parent_ids": sorted(parents[hpo_id]),
            }
        )
    concepts.sort(key=lambda item: item["hpo_id"])
    return {
        "data_version": metadata["data_version"],
        "root_hpo_id": "HP:0000118",
        "concepts": concepts,
    }


def write_index(path: str | Path, payload: dict[str, object]) -> None:
    serialized = (
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    Path(path).write_bytes(gzip.compress(serialized, compresslevel=9, mtime=0))


def main() -> None:
    payload = build_index(
        ROOT / "data/raw/hp.json",
        ROOT / "data/processed/hpo_ptbr.csv",
        ROOT / "data/processed/metadata.json",
    )
    output_path = ROOT / "data/processed/hpo_ontology.json.gz"
    write_index(output_path, payload)
    print(
        json.dumps(
            {
                "output": output_path.relative_to(ROOT).as_posix(),
                "concepts": len(payload["concepts"]),
                "size_bytes": output_path.stat().st_size,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
