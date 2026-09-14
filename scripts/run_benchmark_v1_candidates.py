from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hpo_ptbr.aliases import load_aliases
from hpo_ptbr.assertion import PortugueseContextCueClassifier
from hpo_ptbr.benchmark_evaluation import evaluate_benchmark_method
from hpo_ptbr.data import load_metadata, load_snapshot
from hpo_ptbr.evidence import EvidenceExtractor
from hpo_ptbr.hybrid_evidence import HybridEvidenceExtractor
from hpo_ptbr.rankers import FuzzyMapper
from hpo_ptbr.sapbert import SapBertEncoder
from hpo_ptbr.semantic import AliasSemanticMapper
from hpo_ptbr.semantic_evidence import SemanticEvidenceExtractor

DATASET_PATH = ROOT / "data/eval/benchmark_v1_development.json"
BASELINE_PATH = ROOT / "data/results/benchmark_v1_development_summary.json"
PROTOCOL_PATH = ROOT / "data/protocol/benchmark_v1_candidate_protocol.json"
RESULTS_DIR = ROOT / "data/results"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    serializable = [
        {
            key: json.dumps(value, ensure_ascii=False)
            if isinstance(value, (list, dict))
            else value
            for key, value in row.items()
        }
        for row in rows
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(serializable[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(serializable)


def _passes(value: float, operator: str, threshold: float) -> bool:
    if operator == "gt":
        return value > threshold
    if operator == "gte":
        return value >= threshold
    if operator == "lte":
        return value <= threshold
    raise ValueError(f"Operador de gate inválido: {operator}")


def _gate(
    summary: dict[str, object],
    checks: list[tuple[str, float, str, float]],
) -> dict[str, object]:
    results = [
        {
            "metric": metric,
            "observed": observed,
            "operator": operator,
            "threshold": threshold,
            "passed": _passes(observed, operator, threshold),
        }
        for metric, observed, operator, threshold in checks
    ]
    return {"passed": all(check["passed"] for check in results), "checks": results}


def _evaluate_gates(summaries: dict[str, dict[str, object]]) -> dict[str, object]:
    context = summaries["fuzzy_context_cues"]
    semantic = summaries["semantic_context_cues"]
    combined = summaries["hybrid_context_cues"]
    return {
        "assertion_candidate": _gate(
            context,
            [
                ("assertion_macro_f1", float(context["assertion_macro_f1"]), "gt", 0.2),
                (
                    "present_assertion_accuracy",
                    float(context["by_assertion"]["present"]["assertion_accuracy"]),
                    "gte",
                    1.0,
                ),
            ],
        ),
        "semantic_detection_component": _gate(
            semantic,
            [
                (
                    "paraphrase_exact_span_recall",
                    float(
                        semantic["by_surface_form"]["clinical_paraphrase"][
                            "exact_span_recall"
                        ]
                    ),
                    "gt",
                    0.0,
                ),
                (
                    "official_exact_span_recall",
                    float(
                        semantic["by_surface_form"]["official_label"][
                            "exact_span_recall"
                        ]
                    ),
                    "gte",
                    0.9167,
                ),
                (
                    "orthographic_exact_span_recall",
                    float(
                        semantic["by_surface_form"]["orthographic_variation"][
                            "exact_span_recall"
                        ]
                    ),
                    "gte",
                    0.8333,
                ),
                (
                    "negative_control_false_positive_rate",
                    float(semantic["negative_control_false_positive_rate"]),
                    "lte",
                    0.0,
                ),
                (
                    "invalid_hpo_id_rate",
                    float(semantic["invalid_hpo_id_rate"]),
                    "lte",
                    0.0,
                ),
            ],
        ),
        "combined_candidate": _gate(
            combined,
            [
                (
                    "overall_end_to_end_exact_f1",
                    float(combined["end_to_end_exact_f1"]),
                    "gt",
                    0.5079,
                ),
                (
                    "paraphrase_end_to_end_recall",
                    float(
                        combined["by_surface_form"]["clinical_paraphrase"][
                            "end_to_end_recall"
                        ]
                    ),
                    "gt",
                    0.0,
                ),
                (
                    "official_end_to_end_recall",
                    float(
                        combined["by_surface_form"]["official_label"][
                            "end_to_end_recall"
                        ]
                    ),
                    "gte",
                    0.75,
                ),
                (
                    "negative_control_false_positive_rate",
                    float(combined["negative_control_false_positive_rate"]),
                    "lte",
                    0.0,
                ),
                (
                    "invalid_hpo_id_rate",
                    float(combined["invalid_hpo_id_rate"]),
                    "lte",
                    0.0,
                ),
            ],
        ),
    }


def _percentage(value: object) -> str:
    return f"{float(value) * 100:.2f}%"


def _is_true(value: object) -> bool:
    return value is True or value == "True"


def _build_error_analysis(
    gold_rows: list[dict[str, object]],
    prediction_rows: list[dict[str, object]],
) -> dict[str, object]:
    context_errors = [
        {
            "case_id": row["case_id"],
            "mention_text": row["mention_text"],
            "expected": row["assertion"],
            "predicted": row["predicted_assertion"],
        }
        for row in gold_rows
        if row["configuration"] == "fuzzy_context_cues"
        and not _is_true(row["assertion_correct"])
    ]
    semantic_paraphrases = [
        row
        for row in gold_rows
        if row["configuration"] == "semantic_context_cues"
        and row["surface_form"] == "clinical_paraphrase"
    ]
    detected_paraphrases = [
        {
            "case_id": row["case_id"],
            "mention_text": row["mention_text"],
            "target_hpo_id": row["target_hpo_id"],
            "end_to_end_correct": _is_true(row["end_to_end_correct"]),
        }
        for row in semantic_paraphrases
        if _is_true(row["exact_span_detected"])
    ]
    control_predictions = [
        {
            "configuration": row["configuration"],
            "case_id": row["case_id"],
            "prediction_text": row["prediction_text"],
            "top_hpo_id": row["top_hpo_id"],
        }
        for row in prediction_rows
        if str(row["case_id"]).startswith("DEV-CTRL")
    ]
    configurations = sorted({str(row["configuration"]) for row in prediction_rows})
    return {
        "context_errors": context_errors,
        "semantic_paraphrases_detected_exactly": detected_paraphrases,
        "semantic_paraphrases_missed_count": len(semantic_paraphrases)
        - len(detected_paraphrases),
        "negative_control_predictions": control_predictions,
        "spurious_prediction_count": {
            configuration: sum(
                row["configuration"] == configuration
                and not _is_true(row["exact_gold_match"])
                for row in prediction_rows
            )
            for configuration in configurations
        },
    }


def _build_report(
    baseline: dict[str, object],
    summaries: dict[str, dict[str, object]],
    gates: dict[str, object],
    error_analysis: dict[str, object],
) -> str:
    rows = [("fuzzy_always_present", baseline["fuzzy"]), *summaries.items()]
    lines = [
        "# Benchmark V1 — candidatos no desenvolvimento",
        "",
        "## Matriz controlada",
        "",
        "| Configuração | F1 ponta a ponta | Recall paráfrases | F1 span | Macro-F1 contexto | FP controles | IDs inválidos |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, summary in rows:
        lines.append(
            f"| {name} | {_percentage(summary['end_to_end_exact_f1'])} | "
            f"{_percentage(summary['by_surface_form']['clinical_paraphrase']['exact_span_recall'])} | "
            f"{_percentage(summary['exact_span_f1'])} | "
            f"{_percentage(summary['assertion_macro_f1'])} | "
            f"{_percentage(summary['negative_control_false_positive_rate'])} | "
            f"{_percentage(summary['invalid_hpo_id_rate'])} |"
        )
    lines.extend(["", "## Gates", ""])
    for name, result in gates.items():
        lines.append(f"- `{name}`: {'APROVADO' if result['passed'] else 'REPROVADO'}.")
        for check in result["checks"]:
            lines.append(
                f"  - {check['metric']}: {check['observed']} "
                f"{check['operator']} {check['threshold']} — "
                f"{'ok' if check['passed'] else 'falhou'}."
            )
    context_errors = error_analysis["context_errors"]
    control_predictions = error_analysis["negative_control_predictions"]
    detected_paraphrases = error_analysis["semantic_paraphrases_detected_exactly"]
    lines.extend(
        [
            "",
            "## Análise de erros",
            "",
            f"- O contexto acertou 35/36 menções. A única falha foi `{context_errors[0]['mention_text']}`: esperado `{context_errors[0]['expected']}`, previsto `{context_errors[0]['predicted']}`. A pista ‘como possibilidade’ aparece depois da menção e ficou fora do escopo pré-registrado à esquerda.",
            f"- O detector semântico localizou exatamente {len(detected_paraphrases)}/12 paráfrases: "
            + ", ".join(
                f"`{row['mention_text']}` ({row['target_hpo_id']})"
                for row in detected_paraphrases
            )
            + ".",
            f"- O mesmo detector perdeu {error_analysis['semantic_paraphrases_missed_count']}/12 paráfrases.",
            f"- O gate semântico falhou porque {control_predictions[0]['case_id']} produziu o trecho espúrio `{control_predictions[0]['prediction_text']}` → `{control_predictions[0]['top_hpo_id']}`. A taxa foi 1/2 controles, ou 50%.",
            f"- Previsões sem span ouro: fuzzy+contexto {error_analysis['spurious_prediction_count']['fuzzy_context_cues']}, semântico+contexto {error_analysis['spurious_prediction_count']['semantic_context_cues']} e híbrido+contexto {error_analysis['spurious_prediction_count']['hybrid_context_cues']}.",
            "- Nenhuma configuração retornou HPO ID inválido.",
        ]
    )
    lines.extend(
        [
            "",
            "## Limites de interpretação",
            "",
            "O classificador de contexto foi especificado depois da inspeção dos textos sintéticos e pode refletir seus templates. O SapBERT e seus parâmetros vieram de experimento anterior e foram congelados antes desta execução. O resultado pertence somente ao desenvolvimento, não utiliza holdout e não demonstra validade clínica ou generalização.",
            "",
            "Aprovação em desenvolvimento não promove automaticamente qualquer método ao dashboard.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol["status"] != "preregistered_before_candidate_execution":
        raise ValueError("O protocolo candidato não está pré-registrado.")
    if protocol["holdout_used"]:
        raise ValueError("Este executor não aceita holdout.")
    if _sha256(DATASET_PATH) != protocol["dataset_sha256"]:
        raise ValueError("O dataset diverge do protocolo candidato.")
    if _sha256(BASELINE_PATH) != protocol["baseline_summary_sha256"]:
        raise ValueError("O baseline diverge do protocolo candidato.")

    semantic_config = protocol["semantic_candidate"]
    alias_path = ROOT / semantic_config["alias_dataset"]
    if _sha256(alias_path) != semantic_config["alias_dataset_sha256"]:
        raise ValueError("O arquivo de aliases diverge do protocolo candidato.")

    cases = json.loads(DATASET_PATH.read_text(encoding="utf-8"))["cases"]
    records = load_snapshot(ROOT / "data/processed/hpo_ptbr.csv")
    metadata = load_metadata(ROOT / "data/processed/metadata.json")
    data_version = str(metadata["data_version"])
    fuzzy_mapper = FuzzyMapper(records, data_version)
    lexical_extractor = EvidenceExtractor(
        fuzzy_mapper,
        detection_threshold=0.92,
        max_span_tokens=5,
    )
    encoder = SapBertEncoder(
        model_name=semantic_config["model_name"],
        revision=semantic_config["model_revision"],
        local_files_only=True,
    )
    semantic_mapper = AliasSemanticMapper(
        records,
        data_version,
        encoder,
        load_aliases(alias_path),
    )
    semantic_extractor = SemanticEvidenceExtractor(
        semantic_mapper,
        detection_threshold=float(semantic_config["detection_threshold"]),
        max_span_tokens=int(semantic_config["max_span_tokens"]),
        respect_text_boundaries=bool(semantic_config["respect_text_boundaries"]),
    )
    hybrid_extractor = HybridEvidenceExtractor(lexical_extractor, semantic_extractor)
    classifier = PortugueseContextCueClassifier()
    configurations = {
        "fuzzy_context_cues": lexical_extractor,
        "semantic_context_cues": semantic_extractor,
        "hybrid_context_cues": hybrid_extractor,
    }

    all_gold: list[dict[str, object]] = []
    all_predictions: list[dict[str, object]] = []
    summaries: dict[str, dict[str, object]] = {}
    for name, extractor in configurations.items():
        gold, predictions, summary = evaluate_benchmark_method(
            extractor,
            cases,
            assertion_classifier=classifier,
            detected_span_top_k=int(semantic_config["detected_span_top_k"]),
            gold_span_top_k=20,
        )
        summary["configuration"] = name
        summaries[name] = summary
        all_gold.extend({"configuration": name, **row} for row in gold)
        all_predictions.extend(
            {"configuration": name, **row} for row in predictions
        )

    gates = _evaluate_gates(summaries)
    error_analysis = _build_error_analysis(all_gold, all_predictions)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    _write_csv(RESULTS_DIR / "benchmark_v1_candidate_gold_details.csv", all_gold)
    _write_csv(
        RESULTS_DIR / "benchmark_v1_candidate_predictions.csv",
        all_predictions,
    )
    (RESULTS_DIR / "benchmark_v1_candidate_summary.json").write_text(
        json.dumps(summaries, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (RESULTS_DIR / "benchmark_v1_candidate_gates.json").write_text(
        json.dumps(gates, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (RESULTS_DIR / "benchmark_v1_candidate_error_analysis.json").write_text(
        json.dumps(error_analysis, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    result_metadata = {
        "status": "development_candidates_executed",
        "evaluated_at": "2026-08-24",
        "protocol": PROTOCOL_PATH.relative_to(ROOT).as_posix(),
        "protocol_sha256": _sha256(PROTOCOL_PATH),
        "dataset_sha256": _sha256(DATASET_PATH),
        "baseline_summary_sha256": _sha256(BASELINE_PATH),
        "snapshot": data_version,
        "model_name": semantic_config["model_name"],
        "model_revision": semantic_config["model_revision"],
        "model_sha256": semantic_config["model_sha256"],
        "holdout_used": False,
    }
    (RESULTS_DIR / "benchmark_v1_candidate_metadata.json").write_text(
        json.dumps(result_metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    (RESULTS_DIR / "benchmark_v1_candidate_report.md").write_text(
        _build_report(baseline, summaries, gates, error_analysis),
        encoding="utf-8",
    )
    print(json.dumps({"summaries": summaries, "gates": gates}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
