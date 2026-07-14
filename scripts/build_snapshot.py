from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

HPO_SOURCE_URL = "https://github.com/obophenotype/human-phenotype-ontology/releases/latest/download/hp.json"
PT_SOURCE_URL = "https://raw.githubusercontent.com/obophenotype/hpo-translations/main/babelon/hp-pt.babelon.tsv"
PT_COMMIT = "62f1d254f93e47d87e874783019ccd7480400e76"
HPO_ID_PATTERN = re.compile(r"HP_(\d+)$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hpo_id_from_iri(iri: str) -> str | None:
    match = HPO_ID_PATTERN.search(iri)
    return f"HP:{match.group(1)}" if match else None


def hpo_release(graph: dict[str, object]) -> str:
    metadata = graph.get("meta", {})
    if isinstance(metadata, dict):
        version = metadata.get("version")
        if isinstance(version, str) and version:
            return version.rstrip("/").split("/")[-2]
        for item in metadata.get("basicPropertyValues", []):
            if isinstance(item, dict) and str(item.get("pred", "")).endswith("versionInfo"):
                return str(item.get("val"))
    return "unknown"


def load_translations(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    labels: dict[str, str] = {}
    definitions: dict[str, str] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row.get("translation_status") != "OFFICIAL":
                continue
            hpo_id = row["subject_id"]
            if row["predicate_id"] == "rdfs:label":
                labels[hpo_id] = row["translation_value"].strip()
            elif row["predicate_id"] == "IAO:0000115":
                definitions[hpo_id] = row["translation_value"].strip()
    return labels, definitions


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build(raw_dir: Path, processed_dir: Path) -> dict[str, object]:
    hp_path = raw_dir / "hp.json"
    pt_path = raw_dir / "hp-pt.babelon.tsv"
    if not hp_path.exists() or not pt_path.exists():
        raise FileNotFoundError("Baixe hp.json e hp-pt.babelon.tsv para data/raw antes de gerar o snapshot.")

    payload = json.loads(hp_path.read_text(encoding="utf-8"))
    graph = payload["graphs"][0]
    labels_pt, definitions_pt = load_translations(pt_path)

    active_terms: list[dict[str, str]] = []
    for node in graph.get("nodes", []):
        if node.get("type") != "CLASS" or node.get("meta", {}).get("deprecated"):
            continue
        hpo_id = hpo_id_from_iri(str(node.get("id", "")))
        label_en = str(node.get("lbl", "")).strip()
        if hpo_id and label_en:
            active_terms.append(
                {
                    "hpo_id": hpo_id,
                    "label_en": label_en,
                    "label_pt": labels_pt.get(hpo_id, ""),
                    "definition_pt": definitions_pt.get(hpo_id, ""),
                }
            )
    active_terms.sort(key=lambda row: row["hpo_id"])

    translated_terms = [row for row in active_terms if row["label_pt"]]
    untranslated_terms = [
        {"hpo_id": row["hpo_id"], "label_en": row["label_en"]}
        for row in active_terms
        if not row["label_pt"]
    ]
    release = hpo_release(graph)
    data_version = f"hpo-{release}_pt-{PT_COMMIT[:8]}"
    generated_at = datetime.now(UTC).isoformat()

    write_csv(
        processed_dir / "hpo_ptbr.csv",
        active_terms,
        ["hpo_id", "label_en", "label_pt", "definition_pt"],
    )
    write_csv(
        processed_dir / "untranslated_terms.csv",
        untranslated_terms,
        ["hpo_id", "label_en"],
    )

    summary: dict[str, object] = {
        "data_version": data_version,
        "hpo_release": release,
        "translation_commit": PT_COMMIT,
        "generated_at": generated_at,
        "active_terms": len(active_terms),
        "translated_labels_pt": len(translated_terms),
        "translated_definitions_pt": sum(bool(row["definition_pt"]) for row in active_terms),
        "label_coverage_percent": round(len(translated_terms) / len(active_terms) * 100, 2),
        "sources": {
            "hpo": {"url": HPO_SOURCE_URL, "sha256": sha256(hp_path)},
            "hpo_pt": {"url": PT_SOURCE_URL, "commit": PT_COMMIT, "sha256": sha256(pt_path)},
        },
    }
    processed_dir.mkdir(parents=True, exist_ok=True)
    (processed_dir / "coverage_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (processed_dir / "metadata.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera o snapshot versionado HPO-PTBR.")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    args = parser.parse_args()
    summary = build(args.raw_dir, args.processed_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
