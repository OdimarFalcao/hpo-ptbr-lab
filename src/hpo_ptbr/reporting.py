from __future__ import annotations

import csv
from pathlib import Path

REQUIRED_SUMMARY_COLUMNS = {
    "method",
    "stratum",
    "n",
    "accuracy_at_1",
    "accuracy_at_5",
    "mrr_at_20",
    "latency_mean_ms",
    "invalid_id_rate",
}

DATASET_CONFIGS = (
    {
        "experiment": "Experimento 0",
        "dataset_role": "desenvolvimento exploratório",
        "methods": {"exact", "fuzzy", "bm25"},
        "tuning_allowed": True,
        "claim_scope": "baseline exploratório",
    },
    {
        "experiment": "Experimento 1",
        "dataset_role": "desenvolvimento exploratório",
        "methods": {"semantic", "hybrid"},
        "tuning_allowed": True,
        "claim_scope": "comparação exploratória",
    },
    {
        "experiment": "Experimento 1",
        "dataset_role": "holdout congelado",
        "methods": {"exact", "fuzzy", "bm25", "semantic", "hybrid"},
        "tuning_allowed": False,
        "claim_scope": "avaliação única da sprint",
    },
)


def load_summary(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or not REQUIRED_SUMMARY_COLUMNS.issubset(rows[0]):
        raise ValueError(f"Resumo experimental inválido: {path}")
    return rows


def build_comparison_rows(
    experiment0: list[dict[str, str]],
    development: list[dict[str, str]],
    holdout: list[dict[str, str]],
) -> list[dict[str, object]]:
    sources = (experiment0, development, holdout)
    comparison: list[dict[str, object]] = []
    for rows, config in zip(sources, DATASET_CONFIGS, strict=True):
        selected = [row for row in rows if row["method"] in config["methods"]]
        expected_count = len(config["methods"]) * 4
        if len(selected) != expected_count:
            raise ValueError(
                f"Linhas inesperadas em {config['experiment']} / {config['dataset_role']}: "
                f"esperadas {expected_count}, encontradas {len(selected)}."
            )
        for row in selected:
            comparison.append(
                {
                    "experiment": config["experiment"],
                    "dataset_role": config["dataset_role"],
                    "method": row["method"],
                    "stratum": row["stratum"],
                    "n": int(row["n"]),
                    "accuracy_at_1": float(row["accuracy_at_1"]),
                    "accuracy_at_5": float(row["accuracy_at_5"]),
                    "mrr_at_20": float(row["mrr_at_20"]),
                    "latency_mean_ms": float(row["latency_mean_ms"]),
                    "invalid_id_rate": float(row["invalid_id_rate"]),
                    "tuning_allowed": config["tuning_allowed"],
                    "claim_scope": config["claim_scope"],
                }
            )
    return sorted(
        comparison,
        key=lambda row: (
            row["experiment"],
            row["dataset_role"],
            row["stratum"],
            row["method"],
        ),
    )


def _percent(value: object) -> str:
    return f"{float(value) * 100:.2f}%".replace(".", ",")


def _metric_rows(
    rows: list[dict[str, object]], dataset_role: str, stratum: str
) -> list[dict[str, object]]:
    return [
        row
        for row in rows
        if row["dataset_role"] == dataset_role and row["stratum"] == stratum
    ]


def render_comparison_markdown(
    rows: list[dict[str, object]],
    coverage: dict[str, object],
    evidence: dict[str, object],
) -> str:
    general_dev = _metric_rows(rows, "desenvolvimento exploratório", "ALL")
    paraphrase_dev = _metric_rows(
        rows, "desenvolvimento exploratório", "clinical_paraphrase"
    )
    general_holdout = _metric_rows(rows, "holdout congelado", "ALL")
    paraphrase_holdout = _metric_rows(
        rows, "holdout congelado", "clinical_paraphrase"
    )

    lines = [
        "# Resultados consolidados — HPO-PTBR Lab",
        "",
        "Gerado automaticamente por `python scripts/build_comparison_report.py`.",
        "",
        "## Snapshot e cobertura",
        "",
        f"- Versão: `{coverage['data_version']}`.",
        f"- Termos HPO ativos: {int(coverage['active_terms']):,}.".replace(",", "."),
        f"- Rótulos portugueses: {int(coverage['translated_labels_pt']):,}.".replace(",", "."),
        f"- Cobertura de rótulos: {str(coverage['label_coverage_percent']).replace('.', ',')}%.",
        "",
        "## Desenvolvimento exploratório",
        "",
        "Os 30 casos já influenciaram decisões e não medem generalização.",
        "",
        "| Método | Acc@1 geral | Acc@5 geral | Acc@1 paráfrases | Acc@5 paráfrases |",
        "|---|---:|---:|---:|---:|",
    ]
    dev_by_method = {
        row["method"]: row for row in general_dev
    }
    dev_paraphrase_by_method = {
        row["method"]: row for row in paraphrase_dev
    }
    for method in ("exact", "fuzzy", "bm25", "semantic", "hybrid"):
        general = dev_by_method[method]
        paraphrase = dev_paraphrase_by_method[method]
        lines.append(
            f"| {method} | {_percent(general['accuracy_at_1'])} | "
            f"{_percent(general['accuracy_at_5'])} | "
            f"{_percent(paraphrase['accuracy_at_1'])} | "
            f"{_percent(paraphrase['accuracy_at_5'])} |"
        )

    lines.extend(
        [
            "",
            "## Holdout congelado",
            "",
            "Execução única. Estes resultados não devem ser reutilizados para ajuste.",
            "",
            "| Método | Acc@1 geral | Acc@5 geral | Acc@1 paráfrases | Acc@5 paráfrases |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    holdout_by_method = {row["method"]: row for row in general_holdout}
    holdout_paraphrase_by_method = {
        row["method"]: row for row in paraphrase_holdout
    }
    for method in ("exact", "fuzzy", "bm25", "semantic", "hybrid"):
        general = holdout_by_method[method]
        paraphrase = holdout_paraphrase_by_method[method]
        lines.append(
            f"| {method} | {_percent(general['accuracy_at_1'])} | "
            f"{_percent(general['accuracy_at_5'])} | "
            f"{_percent(paraphrase['accuracy_at_1'])} | "
            f"{_percent(paraphrase['accuracy_at_5'])} |"
        )

    orthographic_holdout = _metric_rows(
        rows, "holdout congelado", "orthographic_variation"
    )
    orthographic_by_method = {row["method"]: row for row in orthographic_holdout}
    lines.extend(
        [
            "",
            "## Critério de promoção do híbrido",
            "",
            f"- Paráfrases Acc@5: híbrido {_percent(holdout_paraphrase_by_method['hybrid']['accuracy_at_5'])}; melhor individual {_percent(max(holdout_paraphrase_by_method[name]['accuracy_at_5'] for name in ('fuzzy', 'bm25', 'semantic')))}.",
            f"- Rótulos oficiais Acc@1 do híbrido: {_percent(next(row['accuracy_at_1'] for row in rows if row['dataset_role'] == 'holdout congelado' and row['stratum'] == 'official_label' and row['method'] == 'hybrid'))}.",
            f"- Variações ortográficas Acc@1: híbrido {_percent(orthographic_by_method['hybrid']['accuracy_at_1'])}; fuzzy {_percent(orthographic_by_method['fuzzy']['accuracy_at_1'])}.",
            "- Decisão: não promover. O híbrido perdeu dois casos ortográficos, acima do limite pré-registrado de um.",
            "",
            "## Sanity check da descrição sintética",
            "",
            f"- Casos: {evidence['n_cases']}; menções detectáveis: {evidence['n_detectable_mentions']}; falha conhecida: {evidence['n_known_miss_mentions']}.",
            f"- Recall de trecho exato: {_percent(evidence['exact_span_recall'])}; HPO Acc@1: {_percent(evidence['hpo_accuracy_at_1'])}; IDs inválidos: {_percent(evidence['invalid_id_rate'])}.",
            "- Escopo: verificação funcional construída no desenvolvimento; não é benchmark, holdout ou evidência clínica.",
            "",
            "## Separação obrigatória",
            "",
            "| Bloco | Pode ajustar? | Uso correto |",
            "|---|---|---|",
            "| Desenvolvimento exploratório | Sim | Construção e diagnóstico de métodos |",
            "| Holdout congelado | Não | Avaliação única da sprint |",
            "| Sanity check sintético | Sim | Verificação funcional da interface |",
            "",
        ]
    )
    return "\n".join(lines)
