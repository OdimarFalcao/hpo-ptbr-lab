from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hpo_ptbr.data import load_snapshot
from hpo_ptbr.evaluation import load_cases
from hpo_ptbr.protocol import select_holdout_concepts, write_review_form


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepara o formulário cego do holdout.")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    records = load_snapshot(ROOT / "data/processed/hpo_ptbr.csv")
    development_cases = load_cases(ROOT / "data/eval/pilot_cases.csv")
    concepts = select_holdout_concepts(records, development_cases)
    output = ROOT / "data/eval/holdout_review.csv"
    if output.exists() and not args.force:
        raise FileExistsError("O formulário já existe; use --force somente para descartá-lo.")
    write_review_form(output, concepts)
    print(f"Formulário criado para {len(concepts)} conceitos: {output}")


if __name__ == "__main__":
    main()
