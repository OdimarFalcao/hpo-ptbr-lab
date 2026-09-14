import gzip
import json
from pathlib import Path

from hpo_ptbr.ontology import load_ontology_index

ROOT = Path(__file__).resolve().parents[1]


def _write_index(path):
    payload = {
        "data_version": "test",
        "root_hpo_id": "HP:0000118",
        "concepts": [
            {
                "hpo_id": "HP:0000118",
                "label_en": "Phenotypic abnormality",
                "label_pt": "Anormalidade fenotípica",
                "definition_en": "",
                "definition_pt": "",
                "definition_sources": [],
                "synonyms": [],
                "parent_ids": [],
            },
            {
                "hpo_id": "HP:0000508",
                "label_en": "Ptosis",
                "label_pt": "Ptose",
                "definition_en": "Drooping upper eyelid.",
                "definition_pt": "",
                "definition_sources": ["PMID:1"],
                "synonyms": [
                    {"text": "Drooping eyelid", "scope": "exact", "audience": "layperson"}
                ],
                "parent_ids": ["HP:0000118"],
            },
        ],
    }
    path.write_bytes(
        gzip.compress(json.dumps(payload).encode("utf-8"), mtime=0)
    )


def test_loads_relations_and_deterministic_path(tmp_path):
    path = tmp_path / "ontology.json.gz"
    _write_index(path)

    index = load_ontology_index(path)
    ptosis = index.require("HP:0000508")

    assert ptosis.parent_ids == ("HP:0000118",)
    assert index.require("HP:0000118").child_ids == ("HP:0000508",)
    assert index.path_to_root("HP:0000508") == ("HP:0000508", "HP:0000118")
    assert ptosis.synonyms[0].audience == "layperson"


def test_rejects_unknown_hpo_id(tmp_path):
    path = tmp_path / "ontology.json.gz"
    _write_index(path)
    index = load_ontology_index(path)

    try:
        index.require("HP:9999999")
    except ValueError as error:
        assert "inexistente" in str(error)
    else:
        raise AssertionError("HPO ID desconhecido deveria falhar")


def test_versioned_index_contains_only_valid_internal_relations():
    path = ROOT / "data/processed/hpo_ontology.json.gz"
    index = load_ontology_index(path)

    assert len(index.concepts) == 19836
    assert index.data_version == "hpo-2026-06-23_pt-62f1d254"
    assert all(
        related_id in index.concepts
        for concept in index.concepts.values()
        for related_id in (*concept.parent_ids, *concept.child_ids)
    )
    with gzip.open(path, mode="rt", encoding="utf-8") as handle:
        serialized = handle.read()
    assert "SNOMEDCT" not in serialized
    assert '"xrefs"' not in serialized
