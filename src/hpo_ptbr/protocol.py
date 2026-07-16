from __future__ import annotations

import csv
import hashlib
import json
import random
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .data import HpoRecord
from .evaluation import load_cases
from .normalize import normalize_text

SELECTION_SEED = 20260717
BUCKET_TARGETS = {1: 4, 2: 3, 3: 3}
ORTHOGRAPHIC_RULES = (
    "remove_accent",
    "remove_accent",
    "separator",
    "separator",
    "case_punctuation",
    "case_punctuation",
    "deletion",
    "deletion",
    "transposition",
    "transposition",
)
REVIEW_COLUMNS = (
    "selection_order",
    "hpo_id",
    "label_pt",
    "label_en",
    "label_word_bucket",
    "orthographic_rule",
    "orthographic_query",
    "proposed_paraphrase_pt",
    "review_status",
    "review_notes",
)
REJECTION_COLUMNS = (*REVIEW_COLUMNS, "rejected_at")


@dataclass(frozen=True)
class SelectedConcept:
    selection_order: int
    record: HpoRecord
    word_bucket: int
    orthographic_rule: str
    orthographic_query: str


def _eligible_label(label: str) -> bool:
    return 3 <= len(label) <= 80 and all(char.isalpha() or char in " -" for char in label)


def _word_bucket(label: str) -> int:
    return min(len(label.split()), 3)


def _without_accents(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def orthographic_variant(label: str, rule: str) -> str:
    if rule == "remove_accent":
        return _without_accents(label).lower()
    if rule == "separator":
        if " " in label:
            return label.lower().replace(" ", "-", 1)
        midpoint = max(1, len(label) // 2)
        return f"{label[:midpoint]} {label[midpoint:]}".lower()
    if rule == "case_punctuation":
        return f"{label.upper()}."
    if rule == "deletion":
        alphabetic_positions = [index for index, char in enumerate(label) if char.isalpha()]
        position = alphabetic_positions[len(alphabetic_positions) // 2]
        return f"{label[:position]}{label[position + 1:]}".lower()
    if rule == "transposition":
        characters = list(label.lower())
        pairs = [
            index
            for index in range(len(characters) - 1)
            if characters[index].isalpha() and characters[index + 1].isalpha()
        ]
        left = min(pairs, key=lambda index: abs(index - len(characters) // 2))
        characters[left], characters[left + 1] = characters[left + 1], characters[left]
        return "".join(characters)
    raise ValueError(f"Regra ortográfica desconhecida: {rule}")


def select_holdout_concepts(
    records: list[HpoRecord],
    development_cases: list[dict[str, str]],
) -> list[SelectedConcept]:
    development_ids = {case["target_hpo_id"] for case in development_cases}
    pools: dict[int, list[HpoRecord]] = {1: [], 2: [], 3: []}
    for record in sorted(records, key=lambda item: item.hpo_id):
        if record.hpo_id in development_ids or not _eligible_label(record.label_pt):
            continue
        pools[_word_bucket(record.label_pt)].append(record)

    randomizer = random.Random(SELECTION_SEED)
    rules_by_bucket = {
        1: ORTHOGRAPHIC_RULES[:4],
        2: ORTHOGRAPHIC_RULES[4:7],
        3: ORTHOGRAPHIC_RULES[7:],
    }
    selected_records: list[tuple[HpoRecord, int, str]] = []
    for bucket, target in BUCKET_TARGETS.items():
        shuffled = pools[bucket].copy()
        randomizer.shuffle(shuffled)
        selected_ids: set[str] = set()
        for rule in rules_by_bucket[bucket]:
            record = next(
                candidate
                for candidate in shuffled
                if candidate.hpo_id not in selected_ids
                and (
                    rule != "remove_accent"
                    or _without_accents(candidate.label_pt) != candidate.label_pt
                )
            )
            selected_ids.add(record.hpo_id)
            selected_records.append((record, bucket, rule))
        if len(selected_ids) != target:
            raise ValueError(f"Não foi possível preencher o estrato de {bucket} palavra(s).")

    selected: list[SelectedConcept] = []
    for index, (record, bucket, rule) in enumerate(selected_records, start=1):
        selected.append(
            SelectedConcept(
                selection_order=index,
                record=record,
                word_bucket=bucket,
                orthographic_rule=rule,
                orthographic_query=orthographic_variant(record.label_pt, rule),
            )
        )
    return selected


def write_review_form(path: str | Path, concepts: list[SelectedConcept]) -> None:
    review_path = Path(path)
    review_path.parent.mkdir(parents=True, exist_ok=True)
    with review_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_COLUMNS)
        writer.writeheader()
        for concept in concepts:
            writer.writerow(
                {
                    "selection_order": concept.selection_order,
                    "hpo_id": concept.record.hpo_id,
                    "label_pt": concept.record.label_pt,
                    "label_en": concept.record.label_en,
                    "label_word_bucket": concept.word_bucket,
                    "orthographic_rule": concept.orthographic_rule,
                    "orthographic_query": concept.orthographic_query,
                    "proposed_paraphrase_pt": "",
                    "review_status": "pending",
                    "review_notes": "",
                }
            )


def replace_rejected_concepts(
    review_path: str | Path,
    rejections_path: str | Path,
    records: list[HpoRecord],
    development_cases: list[dict[str, str]],
) -> int:
    review = Path(review_path)
    with review.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rejected_rows = [row for row in rows if row["review_status"] == "rejected"]
    if not rejected_rows:
        return 0
    if any(not row["review_notes"].strip() for row in rejected_rows):
        raise ValueError("Todo conceito rejeitado precisa registrar o motivo.")

    development_ids = {case["target_hpo_id"] for case in development_cases}
    pools: dict[int, list[HpoRecord]] = {1: [], 2: [], 3: []}
    for record in sorted(records, key=lambda item: item.hpo_id):
        if record.hpo_id in development_ids or not _eligible_label(record.label_pt):
            continue
        pools[_word_bucket(record.label_pt)].append(record)
    randomizer = random.Random(SELECTION_SEED)
    for pool in pools.values():
        randomizer.shuffle(pool)

    rejections = Path(rejections_path)
    existing_rejections: list[dict[str, str]] = []
    if rejections.exists():
        with rejections.open(encoding="utf-8", newline="") as handle:
            existing_rejections = list(csv.DictReader(handle))
    banned_ids = {row["hpo_id"] for row in rows}
    banned_ids.update(row["hpo_id"] for row in existing_rejections)
    rejected_at = datetime.now(UTC).isoformat()

    for row in rejected_rows:
        bucket = int(row["label_word_bucket"])
        rule = row["orthographic_rule"]
        replacement = next(
            candidate
            for candidate in pools[bucket]
            if candidate.hpo_id not in banned_ids
            and (
                rule != "remove_accent"
                or _without_accents(candidate.label_pt) != candidate.label_pt
            )
        )
        existing_rejections.append({**row, "rejected_at": rejected_at})
        banned_ids.add(replacement.hpo_id)
        row.update(
            {
                "hpo_id": replacement.hpo_id,
                "label_pt": replacement.label_pt,
                "label_en": replacement.label_en,
                "orthographic_query": orthographic_variant(replacement.label_pt, rule),
                "proposed_paraphrase_pt": "",
                "review_status": "pending",
                "review_notes": "",
            }
        )

    with review.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    rejections.parent.mkdir(parents=True, exist_ok=True)
    with rejections.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REJECTION_COLUMNS)
        writer.writeheader()
        writer.writerows(existing_rejections)
    return len(rejected_rows)


def _validate_review_rows(
    rows: list[dict[str, str]],
    records: list[HpoRecord],
    development_cases: list[dict[str, str]],
) -> None:
    if len(rows) != 10:
        raise ValueError("O formulário deve conter exatamente 10 conceitos.")
    snapshot_ids = {record.hpo_id for record in records}
    records_by_id = {record.hpo_id: record for record in records}
    development_ids = {case["target_hpo_id"] for case in development_cases}
    holdout_ids = [row["hpo_id"] for row in rows]
    if len(set(holdout_ids)) != 10:
        raise ValueError("Os conceitos do holdout devem ser únicos.")
    if development_ids.intersection(holdout_ids):
        raise ValueError("Há sobreposição de HPO IDs entre desenvolvimento e holdout.")
    if any(hpo_id not in snapshot_ids for hpo_id in holdout_ids):
        raise ValueError("O formulário contém HPO ID ausente no snapshot.")
    if sorted(int(row["selection_order"]) for row in rows) != list(range(1, 11)):
        raise ValueError("A ordem de seleção deve conter os valores de 1 a 10.")
    if any(row["review_status"] != "approved" for row in rows):
        raise ValueError("Todos os conceitos precisam ser aprovados por Odimar.")
    for row in rows:
        record = records_by_id[row["hpo_id"]]
        order = int(row["selection_order"])
        expected_rule = ORTHOGRAPHIC_RULES[order - 1]
        if row["label_pt"] != record.label_pt or row["label_en"] != record.label_en:
            raise ValueError(f"Rótulo alterado em relação ao snapshot: {row['hpo_id']}")
        if int(row["label_word_bucket"]) != _word_bucket(record.label_pt):
            raise ValueError(f"Estrato de palavras inválido: {row['hpo_id']}")
        if row["orthographic_rule"] != expected_rule:
            raise ValueError(f"Regra ortográfica fora da agenda: {row['hpo_id']}")
        if row["orthographic_query"] != orthographic_variant(record.label_pt, expected_rule):
            raise ValueError(f"Variação ortográfica alterada: {row['hpo_id']}")
        paraphrase = row["proposed_paraphrase_pt"].strip()
        word_count = len(paraphrase.split())
        if word_count < 4 or word_count > 12:
            raise ValueError(f"Paráfrase fora do limite de 4–12 palavras: {row['hpo_id']}")
        if normalize_text(row["label_pt"]) in normalize_text(paraphrase):
            raise ValueError(f"Paráfrase repete o rótulo oficial: {row['hpo_id']}")


def freeze_holdout(
    review_path: str | Path,
    output_path: str | Path,
    manifest_path: str | Path,
    records: list[HpoRecord],
    development_path: str | Path,
    data_version: str,
    rejections_path: str | Path | None = None,
) -> dict[str, object]:
    with Path(review_path).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    development_cases = load_cases(development_path)
    _validate_review_rows(rows, records, development_cases)

    cases: list[dict[str, str]] = []
    for index, row in enumerate(rows, start=1):
        suffix = f"{index:02d}"
        cases.extend(
            [
                {
                    "case_id": f"HLD-OFF-{suffix}",
                    "query_pt": row["label_pt"],
                    "target_hpo_id": row["hpo_id"],
                    "stratum": "official_label",
                    "provenance": "HPO-PT official label",
                },
                {
                    "case_id": f"HLD-ORT-{suffix}",
                    "query_pt": row["orthographic_query"],
                    "target_hpo_id": row["hpo_id"],
                    "stratum": "orthographic_variation",
                    "provenance": f"Deterministic {row['orthographic_rule']} variation",
                },
                {
                    "case_id": f"HLD-PAR-{suffix}",
                    "query_pt": row["proposed_paraphrase_pt"].strip(),
                    "target_hpo_id": row["hpo_id"],
                    "stratum": "clinical_paraphrase",
                    "provenance": "Synthetic paraphrase approved blindly by Odimar",
                },
            ]
        )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(cases[0]))
        writer.writeheader()
        writer.writerows(cases)
    checksum = hashlib.sha256(output.read_bytes()).hexdigest()
    rejections: list[dict[str, str]] = []
    if rejections_path and Path(rejections_path).exists():
        with Path(rejections_path).open(encoding="utf-8", newline="") as handle:
            rejections = list(csv.DictReader(handle))
    manifest: dict[str, object] = {
        "status": "frozen",
        "frozen_at": datetime.now(UTC).isoformat(),
        "data_version": data_version,
        "selection_seed": SELECTION_SEED,
        "case_count": len(cases),
        "concept_count": len(rows),
        "strata": dict(Counter(case["stratum"] for case in cases)),
        "development_hpo_ids": sorted(
            {case["target_hpo_id"] for case in development_cases}
        ),
        "holdout_hpo_ids": sorted({case["target_hpo_id"] for case in cases}),
        "sha256": checksum,
        "review_file": Path(review_path).name,
        "rejections": rejections,
    }
    Path(manifest_path).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest
