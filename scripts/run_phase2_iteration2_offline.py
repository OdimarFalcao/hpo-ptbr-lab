from __future__ import annotations

import hashlib
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hpo_ptbr.hashing import content_sha256
from hpo_ptbr.data import load_metadata, load_snapshot
from hpo_ptbr.evidence import EvidenceExtractor
from hpo_ptbr.official_term_index import (
    OfficialBm25Ranker,
    OfficialExactRanker,
    OfficialFuzzyRanker,
    OfficialSemanticRanker,
    build_official_term_index,
)
from hpo_ptbr.ontology import load_ontology_index
from hpo_ptbr.phase2_evaluation import load_phase2_dataset
from hpo_ptbr.rankers import FuzzyMapper
from hpo_ptbr.sapbert import (
    DEFAULT_SAPBERT_MODEL_NAME,
    DEFAULT_SAPBERT_MODEL_REVISION,
    DEFAULT_SAPBERT_MODEL_SHA256,
    SapBertEncoder,
)

PROTOCOL_PATH = ROOT / "data/protocol/phase2_iteration2_offline_protocol.json"
BASELINE_PATH = ROOT / "data/protocol/phase2_baseline_freeze.json"
DATASET_PATH = ROOT / "data/eval/phase2_development.json"
ONTOLOGY_PATH = ROOT / "data/processed/hpo_ontology.json.gz"
METADATA_PATH = ROOT / "data/processed/metadata.json"
RESULTS_DIR = ROOT / "data/results"


def sha256(path: Path) -> str:
    return content_sha256(path)


def verify_frozen_baseline() -> dict[str, object]:
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    for relative_path, expected_hash in baseline["sha256"].items():
        if sha256(ROOT / relative_path) != expected_hash:
            raise ValueError(f"Baseline divergiu em {relative_path}.")
    return baseline


def baseline_candidates(result, translation_version: str) -> list[dict[str, object]]:
    return [
        {
            **candidate.to_dict(),
            "label_pt_status": "official",
            "matched_term": candidate.label_pt,
            "matched_term_language": "pt-BR",
            "matched_term_field": "official_label_pt",
            "matched_term_scope": "label",
            "term_source": "hpo_pt",
            "term_source_version": translation_version,
            "human_review_required": True,
        }
        for candidate in result.candidates
    ]


def evaluate_ranker(
    method: str,
    ranker,
    dataset: dict[str, object],
    ontology,
    translation_version: str,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    details = []
    latencies = []
    for case in dataset["cases"]:
        for annotation in case["annotations"]:
            result = ranker.map(str(annotation["mention_text"]), top_k=5)
            latencies.append(result.latency_ms)
            candidates = (
                baseline_candidates(result, translation_version)
                if method == "baseline_pt_fuzzy"
                else [candidate.to_dict() for candidate in result.candidates]
            )
            target = str(annotation["hpo_id"])
            rank = next(
                (
                    index
                    for index, candidate in enumerate(candidates, start=1)
                    if candidate["hpo_id"] == target
                ),
                None,
            )
            concept = ontology.require_phenotypic_abnormality(target)
            details.append(
                {
                    "method": method,
                    "case_id": case["case_id"],
                    "query": annotation["mention_text"],
                    "target_hpo_id": target,
                    "target_label_pt": concept.label_pt or None,
                    "target_label_pt_status": "official" if concept.label_pt else "unavailable",
                    "target_label_en": concept.label_en,
                    "target_rank": rank,
                    "target_at_1": rank == 1,
                    "target_at_5": rank is not None,
                    "reciprocal_rank_at_5": round(1 / rank, 6) if rank else 0.0,
                    "latency_ms": result.latency_ms,
                    "candidates": candidates,
                }
            )

    def metrics(rows: list[dict[str, object]]) -> dict[str, object]:
        count = len(rows)
        return {
            "n": count,
            "accuracy_at_1": round(sum(bool(row["target_at_1"]) for row in rows) / count, 4) if count else None,
            "accuracy_at_5": round(sum(bool(row["target_at_5"]) for row in rows) / count, 4) if count else None,
            "mrr_at_5": round(statistics.fmean(float(row["reciprocal_rank_at_5"]) for row in rows), 4) if count else None,
            "targets_retrieved_at_5": sum(bool(row["target_at_5"]) for row in rows),
        }

    summary = {
        "method": method,
        "overall": metrics(details),
        "by_label_pt_status": {
            status: metrics([row for row in details if row["target_label_pt_status"] == status])
            for status in ("official", "unavailable")
        },
        "latency_mean_ms": round(statistics.fmean(latencies), 3),
        "latency_median_ms": round(statistics.median(latencies), 3),
        "latency_is_descriptive_only": True,
    }
    return details, summary


def detector_control(dataset: dict[str, object], mapper, pipeline: dict[str, object]) -> dict[str, object]:
    extractor = EvidenceExtractor(
        mapper,
        detection_threshold=float(pipeline["detector_threshold"]),
        max_span_tokens=int(pipeline["detector_max_span_tokens"]),
    )
    rows = []
    for case in dataset["cases"]:
        result = extractor.map_text(
            str(case["text"]),
            top_k=int(pipeline["top_k"]),
            max_spans=int(pipeline["max_spans"]),
        )
        rows.append(
            {
                "case_id": case["case_id"],
                "is_negative_control": not bool(case["annotations"]),
                "predicted_spans": len(result.spans),
            }
        )
    controls = [row for row in rows if row["is_negative_control"]]
    return {
        "detector_unchanged_from_iteration_1": True,
        "n_cases": len(rows),
        "predicted_spans_all_cases": sum(int(row["predicted_spans"]) for row in rows),
        "n_negative_controls": len(controls),
        "negative_controls_with_false_positive": sum(int(row["predicted_spans"]) > 0 for row in controls),
        "negative_control_false_positive_rate": round(
            sum(int(row["predicted_spans"]) > 0 for row in controls) / len(controls), 4
        ),
        "note": "Os rankers novos recebem somente spans fornecidos; não criam menções automáticas. O detector automático permaneceu congelado.",
    }


def build_error_analysis(
    details: list[dict[str, object]],
    ontology,
    best_method: str,
) -> dict[str, object]:
    rows = [row for row in details if row["method"] == best_method]
    errors = []
    for row in rows:
        candidates = row["candidates"]
        top_hpo_id = str(candidates[0]["hpo_id"]) if candidates else None
        target_hpo_id = str(row["target_hpo_id"])
        categories = []
        if row["target_rank"] is None:
            categories.append("target_not_retrieved_at_5")
        elif int(row["target_rank"]) > 1:
            categories.append("correct_candidate_below_top_1")
        if row["target_label_pt_status"] == "unavailable" and row["target_rank"] is None:
            categories.append("portuguese_coverage_unresolved")
        if top_hpo_id and top_hpo_id != target_hpo_id:
            if top_hpo_id in ontology.path_to_root(target_hpo_id)[1:]:
                categories.append("top_candidate_too_generic")
            elif target_hpo_id in ontology.path_to_root(top_hpo_id)[1:]:
                categories.append("top_candidate_too_specific")
            else:
                categories.append("wrong_concept_different_branch")
        errors.append(
            {
                "case_id": row["case_id"],
                "query": row["query"],
                "target_hpo_id": target_hpo_id,
                "target_label_pt_status": row["target_label_pt_status"],
                "target_rank": row["target_rank"],
                "top_hpo_id": top_hpo_id,
                "top_label_pt": candidates[0]["label_pt"] or None if candidates else None,
                "top_label_en": candidates[0]["label_en"] if candidates else None,
                "categories": categories,
            }
        )
    counts = Counter(category for row in errors for category in row["categories"])
    return {
        "schema_version": "phase2-iteration2-error-analysis-v1",
        "method": best_method,
        "n_gold_mentions": len(rows),
        "counts": dict(sorted(counts.items())),
        "errors": errors,
        "categories_can_overlap": True,
        "clinical_adjudication": False,
        "interpretation": "Classificação técnica no desenvolvimento sintético; relações ontológicas não determinam adequação clínica.",
    }


def report(summary: dict[str, object]) -> str:
    lines = [
        "# Fase 2 — Iteração 2 offline",
        "",
        "## Escopo",
        "",
        "Avaliação de linking em nove trechos-ouro sintéticos de desenvolvimento. A aplicação, validação e holdout não foram alterados nem executados.",
        "",
        "## Resultados",
        "",
        "| Método | Acc@1 | Acc@5 | MRR@5 | Sem PT recuperados@5 |",
        "|---|---:|---:|---:|---:|",
    ]
    for method in summary["methods"]:
        overall = method["overall"]
        unavailable = method["by_label_pt_status"]["unavailable"]
        lines.append(
            f"| `{method['method']}` | {overall['accuracy_at_1']:.1%} | {overall['accuracy_at_5']:.1%} | {overall['mrr_at_5']:.1%} | {unavailable['targets_retrieved_at_5']}/{unavailable['n']} |"
        )
    control = summary["automatic_detector_control"]
    decision = summary["decision"]
    lines.extend(
        [
            "",
            "## Controle de falsos positivos",
            "",
            f"O detector congelado produziu {control['predicted_spans_all_cases']} spans nos onze casos e {control['negative_controls_with_false_positive']}/{control['n_negative_controls']} controles negativos com falso positivo. O linking em span-ouro não é um detector e não possui taxa própria de falso positivo.",
            "",
            "## Decisão",
            "",
            f"Status: `{decision['status']}`.",
            "",
            decision["reason"],
            "",
            "Mesmo um ganho neste desenvolvimento pequeno não demonstra generalização ou segurança clínica. Nenhuma alteração foi integrada à API ou ao frontend.",
            "",
        ]
    )
    if summary["semantic_method_status"]["status"] != "executed":
        lines.extend(
            [
                "## SapBERT",
                "",
                f"Não executado: {summary['semantic_method_status']['reason']}",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> None:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol["status"] != "development_only_registered_before_execution":
        raise ValueError("Protocolo da Iteração 2 não está pré-registrado para desenvolvimento.")
    if protocol["inputs"]["allowed_split"] != "development":
        raise ValueError("Somente o desenvolvimento está autorizado.")
    baseline = verify_frozen_baseline()
    metadata = load_metadata(METADATA_PATH)
    ontology = load_ontology_index(ONTOLOGY_PATH)
    dataset = load_phase2_dataset(DATASET_PATH, ontology, expected_split="development")
    index = build_official_term_index(ontology, metadata)
    translated_records = [
        record
        for record in load_snapshot(ROOT / "data/processed/hpo_ptbr.csv")
        if ontology.is_phenotypic_abnormality(record.hpo_id)
    ]
    baseline_mapper = FuzzyMapper(translated_records, ontology.data_version)

    rankers = [
        ("baseline_pt_fuzzy", baseline_mapper),
        ("official_terms_exact", OfficialExactRanker(index, ontology)),
        ("official_terms_fuzzy", OfficialFuzzyRanker(index, ontology)),
        ("official_terms_bm25", OfficialBm25Ranker(index, ontology)),
    ]
    semantic_status: dict[str, object]
    try:
        encoder = SapBertEncoder(local_files_only=True)
        rankers.append(
            (
                "official_terms_sapbert",
                OfficialSemanticRanker(index, ontology, encoder),
            )
        )
        semantic_status = {
            "status": "executed",
            "model": DEFAULT_SAPBERT_MODEL_NAME,
            "revision": DEFAULT_SAPBERT_MODEL_REVISION,
            "sha256": DEFAULT_SAPBERT_MODEL_SHA256,
            "local_files_only": True,
        }
    except (ImportError, OSError) as error:
        semantic_status = {
            "status": "not_executed",
            "reason": f"modelo ou dependência indisponível somente no cache local: {type(error).__name__}",
            "network_download_attempted": False,
        }

    all_details = []
    method_summaries = []
    for method, ranker in rankers:
        details, method_summary = evaluate_ranker(
            method,
            ranker,
            dataset,
            ontology,
            str(metadata["translation_commit"]),
        )
        all_details.extend(details)
        method_summaries.append(method_summary)

    detector = detector_control(dataset, baseline_mapper, baseline["pipeline"])
    baseline_summary = next(item for item in method_summaries if item["method"] == "baseline_pt_fuzzy")
    candidates = [item for item in method_summaries if item["method"] != "baseline_pt_fuzzy"]
    best = max(
        candidates,
        key=lambda item: (
            item["overall"]["accuracy_at_5"],
            item["overall"]["accuracy_at_1"],
            item["method"],
        ),
    )
    conditions = {
        "accuracy_at_5_strictly_exceeds_baseline": best["overall"]["accuracy_at_5"] > baseline_summary["overall"]["accuracy_at_5"],
        "retrieves_untranslated_target_at_5": best["by_label_pt_status"]["unavailable"]["targets_retrieved_at_5"] > 0,
        "automatic_negative_control_false_positives_do_not_increase": detector["negative_controls_with_false_positive"] == 0,
    }
    eligible = all(conditions.values())
    decision = {
        "status": "offline_candidate_for_separate_review" if eligible else "do_not_integrate",
        "best_method": best["method"],
        "conditions": conditions,
        "application_changed": False,
        "reason": (
            "O candidato satisfez os critérios exploratórios pré-registrados, mas ainda exige revisão independente antes de qualquer integração."
            if eligible
            else "Nenhum candidato satisfez simultaneamente os critérios exploratórios; não há justificativa para integração."
        ),
    }
    field_counts = Counter(term.field for term in index.terms)
    language_counts = Counter(term.language for term in index.terms)
    concepts_with_pt = {
        term.hpo_id for term in index.terms if term.field == "official_label_pt"
    }
    manifest = {
        "schema_version": "official-term-index-manifest-v1",
        "data_version": index.data_version,
        "scope_root": index.scope_root,
        "scope_root_included": False,
        "phenotype_concepts": len(ontology.phenotypic_abnormality_ids),
        "concepts_with_official_label_pt": len(concepts_with_pt),
        "concepts_without_official_label_pt": len(ontology.phenotypic_abnormality_ids) - len(concepts_with_pt),
        "terms": len(index.terms),
        "terms_by_field": dict(sorted(field_counts.items())),
        "terms_by_language": dict(sorted(language_counts.items())),
        "sources": index.sources,
        "derived_at_runtime_from_versioned_ontology": True,
        "official_dataset_modified": False,
        "builder": "src/hpo_ptbr/official_term_index.py",
        "builder_sha256": sha256(ROOT / "src/hpo_ptbr/official_term_index.py"),
        "ontology_sha256": sha256(ONTOLOGY_PATH),
    }
    summary = {
        "schema_version": "phase2-iteration2-offline-summary-v1",
        "status": "development_exploratory_not_clinically_validated",
        "protocol": PROTOCOL_PATH.relative_to(ROOT).as_posix(),
        "protocol_sha256": sha256(PROTOCOL_PATH),
        "dataset": DATASET_PATH.relative_to(ROOT).as_posix(),
        "dataset_sha256": sha256(DATASET_PATH),
        "baseline_id": baseline["baseline_id"],
        "validation_used": False,
        "holdout_used": False,
        "methods": method_summaries,
        "semantic_method_status": semantic_status,
        "automatic_detector_control": detector,
        "decision": decision,
        "interpretation": "Trechos-ouro isolam linking; resultados não medem detecção de paráfrase, generalização nem desempenho clínico.",
    }
    error_analysis = build_error_analysis(
        all_details,
        ontology,
        str(decision["best_method"]),
    )
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {
        "phase2_iteration2_term_index_manifest.json": manifest,
        "phase2_iteration2_offline_details.json": all_details,
        "phase2_iteration2_offline_summary.json": summary,
        "phase2_iteration2_offline_error_analysis.json": error_analysis,
    }
    for filename, payload in outputs.items():
        (RESULTS_DIR / filename).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    (RESULTS_DIR / "phase2_iteration2_offline_report.md").write_text(
        report(summary),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
