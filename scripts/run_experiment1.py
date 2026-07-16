from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hpo_ptbr.data import load_metadata, load_snapshot
from hpo_ptbr.evaluation import evaluate_cases, load_cases
from hpo_ptbr.experiment import promotion_gate, result_fingerprint, verify_frozen_holdout
from hpo_ptbr.hybrid import HybridMapper, RRF_K, SOURCE_TOP_K
from hpo_ptbr.rankers import Bm25Mapper, ExactMapper, FuzzyMapper
from hpo_ptbr.semantic import (
    DEFAULT_MODEL_NAME,
    DEFAULT_MODEL_REVISION,
    SemanticMapper,
    load_default_encoder,
)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def git_state() -> tuple[str, bool]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    return commit, dirty


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa o protocolo do Experimento 1.")
    parser.add_argument("--dataset", choices=("development", "holdout"), required=True)
    parser.add_argument("--confirm-holdout", action="store_true")
    args = parser.parse_args()

    commit, dirty = git_state()
    if args.dataset == "holdout":
        if not args.confirm_holdout:
            raise ValueError("Use --confirm-holdout para autorizar a execução única do holdout.")
        if dirty:
            raise ValueError("O repositório deve estar limpo antes de executar o holdout.")
        cases_path = ROOT / "data/eval/holdout_cases.csv"
        manifest_path = ROOT / "data/eval/holdout_manifest.json"
        holdout_manifest = verify_frozen_holdout(cases_path, manifest_path)
        prefix = "holdout_experiment1"
    else:
        cases_path = ROOT / "data/eval/pilot_cases.csv"
        holdout_manifest = None
        prefix = "development_experiment1"

    results_dir = ROOT / "data/results"
    output_paths = {
        "details": results_dir / f"{prefix}_details.csv",
        "summary_csv": results_dir / f"{prefix}_summary.csv",
        "summary_json": results_dir / f"{prefix}_summary.json",
        "metadata": results_dir / f"{prefix}_metadata.json",
    }
    if args.dataset == "holdout" and any(path.exists() for path in output_paths.values()):
        raise FileExistsError("Resultados do holdout já existem; a execução única não será sobrescrita.")

    records = load_snapshot(ROOT / "data/processed/hpo_ptbr.csv")
    metadata = load_metadata(ROOT / "data/processed/metadata.json")
    version = str(metadata["data_version"])
    cases = load_cases(cases_path)
    exact = ExactMapper(records, version)
    fuzzy = FuzzyMapper(records, version)
    bm25 = Bm25Mapper(records, version)
    semantic = SemanticMapper(records, version, load_default_encoder())
    hybrid = HybridMapper(records, version, (fuzzy, bm25, semantic))
    mappers = {
        "exact": exact,
        "fuzzy": fuzzy,
        "bm25": bm25,
        "semantic": semantic,
        "hybrid": hybrid,
    }
    details, summary = evaluate_cases(mappers, cases)
    gate = promotion_gate(summary)

    write_csv(output_paths["details"], details)
    write_csv(output_paths["summary_csv"], summary)
    output_paths["summary_json"].write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    experiment_metadata = {
        "experiment": "experiment-1-hybrid-retrieval",
        "dataset": args.dataset,
        "generated_at": datetime.now(UTC).isoformat(),
        "data_version": version,
        "case_file": str(cases_path.relative_to(ROOT).as_posix()),
        "case_count": len(cases),
        "model_name": DEFAULT_MODEL_NAME,
        "model_revision": DEFAULT_MODEL_REVISION,
        "hybrid": {
            "method": "unweighted_reciprocal_rank_fusion",
            "rrf_k": RRF_K,
            "source_top_k": SOURCE_TOP_K,
            "sources": ["fuzzy", "bm25", "semantic"],
            "exact_short_circuit": True,
        },
        "git_commit": commit,
        "git_dirty_before_run": dirty,
        "result_fingerprint_without_timing": result_fingerprint(details, summary),
        "promotion_gate": gate,
        "eligible_for_dashboard_promotion": args.dataset == "holdout" and gate["passed"],
        "holdout_manifest": holdout_manifest,
    }
    output_paths["metadata"].write_text(
        json.dumps(experiment_metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"summary": summary, "promotion_gate": gate}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
