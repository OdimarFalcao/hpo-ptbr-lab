from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

from .rankers import BaseMapper


def load_cases(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        cases = list(csv.DictReader(handle))
    required = {"case_id", "query_pt", "target_hpo_id", "stratum", "provenance"}
    if not cases or not required.issubset(cases[0]):
        raise ValueError(f"Arquivo piloto inválido; colunas obrigatórias: {sorted(required)}")
    return cases


def _summarize(rows: list[dict[str, object]]) -> dict[str, float | int]:
    total = len(rows)
    reciprocal_ranks = [1 / int(row["target_rank"]) if row["target_rank"] else 0.0 for row in rows]
    latencies = [float(row["latency_ms"]) for row in rows]
    return {
        "n": total,
        "accuracy_at_1": round(sum(row["target_rank"] == 1 for row in rows) / total, 4),
        "accuracy_at_5": round(
            sum(bool(row["target_rank"]) and int(row["target_rank"]) <= 5 for row in rows) / total,
            4,
        ),
        "mrr_at_20": round(statistics.fmean(reciprocal_ranks), 4),
        "latency_mean_ms": round(statistics.fmean(latencies), 3),
    }


def evaluate_cases(
    mappers: dict[str, BaseMapper],
    cases: list[dict[str, str]],
    top_k: int = 20,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    details: list[dict[str, object]] = []
    for method, mapper in mappers.items():
        for case in cases:
            result = mapper.map(case["query_pt"], top_k=top_k)
            target_rank = next(
                (candidate.rank for candidate in result.candidates if candidate.hpo_id == case["target_hpo_id"]),
                None,
            )
            details.append(
                {
                    "method": method,
                    "case_id": case["case_id"],
                    "stratum": case["stratum"],
                    "query_pt": case["query_pt"],
                    "target_hpo_id": case["target_hpo_id"],
                    "target_rank": target_rank,
                    "latency_ms": result.latency_ms,
                    "top_hpo_ids": json.dumps(
                        [candidate.hpo_id for candidate in result.candidates[:5]], ensure_ascii=False
                    ),
                }
            )

    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in details:
        grouped[(str(row["method"]), str(row["stratum"]))].append(row)
        grouped[(str(row["method"]), "ALL")].append(row)

    summary: list[dict[str, object]] = []
    for (method, stratum), rows in sorted(grouped.items()):
        summary.append({"method": method, "stratum": stratum, **_summarize(rows)})
    return details, summary
