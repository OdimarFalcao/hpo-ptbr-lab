from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hpo_ptbr.aliases import (
    ACCEPTED_SYNONYM_TYPES,
    EXACT_SYNONYM_PREDICATE,
    extract_exact_aliases,
)
from hpo_ptbr.data import load_metadata, load_snapshot


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    snapshot_path = ROOT / "data/processed/hpo_ptbr.csv"
    hp_json_path = ROOT / "data/raw/hp.json"
    output_path = ROOT / "data/processed/hpo_exact_synonyms_en.csv"
    metadata_path = ROOT / "data/processed/hpo_exact_synonyms_en_metadata.json"

    records = load_snapshot(snapshot_path)
    snapshot_metadata = load_metadata(ROOT / "data/processed/metadata.json")
    aliases = extract_exact_aliases(hp_json_path, records)

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["hpo_id", "alias_en", "synonym_type"],
        )
        writer.writeheader()
        writer.writerows(
            {
                "hpo_id": alias.hpo_id,
                "alias_en": alias.alias_en,
                "synonym_type": alias.synonym_type,
            }
            for alias in aliases
        )

    aliases_by_type = Counter(alias.synonym_type for alias in aliases)
    metadata = {
        "data_version": snapshot_metadata["data_version"],
        "source_sha256": snapshot_metadata["sources"]["hpo"]["sha256"],
        "predicate": EXACT_SYNONYM_PREDICATE,
        "accepted_synonym_types": sorted(ACCEPTED_SYNONYM_TYPES),
        "translated_concepts": len(records),
        "concepts_with_aliases": len({alias.hpo_id for alias in aliases}),
        "aliases": len(aliases),
        "aliases_by_type": dict(sorted(aliases_by_type.items())),
        "dataset_sha256": sha256(output_path),
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
