from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hpo_ptbr.data import load_metadata, load_snapshot
from hpo_ptbr.evidence import EvidenceExtractor
from hpo_ptbr.rankers import FuzzyMapper


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mede a latência da prova de conceito com textos sintéticos."
    )
    parser.add_argument("--runs", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.runs < 1:
        raise ValueError("--runs deve ser maior ou igual a 1.")

    records = load_snapshot(ROOT / "data/processed/hpo_ptbr.csv")
    metadata = load_metadata(ROOT / "data/processed/metadata.json")
    cases = json.loads(
        (ROOT / "data/demo/synthetic_descriptions.json").read_text(encoding="utf-8")
    )
    extractor = EvidenceExtractor(FuzzyMapper(records, str(metadata["data_version"])))

    case_results = []
    all_measurements = []
    for case in cases:
        measurements = [
            extractor.map_text(case["text"], top_k=5).latency_ms
            for _ in range(args.runs)
        ]
        all_measurements.extend(measurements)
        case_results.append(
            {
                "id": case["id"],
                "runs_ms": measurements,
                "median_ms": round(statistics.median(measurements), 3),
            }
        )

    payload = {
        "data_version": metadata["data_version"],
        "runs_per_case": args.runs,
        "case_results": case_results,
        "overall_median_ms": round(statistics.median(all_measurements), 3),
        "overall_mean_ms": round(statistics.mean(all_measurements), 3),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
