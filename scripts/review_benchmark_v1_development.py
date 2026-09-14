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
from hpo_ptbr.data import load_metadata, load_snapshot
from hpo_ptbr.evaluation import load_cases

DATASET_PATH = ROOT / "data/eval/benchmark_v1_development.json"
REVIEW_PATH = ROOT / "data/eval/benchmark_v1_development_review.csv"
REVIEW_LOG_PATH = ROOT / "data/eval/benchmark_v1_development_review_log.json"
MANIFEST_PATH = ROOT / "data/eval/benchmark_v1_development_manifest.json"
PROTOCOL_PATH = ROOT / "data/protocol/benchmark_v1_protocol.json"
SNAPSHOT_PATH = ROOT / "data/processed/hpo_ptbr.csv"
METADATA_PATH = ROOT / "data/processed/metadata.json"
HPO_SOURCE_PATH = ROOT / "data/raw/hp.json"

TECHNICAL_REVIEW_STATUS = "technical_approved_pending_human_confirmation"
SURFACE_CORRECTIONS = {
    "HP:0007513": "pigmentação cutânea reduzida de forma generalizada",
}
PARAPHRASE_RATIONALES = {
    "HP:0007034": "Mantém o aumento dos reflexos e a distribuição generalizada do conceito.",
    "HP:0000541": "Corresponde ao sinônimo oficial em inglês 'Detached retina'.",
    "HP:0002803": "Preserva a contratura articular e sua presença desde o nascimento.",
    "HP:0032553": "Preserva a redução da amplitude ou força do pulso.",
    "HP:0030829": "Expressa um som respiratório anômalo sem especificar um subtipo ausente.",
    "HP:0000126": "Expressa a dilatação do sistema coletor renal descrita no conceito.",
    "HP:0007513": "Explicita redução generalizada da pigmentação e evita confusão com palidez.",
    "HP:0007380": "Expressa pequenos vasos visíveis próximos à superfície da pele da face.",
    "HP:0004389": "Preserva manifestações de obstrução intestinal sem bloqueio mecânico.",
    "HP:0006280": "Equivale ao sinônimo oficial em inglês 'Chronic pancreas inflammation'.",
    "HP:0000458": "Equivale ao sinônimo oficial em inglês 'Loss of smell'.",
    "HP:0004409": "Preserva a diminuição, sem perda completa, da percepção de odores.",
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


def _sha256(path: Path) -> str:
    return content_sha256(path)


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


def _hpo_nodes() -> dict[str, dict[str, object]]:
    source = json.loads(HPO_SOURCE_PATH.read_text(encoding="utf-8"))
    return {
        node["id"].rsplit("/", 1)[-1].replace("_", ":"): node
        for node in source["graphs"][0]["nodes"]
    }


def _apply_surface_corrections(document: dict[str, object]) -> list[dict[str, str]]:
    corrections: list[dict[str, str]] = []
    for case in document["cases"]:
        for mention_index, mention in enumerate(case["mentions"]):
            replacement = SURFACE_CORRECTIONS.get(mention["hpo_id"])
            if replacement is None or replacement == mention["text"]:
                continue
            original = mention["text"]
            start = mention["start"]
            end = mention["end"]
            case["text"] = f"{case['text'][:start]}{replacement}{case['text'][end:]}"
            delta = len(replacement) - len(original)
            mention["text"] = replacement
            mention["end"] = start + len(replacement)
            for later_mention in case["mentions"][mention_index + 1 :]:
                later_mention["start"] += delta
                later_mention["end"] += delta
            corrections.append(
                {
                    "case_id": case["case_id"],
                    "hpo_id": mention["hpo_id"],
                    "before": original,
                    "after": replacement,
                    "reason": PARAPHRASE_RATIONALES[mention["hpo_id"]],
                }
            )
    return corrections


def _technical_rationale(mention: dict[str, object]) -> str:
    if mention["surface_form"] == "official_label":
        return "Superfície idêntica ao rótulo português versionado."
    if mention["surface_form"] == "orthographic_variation":
        return "Variação controlada de acento, separador, deleção ou abreviação, sem alterar o conceito-alvo."
    return PARAPHRASE_RATIONALES[mention["hpo_id"]]


def _write_review_form(document: dict[str, object]) -> None:
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
                    "review_status": TECHNICAL_REVIEW_STATUS,
                    "review_notes": "Controle negativo intencional sem menção HPO anotada.",
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
    metadata = load_metadata(METADATA_PATH)
    expected_source_hash = metadata["sources"]["hpo"]["sha256"]
    observed_source_hash = _sha256(HPO_SOURCE_PATH)
    if observed_source_hash != expected_source_hash:
        raise ValueError("O hp.json não corresponde ao hash registrado no snapshot.")

    document = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    corrections = _apply_surface_corrections(document)
    nodes = _hpo_nodes()
    decisions: list[dict[str, object]] = []
    for case in document["cases"]:
        for mention in case["mentions"]:
            rationale = _technical_rationale(mention)
            mention["review_status"] = TECHNICAL_REVIEW_STATUS
            mention["review_notes"] = rationale
            node_meta = nodes[mention["hpo_id"]].get("meta", {})
            decisions.append(
                {
                    "case_id": case["case_id"],
                    "hpo_id": mention["hpo_id"],
                    "surface_text": mention["text"],
                    "surface_form": mention["surface_form"],
                    "assertion": mention["assertion"],
                    "status": TECHNICAL_REVIEW_STATUS,
                    "rationale_pt": rationale,
                    "official_label_en": nodes[mention["hpo_id"]]["lbl"],
                    "official_definition_en": node_meta.get("definition", {}).get("val", ""),
                    "official_exact_synonyms_en": [
                        synonym["val"]
                        for synonym in node_meta.get("synonyms", [])
                        if synonym.get("pred") == "hasExactSynonym"
                    ],
                }
            )

    document["status"] = "technical_review_complete_pending_human_confirmation"
    records = load_snapshot(SNAPSHOT_PATH)
    labels = {record.hpo_id: record.label_pt for record in records}
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    summary = validate_benchmark(
        document,
        labels,
        excluded_hpo_ids=_historical_hpo_ids(),
        official_labels=labels,
    )
    validate_benchmark_targets(summary, protocol, target_name="development")
    DATASET_PATH.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_review_form(document)

    review_log = {
        "status": "technical_review_complete_pending_human_confirmation",
        "review_date": "2026-08-24",
        "reviewer": "Codex technical review under Odimar's instruction",
        "human_clinical_review": False,
        "rankings_consulted": False,
        "methods_executed": False,
        "source": {
            "snapshot": metadata["data_version"],
            "hpo_url": metadata["sources"]["hpo"]["url"],
            "hpo_sha256": observed_source_hash,
        },
        "corrections": corrections,
        "decisions": decisions,
        "limitations": [
            "Technical linguistic and ontology review, not validation by a healthcare professional.",
            "Human confirmation remains pending before any benchmark execution.",
        ],
    }
    REVIEW_LOG_PATH.write_text(
        json.dumps(review_log, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest.update(
        {
            "status": "technical_review_complete_pending_human_confirmation",
            "dataset_sha256": _sha256(DATASET_PATH),
            "review_sha256": _sha256(REVIEW_PATH),
            "review_log": REVIEW_LOG_PATH.relative_to(ROOT).as_posix(),
            "review_log_sha256": _sha256(REVIEW_LOG_PATH),
            "technical_correction_count": len(corrections),
            "rankings_consulted_during_review": False,
            "human_confirmation_pending": True,
        }
    )
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
