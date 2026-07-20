import json
from pathlib import Path

from hpo_ptbr.reporting import (
    build_comparison_rows,
    load_summary,
    render_comparison_markdown,
    write_comparison_csv,
)


def test_consolidates_without_mixing_dataset_roles():
    root = Path(__file__).resolve().parents[1]
    results = root / "data/results"
    rows = build_comparison_rows(
        load_summary(results / "evaluation_summary.csv"),
        load_summary(results / "development_experiment1_summary.csv"),
        load_summary(results / "holdout_experiment1_summary.csv"),
    )

    assert len(rows) == 40
    experiment0_methods = {
        row["method"] for row in rows if row["experiment"] == "Experimento 0"
    }
    development_increment_methods = {
        row["method"]
        for row in rows
        if row["experiment"] == "Experimento 1"
        and row["dataset_role"] == "desenvolvimento exploratório"
    }
    holdout_rows = [row for row in rows if row["dataset_role"] == "holdout congelado"]

    assert experiment0_methods == {"exact", "fuzzy", "bm25"}
    assert development_increment_methods == {"semantic", "hybrid"}
    assert {row["method"] for row in holdout_rows} == {
        "exact",
        "fuzzy",
        "bm25",
        "semantic",
        "hybrid",
    }
    assert all(not row["tuning_allowed"] for row in holdout_rows)


def test_report_separates_holdout_and_sanity_check():
    root = Path(__file__).resolve().parents[1]
    results = root / "data/results"
    rows = build_comparison_rows(
        load_summary(results / "evaluation_summary.csv"),
        load_summary(results / "development_experiment1_summary.csv"),
        load_summary(results / "holdout_experiment1_summary.csv"),
    )
    coverage = json.loads(
        (root / "data/processed/coverage_summary.json").read_text(encoding="utf-8")
    )
    evidence = json.loads(
        (results / "evidence_evaluation_summary.json").read_text(encoding="utf-8")
    )

    report = render_comparison_markdown(rows, coverage, evidence)

    assert "não devem ser reutilizados para ajuste" in report
    assert "não é benchmark, holdout ou evidência clínica" in report
    assert "Decisão: não promover" in report


def test_comparison_csv_uses_cross_platform_line_endings(tmp_path):
    output = tmp_path / "comparison.csv"

    write_comparison_csv(output, [{"method": "exact", "accuracy_at_1": 1.0}])

    content = output.read_bytes()
    assert b"\r\n" not in content
    assert content.endswith(b"\n")
