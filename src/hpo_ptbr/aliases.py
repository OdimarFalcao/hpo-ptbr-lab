from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path

from .data import HpoRecord

HPO_ID_PATTERN = re.compile(r"HP_(\d+)$")
EXACT_SYNONYM_PREDICATE = "hasExactSynonym"
ACCEPTED_SYNONYM_TYPES = frozenset(
    {
        "",
        "http://purl.obolibrary.org/obo/hp#abbreviation",
        "http://purl.obolibrary.org/obo/hp#layperson",
        "http://purl.obolibrary.org/obo/hp#plural_form",
        "http://purl.obolibrary.org/obo/hp#uk_spelling",
    }
)


@dataclass(frozen=True)
class HpoAlias:
    hpo_id: str
    alias_en: str
    synonym_type: str


def _hpo_id_from_iri(iri: str) -> str | None:
    match = HPO_ID_PATTERN.search(iri)
    return f"HP:{match.group(1)}" if match else None


def _normalized_text(text: str) -> str:
    return " ".join(text.split()).casefold()


def extract_exact_aliases(
    hp_json_path: str | Path,
    records: list[HpoRecord],
) -> list[HpoAlias]:
    records_by_id = {record.hpo_id: record for record in records}
    payload = json.loads(Path(hp_json_path).read_text(encoding="utf-8"))
    aliases: list[HpoAlias] = []
    seen: set[tuple[str, str]] = set()

    for node in payload["graphs"][0].get("nodes", []):
        if node.get("type") != "CLASS" or node.get("meta", {}).get("deprecated"):
            continue
        hpo_id = _hpo_id_from_iri(str(node.get("id", "")))
        if hpo_id not in records_by_id:
            continue
        record = records_by_id[hpo_id]
        labels = {
            _normalized_text(record.label_en),
            _normalized_text(record.label_pt),
        }
        for synonym in node.get("meta", {}).get("synonyms", []):
            synonym_type = str(synonym.get("synonymType", ""))
            if (
                synonym.get("pred") != EXACT_SYNONYM_PREDICATE
                or synonym_type not in ACCEPTED_SYNONYM_TYPES
            ):
                continue
            alias_en = " ".join(str(synonym.get("val", "")).split())
            normalized_alias = _normalized_text(alias_en)
            key = (hpo_id, normalized_alias)
            if not alias_en or normalized_alias in labels or key in seen:
                continue
            seen.add(key)
            aliases.append(
                HpoAlias(
                    hpo_id=hpo_id,
                    alias_en=alias_en,
                    synonym_type=synonym_type.rsplit("#", 1)[-1] or "unspecified",
                )
            )

    return sorted(
        aliases,
        key=lambda alias: (
            alias.hpo_id,
            alias.alias_en.casefold(),
            alias.alias_en,
        ),
    )


def load_aliases(path: str | Path) -> list[HpoAlias]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return [
            HpoAlias(
                hpo_id=row["hpo_id"],
                alias_en=row["alias_en"],
                synonym_type=row["synonym_type"],
            )
            for row in csv.DictReader(handle)
        ]
