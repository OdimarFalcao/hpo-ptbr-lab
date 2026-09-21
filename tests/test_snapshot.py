import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_snapshot_tem_rotulos_portugueses():
    with (ROOT / "data/processed/hpo_ptbr.csv").open(encoding="utf-8", newline="") as handle:
        linhas = list(csv.DictReader(handle))
    assert linhas, "snapshot terminológico vazio"
    assert all(linha["hpo_id"].startswith("HP:") for linha in linhas)
    assert sum(1 for linha in linhas if linha["label_pt"]) > 0


def test_metadata_has_reproducibility_fields():
    metadata = json.loads((ROOT / "data/processed/metadata.json").read_text(encoding="utf-8"))
    assert metadata["hpo_release"] != "unknown"
    assert len(metadata["translation_commit"]) == 40
    assert len(metadata["sources"]["hpo"]["sha256"]) == 64
    assert len(metadata["sources"]["hpo_pt"]["sha256"]) == 64
