from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from hpo_ptbr.aliases import extract_exact_aliases
from hpo_ptbr.data import HpoRecord

ROOT = Path(__file__).resolve().parents[1]


def test_extract_exact_aliases_filters_and_orders(tmp_path) -> None:
    payload = {
        "graphs": [
            {
                "nodes": [
                    {
                        "id": "http://purl.obolibrary.org/obo/HP_0000002",
                        "type": "CLASS",
                        "meta": {
                            "synonyms": [
                                {
                                    "pred": "hasRelatedSynonym",
                                    "val": "Related term",
                                },
                                {
                                    "pred": "hasExactSynonym",
                                    "val": "  Second   alias ",
                                },
                                {
                                    "pred": "hasExactSynonym",
                                    "val": "second alias",
                                },
                                {
                                    "pred": "hasExactSynonym",
                                    "val": "Obsolete term",
                                    "synonymType": (
                                        "http://purl.obolibrary.org/obo/"
                                        "hp#obsolete_synonym"
                                    ),
                                },
                            ]
                        },
                    },
                    {
                        "id": "http://purl.obolibrary.org/obo/HP_0000001",
                        "type": "CLASS",
                        "meta": {
                            "synonyms": [
                                {
                                    "pred": "hasExactSynonym",
                                    "val": "First alias",
                                    "synonymType": (
                                        "http://purl.obolibrary.org/obo/hp#layperson"
                                    ),
                                },
                                {
                                    "pred": "hasExactSynonym",
                                    "val": "English label",
                                },
                            ]
                        },
                    },
                    {
                        "id": "http://purl.obolibrary.org/obo/HP_9999999",
                        "type": "CLASS",
                        "meta": {
                            "synonyms": [
                                {
                                    "pred": "hasExactSynonym",
                                    "val": "Unknown concept",
                                }
                            ]
                        },
                    },
                ]
            }
        ]
    }
    hp_json_path = tmp_path / "hp.json"
    hp_json_path.write_text(json.dumps(payload), encoding="utf-8")
    records = [
        HpoRecord("HP:0000002", "Second label", "Segundo rótulo"),
        HpoRecord("HP:0000001", "English label", "Primeiro rótulo"),
    ]

    aliases = extract_exact_aliases(hp_json_path, records)

    assert [
        (alias.hpo_id, alias.alias_en, alias.synonym_type)
        for alias in aliases
    ] == [
        ("HP:0000001", "First alias", "layperson"),
        ("HP:0000002", "Second alias", "unspecified"),
    ]


def test_versioned_alias_dataset_matches_metadata_and_snapshot() -> None:
    alias_path = ROOT / "data/processed/hpo_exact_synonyms_en.csv"
    metadata = json.loads(
        (
            ROOT / "data/processed/hpo_exact_synonyms_en_metadata.json"
        ).read_text(encoding="utf-8")
    )
    with alias_path.open(encoding="utf-8", newline="") as handle:
        aliases = list(csv.DictReader(handle))
    with (ROOT / "data/processed/hpo_ptbr.csv").open(
        encoding="utf-8",
        newline="",
    ) as handle:
        translated_ids = {
            row["hpo_id"]
            for row in csv.DictReader(handle)
            if row["label_pt"].strip()
        }

    assert len(aliases) == metadata["aliases"] == 8921
    assert len({row["hpo_id"] for row in aliases}) == metadata[
        "concepts_with_aliases"
    ]
    assert {row["hpo_id"] for row in aliases} <= translated_ids
    normalized_content = alias_path.read_text(encoding="utf-8").encode("utf-8")
    assert hashlib.sha256(normalized_content).hexdigest() == metadata["dataset_sha256"]
