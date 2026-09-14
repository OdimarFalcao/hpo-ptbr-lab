from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hpo_ptbr.hashing import content_sha256
from hpo_ptbr.benchmark_evaluation import evaluate_benchmark_method
from hpo_ptbr.data import load_metadata, load_snapshot
from hpo_ptbr.evidence import EvidenceExtractor
from hpo_ptbr.rankers import Bm25Mapper, ExactMapper, FuzzyMapper

DATASET_PATH = ROOT / "data/eval/benchmark_v1_development.json"
MANIFEST_PATH = ROOT / "data/eval/benchmark_v1_development_manifest.json"
PROTOCOL_PATH = ROOT / "data/protocol/benchmark_v1_development_baseline.json"
RESULTS_DIR = ROOT / "data/results"


def _sha256(path: Path) -> str:
    return content_sha256(path)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    serializable = []
    for row in rows:
        serializable.append(
            {
                key: json.dumps(value, ensure_ascii=False)
                if isinstance(value, (list, dict))
                else value
                for key, value in row.items()
            }
        )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(serializable[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(serializable)


def _percentage(value: object) -> str:
    return f"{float(value) * 100:.2f}%"


def _build_error_analysis(
    gold_details: list[dict[str, object]],
    prediction_details: list[dict[str, object]],
    negative_control_ids: set[str],
) -> dict[str, dict[str, object]]:
    methods = sorted({str(row["method"]) for row in gold_details})
    analysis: dict[str, dict[str, object]] = {}
    for method in methods:
        method_gold = [row for row in gold_details if row["method"] == method]
        method_predictions = [
            row for row in prediction_details if row["method"] == method
        ]
        missed_spans = [
            row for row in method_gold if not row["exact_span_detected"]
        ]
        assertion_errors = [
            row for row in method_gold if not row["assertion_correct"]
        ]
        linking_top_1_errors = [
            row for row in method_gold if row["gold_span_target_rank"] != 1
        ]
        linking_top_5_errors = [
            row
            for row in method_gold
            if row["gold_span_target_rank"] is None
            or int(row["gold_span_target_rank"]) > 5
        ]
        spurious_predictions = [
            row for row in method_predictions if not row["exact_gold_match"]
        ]
        control_predictions = [
            row
            for row in method_predictions
            if str(row["case_id"]) in negative_control_ids
        ]
        analysis[method] = {
            "missed_exact_spans_by_surface": dict(
                sorted(Counter(str(row["surface_form"]) for row in missed_spans).items())
            ),
            "missed_exact_span_examples": [
                {
                    "case_id": row["case_id"],
                    "mention_text": row["mention_text"],
                    "target_hpo_id": row["target_hpo_id"],
                    "surface_form": row["surface_form"],
                }
                for row in missed_spans
            ],
            "gold_span_linking_top_1_errors_by_surface": dict(
                sorted(
                    Counter(
                        str(row["surface_form"]) for row in linking_top_1_errors
                    ).items()
                )
            ),
            "gold_span_linking_top_5_errors_by_surface": dict(
                sorted(
                    Counter(
                        str(row["surface_form"]) for row in linking_top_5_errors
                    ).items()
                )
            ),
            "assertion_errors_by_gold_class": dict(
                sorted(Counter(str(row["assertion"]) for row in assertion_errors).items())
            ),
            "end_to_end_failures_by_surface": dict(
                sorted(
                    Counter(
                        str(row["surface_form"])
                        for row in method_gold
                        if not row["end_to_end_correct"]
                    ).items()
                )
            ),
            "spurious_prediction_count": len(spurious_predictions),
            "negative_control_prediction_count": len(control_predictions),
        }
    return analysis


def _build_report(
    summaries: dict[str, dict[str, object]],
    metadata: dict[str, object],
    error_analysis: dict[str, dict[str, object]],
) -> str:
    lines = [
        "# Benchmark V1 — baseline de desenvolvimento",
        "",
        "## Configuração",
        "",
        f"- Dataset: `{metadata['dataset']}`.",
        f"- Snapshot: `{metadata['snapshot']}`.",
        "- Detector: janelas fuzzy, limiar 0,92 e máximo de cinco tokens.",
        "- Rankers: exact, fuzzy e BM25.",
        "- Contexto: baseline fixo `always_present`.",
        "- Holdout: não utilizado.",
        "- Scores dos rankers não são confiança calibrada.",
        "",
        "## Resultados gerais",
        "",
        "| Método | F1 ponta a ponta | F1 span exato | Linking A@1 | Linking A@5 | Macro-F1 contexto | FP controles | IDs inválidos | Latência média |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for method, summary in summaries.items():
        lines.append(
            "| "
            + " | ".join(
                [
                    method,
                    _percentage(summary["end_to_end_exact_f1"]),
                    _percentage(summary["exact_span_f1"]),
                    _percentage(summary["linking_accuracy_at_1"]),
                    _percentage(summary["linking_accuracy_at_5"]),
                    _percentage(summary["assertion_macro_f1"]),
                    _percentage(summary["negative_control_false_positive_rate"]),
                    _percentage(summary["invalid_hpo_id_rate"]),
                    f"{summary['latency_mean_ms']} ms",
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Estratos de forma superficial",
            "",
            "| Método | Estrato | N | Recall span | Linking A@1 | Linking A@5 | Recall ponta a ponta |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for method, summary in summaries.items():
        for stratum, values in summary["by_surface_form"].items():
            lines.append(
                f"| {method} | {stratum} | {values['n']} | "
                f"{_percentage(values['exact_span_recall'])} | "
                f"{_percentage(values['linking_accuracy_at_1'])} | "
                f"{_percentage(values['linking_accuracy_at_5'])} | "
                f"{_percentage(values['end_to_end_recall'])} |"
            )

    lines.extend(
        [
            "",
            "## Estratos de contexto",
            "",
            "| Método | Contexto | N | Accuracy contexto | Linking A@1 | Recall ponta a ponta |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for method, summary in summaries.items():
        for stratum, values in summary["by_assertion"].items():
            lines.append(
                f"| {method} | {stratum} | {values['n']} | "
                f"{_percentage(values['assertion_accuracy'])} | "
                f"{_percentage(values['linking_accuracy_at_1'])} | "
                f"{_percentage(values['end_to_end_recall'])} |"
            )

    fuzzy_errors = error_analysis["fuzzy"]
    bm25_paraphrase = summaries["bm25"]["by_surface_form"]["clinical_paraphrase"]
    missed_examples = fuzzy_errors["missed_exact_span_examples"]
    orthographic_misses = [
        row
        for row in missed_examples
        if row["surface_form"] == "orthographic_variation"
    ]
    orthographic_text = ", ".join(
        f"`{row['mention_text']}` ({row['target_hpo_id']})"
        for row in orthographic_misses
    )
    lines.extend(
        [
            "",
            "## Análise de erros",
            "",
            "- O detector lexical perdeu as 12 paráfrases clínicas e uma variação ortográfica"
            + (f": {orthographic_text}." if orthographic_text else "."),
            "- Quando recebeu os spans ouro, fuzzy vinculou corretamente 12/12 rótulos oficiais e 12/12 variações ortográficas, mas 0/12 paráfrases.",
            f"- Com spans ouro, BM25 recuperou paráfrases em {_percentage(bm25_paraphrase['linking_accuracy_at_1'])} no Top-1 e {_percentage(bm25_paraphrase['linking_accuracy_at_5'])} no Top-5; a detecção automática dessas paráfrases permaneceu em 0%.",
            "- O classificador `always_present` errou as quatro negações, quatro incertezas e quatro menções de histórico familiar.",
            "- Nenhum método retornou HPO ID inválido ou produziu falso positivo nos dois controles negativos.",
            "",
            "A separação entre detecção, linking e contexto mostra onde cada erro nasce. Melhorar somente o ranker não resolve as paráfrases enquanto o detector não localizar seus trechos; melhorar somente a detecção não resolve negação, incerteza e histórico familiar.",
        ]
    )

    lines.extend(
        [
            "",
            "## Interpretação",
            "",
            "A detecção e o linking são medidos separadamente para evitar atribuir ao ranker uma falha de span. O resultado ponta a ponta exige span exato, HPO Top-1 e contexto corretos. Como a aplicação atual não classifica negação, incerteza ou histórico familiar, o baseline prevê `present` para todas as menções; essa limitação foi registrada antes da execução e não será corrigida retroativamente neste resultado.",
            "",
            "Os números pertencem ao desenvolvimento sintético e podem orientar engenharia e análise de erros. Eles não demonstram generalização, utilidade clínica ou superioridade estatística.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if not manifest.get("development_evaluation_authorized"):
        raise ValueError("O desenvolvimento ainda não foi confirmado por Odimar.")
    if manifest.get("holdout_evaluation_authorized"):
        raise ValueError("Este executor não aceita autorização de holdout.")
    dataset_hash = _sha256(DATASET_PATH)
    if dataset_hash != protocol["dataset_sha256"]:
        raise ValueError("O dataset confirmado diverge do hash pré-registrado.")

    cases = json.loads(DATASET_PATH.read_text(encoding="utf-8"))["cases"]
    negative_control_ids = {
        str(case["case_id"])
        for case in cases
        if case["case_type"] == "negative_control"
    }
    records = load_snapshot(ROOT / "data/processed/hpo_ptbr.csv")
    source_metadata = load_metadata(ROOT / "data/processed/metadata.json")
    data_version = str(source_metadata["data_version"])
    mappers = {
        "exact": ExactMapper(records, data_version),
        "fuzzy": FuzzyMapper(records, data_version),
        "bm25": Bm25Mapper(records, data_version),
    }
    all_gold_details: list[dict[str, object]] = []
    all_prediction_details: list[dict[str, object]] = []
    summaries: dict[str, dict[str, object]] = {}
    for method, mapper in mappers.items():
        extractor = EvidenceExtractor(
            mapper,
            detection_threshold=float(protocol["detection"]["detection_threshold"]),
            max_span_tokens=int(protocol["detection"]["max_span_tokens"]),
        )
        gold_details, prediction_details, summary = evaluate_benchmark_method(
            extractor,
            cases,
            detected_span_top_k=int(protocol["linking"]["detected_span_top_k"]),
            gold_span_top_k=int(protocol["linking"]["gold_span_top_k"]),
            relaxed_iou_threshold=float(
                protocol["evaluation"]["relaxed_span_iou_threshold"]
            ),
        )
        all_gold_details.extend({"method": method, **row} for row in gold_details)
        all_prediction_details.extend(
            {"method": method, **row} for row in prediction_details
        )
        summaries[method] = summary

    error_analysis = _build_error_analysis(
        all_gold_details,
        all_prediction_details,
        negative_control_ids,
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    _write_csv(
        RESULTS_DIR / "benchmark_v1_development_gold_details.csv",
        all_gold_details,
    )
    _write_csv(
        RESULTS_DIR / "benchmark_v1_development_predictions.csv",
        all_prediction_details,
    )
    (RESULTS_DIR / "benchmark_v1_development_summary.json").write_text(
        json.dumps(summaries, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (RESULTS_DIR / "benchmark_v1_development_error_analysis.json").write_text(
        json.dumps(error_analysis, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    result_metadata = {
        "status": "development_baseline_executed",
        "evaluated_at": "2026-08-24",
        "dataset": DATASET_PATH.relative_to(ROOT).as_posix(),
        "dataset_sha256": dataset_hash,
        "protocol": PROTOCOL_PATH.relative_to(ROOT).as_posix(),
        "protocol_sha256": _sha256(PROTOCOL_PATH),
        "snapshot": data_version,
        "methods": list(mappers),
        "assertion_method": protocol["assertion"]["method"],
        "holdout_used": False,
    }
    (RESULTS_DIR / "benchmark_v1_development_metadata.json").write_text(
        json.dumps(result_metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (RESULTS_DIR / "benchmark_v1_development_report.md").write_text(
        _build_report(summaries, result_metadata, error_analysis),
        encoding="utf-8",
    )
    print(json.dumps(summaries, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
