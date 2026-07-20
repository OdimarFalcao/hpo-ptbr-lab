from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hpo_ptbr.reporting import (
    build_comparison_rows,
    load_summary,
    render_comparison_markdown,
    write_comparison_csv,
)


def main() -> None:
    results = ROOT / "data/results"
    rows = build_comparison_rows(
        load_summary(results / "evaluation_summary.csv"),
        load_summary(results / "development_experiment1_summary.csv"),
        load_summary(results / "holdout_experiment1_summary.csv"),
    )
    coverage = json.loads(
        (ROOT / "data/processed/coverage_summary.json").read_text(encoding="utf-8")
    )
    evidence = json.loads(
        (results / "evidence_evaluation_summary.json").read_text(encoding="utf-8")
    )

    write_comparison_csv(results / "comparison_metrics.csv", rows)
    (results / "comparison_report.md").write_text(
        render_comparison_markdown(rows, coverage, evidence), encoding="utf-8"
    )
    print(f"Geradas {len(rows)} linhas em data/results/comparison_metrics.csv")


if __name__ == "__main__":
    main()
