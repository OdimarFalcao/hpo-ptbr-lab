from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hpo_ptbr.hashing import content_sha256
from hpo_ptbr.benchmark import validate_benchmark, validate_benchmark_targets
from hpo_ptbr.data import load_snapshot
from hpo_ptbr.evaluation import load_cases

PLAN_PATH = ROOT / "data/protocol/benchmark_v1_development_plan.json"
PROTOCOL_PATH = ROOT / "data/protocol/benchmark_v1_protocol.json"
SNAPSHOT_PATH = ROOT / "data/processed/hpo_ptbr.csv"
OUTPUT_PATH = ROOT / "data/eval/benchmark_v1_development.json"
REVIEW_PATH = ROOT / "data/eval/benchmark_v1_development_review.csv"
MANIFEST_PATH = ROOT / "data/eval/benchmark_v1_development_manifest.json"

SENTENCE_TEMPLATES = {
    "present": (
        "O registro menciona {mention}.",
        "A avaliação documenta {mention}.",
        "A descrição inclui {mention}.",
        "O texto sintético descreve {mention}.",
        "O registro contém {mention}.",
        "A anotação apresenta {mention}.",
    ),
    "absent": (
        "Não há evidência de {mention}.",
        "A avaliação não identificou {mention}.",
        "O registro nega {mention}.",
        "Não foram encontrados sinais de {mention}.",
    ),
    "uncertain": (
        "Permanece a hipótese de {mention}.",
        "A avaliação levanta suspeita de {mention}.",
        "O registro mantém {mention} como possibilidade.",
        "Ainda se investiga {mention}.",
    ),
    "family_history": (
        "Há histórico familiar de {mention}.",
        "A família relata ocorrência de {mention}.",
        "O antecedente familiar inclui {mention}.",
        "O histórico familiar registra {mention}.",
    ),
}
REVIEW_COLUMNS = (
    "case_id",
    "domain",
    "case_type",
    "case_text",
    "mention_order",
    "surface_text",
    "start",
    "end",
    "hpo_id",
    "label_pt",
    "label_en",
    "assertion",
    "surface_form",
    "review_status",
    "review_notes",
)


def _historical_hpo_ids() -> set[str]:
    historical = {
        case["target_hpo_id"]
        for path in (
            ROOT / "data/eval/pilot_cases.csv",
            ROOT / "data/eval/holdout_cases.csv",
        )
        for case in load_cases(path)
    }
    demo_cases = json.loads(
        (ROOT / "data/demo/synthetic_review_cases.json").read_text(encoding="utf-8")
    )
    historical.update(
        mention["hpo_id"]
        for case in demo_cases
        for mention in case["mentions"]
    )
    return historical


def _build_case(case_plan: dict[str, object], records_by_id):
    case_type = str(case_plan.get("case_type", "phenotype"))
    if case_type == "negative_control":
        return {
            "case_id": case_plan["case_id"],
            "split": "development",
            "domain": case_plan["domain"],
            "case_type": case_type,
            "text": case_plan["text"],
            "mentions": [],
        }

    sentences: list[str] = []
    mentions: list[dict[str, object]] = []
    current_offset = 0
    case_id = str(case_plan["case_id"])
    for mention_order, mention_plan in enumerate(case_plan["mentions"], start=1):
        surface_text = mention_plan["surface_text"]
        templates = SENTENCE_TEMPLATES[mention_plan["assertion"]]
        template_index = (sum(ord(char) for char in case_id) + mention_order) % len(
            templates
        )
        sentence = templates[template_index].format(mention=surface_text)
        start = current_offset + sentence.index(surface_text)
        end = start + len(surface_text)
        record = records_by_id[mention_plan["hpo_id"]]
        mentions.append(
            {
                "text": surface_text,
                "start": start,
                "end": end,
                "hpo_id": record.hpo_id,
                "label_pt": record.label_pt,
                "label_en": record.label_en,
                "assertion": mention_plan["assertion"],
                "surface_form": mention_plan["surface_form"],
                "review_status": "pending",
                "review_notes": "",
            }
        )
        sentences.append(sentence)
        current_offset += len(sentence) + 1
    return {
        "case_id": case_id,
        "split": "development",
        "domain": case_plan["domain"],
        "case_type": case_type,
        "text": " ".join(sentences),
        "mentions": mentions,
    }


def build_development_document() -> tuple[dict[str, object], dict[str, object]]:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    records = load_snapshot(SNAPSHOT_PATH)
    records_by_id = {record.hpo_id: record for record in records}
    document = {
        "benchmark_version": plan["benchmark_version"],
        "snapshot": plan["snapshot"],
        "status": plan["status"],
        "selection_method": plan["selection_method"],
        "cases": [_build_case(case_plan, records_by_id) for case_plan in plan["cases"]],
    }
    summary = validate_benchmark(
        document,
        records_by_id,
        excluded_hpo_ids=_historical_hpo_ids(),
        official_labels={hpo_id: record.label_pt for hpo_id, record in records_by_id.items()},
    )
    validate_benchmark_targets(summary, protocol, target_name="development")
    return document, {
        "case_count": summary.case_count,
        "mention_count": summary.mention_count,
        "negative_control_count": summary.negative_control_count,
        "cases_by_split": dict(summary.cases_by_split),
        "mentions_by_split": dict(summary.mentions_by_split),
        "domains": sorted(summary.domains),
        "assertion_counts": dict(summary.assertion_counts),
        "surface_form_counts": dict(summary.surface_form_counts),
        "domain_mention_counts": dict(summary.domain_mention_counts),
        "hpo_ids": sorted(summary.hpo_ids),
    }


def _write_review(document: dict[str, object]) -> None:
    rows: list[dict[str, object]] = []
    for case in document["cases"]:
        if not case["mentions"]:
            rows.append(
                {
                    "case_id": case["case_id"],
                    "domain": case["domain"],
                    "case_type": case["case_type"],
                    "case_text": case["text"],
                    "mention_order": "",
                    "surface_text": "",
                    "start": "",
                    "end": "",
                    "hpo_id": "",
                    "label_pt": "",
                    "label_en": "",
                    "assertion": "",
                    "surface_form": "",
                    "review_status": "pending",
                    "review_notes": "",
                }
            )
            continue
        for mention_order, mention in enumerate(case["mentions"], start=1):
            rows.append(
                {
                    "case_id": case["case_id"],
                    "domain": case["domain"],
                    "case_type": case["case_type"],
                    "case_text": case["text"],
                    "mention_order": mention_order,
                    "surface_text": mention["text"],
                    "start": mention["start"],
                    "end": mention["end"],
                    "hpo_id": mention["hpo_id"],
                    "label_pt": mention["label_pt"],
                    "label_en": mention["label_en"],
                    "assertion": mention["assertion"],
                    "surface_form": mention["surface_form"],
                    "review_status": mention["review_status"],
                    "review_notes": mention["review_notes"],
                }
            )
    with REVIEW_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    document, summary = build_development_document()
    OUTPUT_PATH.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_review(document)
    manifest = {
        "status": "draft_pending_blind_review",
        "protocol_version": "ptbr-phenotype-benchmark-v1",
        "snapshot": document["snapshot"],
        "selection_plan": PLAN_PATH.relative_to(ROOT).as_posix(),
        "historical_exclusions": [
            "data/eval/pilot_cases.csv",
            "data/eval/holdout_cases.csv",
            "data/demo/synthetic_review_cases.json",
        ],
        **summary,
        "dataset_sha256": content_sha256(OUTPUT_PATH),
        "review_sha256": content_sha256(REVIEW_PATH),
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
