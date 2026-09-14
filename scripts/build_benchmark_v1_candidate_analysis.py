from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_benchmark_v1_candidates import _build_error_analysis, _build_report

RESULTS_DIR = ROOT / "data/results"


def _read_csv(path: Path) -> list[dict[str, object]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    gold_rows = _read_csv(RESULTS_DIR / "benchmark_v1_candidate_gold_details.csv")
    prediction_rows = _read_csv(
        RESULTS_DIR / "benchmark_v1_candidate_predictions.csv"
    )
    analysis = _build_error_analysis(gold_rows, prediction_rows)
    (RESULTS_DIR / "benchmark_v1_candidate_error_analysis.json").write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    baseline = _read_json(
        RESULTS_DIR / "benchmark_v1_development_summary.json"
    )
    summaries = _read_json(RESULTS_DIR / "benchmark_v1_candidate_summary.json")
    gates = _read_json(RESULTS_DIR / "benchmark_v1_candidate_gates.json")
    (RESULTS_DIR / "benchmark_v1_candidate_report.md").write_text(
        _build_report(baseline, summaries, gates, analysis),
        encoding="utf-8",
    )
    print(json.dumps(analysis, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
