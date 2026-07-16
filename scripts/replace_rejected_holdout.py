from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hpo_ptbr.data import load_snapshot
from hpo_ptbr.evaluation import load_cases
from hpo_ptbr.protocol import replace_rejected_concepts


def main() -> None:
    replaced = replace_rejected_concepts(
        review_path=ROOT / "data/eval/holdout_review.csv",
        rejections_path=ROOT / "data/eval/holdout_rejections.csv",
        records=load_snapshot(ROOT / "data/processed/hpo_ptbr.csv"),
        development_cases=load_cases(ROOT / "data/eval/pilot_cases.csv"),
    )
    print(f"Conceitos substituídos: {replaced}")


if __name__ == "__main__":
    main()
