"""Caminhos, constantes e formatação compartilhados pelos comandos."""

from __future__ import annotations

import os
from pathlib import Path


def _raiz() -> Path:
    """Raiz do projeto: onde ficam `data/raw` e `data/processed`.

    Ordem: variável `ALCANCE_RAIZ`; o repositório que contém este pacote
    (instalação editável, `pip install -e .`); o diretório atual.
    """
    if os.environ.get("ALCANCE_RAIZ"):
        return Path(os.environ["ALCANCE_RAIZ"]).resolve()
    repositorio = Path(__file__).resolve().parents[3]
    if (repositorio / "data").is_dir():
        return repositorio
    return Path.cwd()


ROOT = _raiz()

RELEASE_BASE = (
    "https://github.com/obophenotype/human-phenotype-ontology/releases/download/v2026-06-23"
)

HPOA_SOURCE = ROOT / "data/raw/phenotype.hpoa"
HPOA_CSV = ROOT / "data/processed/hpo_annotations.csv"
HPOA_MANIFEST = ROOT / "data/processed/hpoa_metadata.json"

GENES_SOURCE = ROOT / "data/raw/genes_to_disease.txt"
GENES_CSV = ROOT / "data/processed/gene_disease.csv"
GENES_MANIFEST = ROOT / "data/processed/gene_disease_metadata.json"

PANEL_MANIFEST = ROOT / "data/processed/genotype_panel_metadata.json"

AADR_ANNO_URL = ""
AADR_ANNO_MANIFEST = ROOT / "data/processed/aadr_anno_metadata.json"

CLINVAR_URL = "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz"
CLINVAR_SOURCE = ROOT / "data/raw/variant_summary.txt.gz"
CLINVAR_CSV = ROOT / "data/processed/clinvar_pathogenic.csv"
CLINVAR_MANIFEST = ROOT / "data/processed/clinvar_pathogenic_metadata.json"

COVERAGE_CSV = ROOT / "data/processed/target_coverage.csv"
COVERAGE_MANIFEST = ROOT / "data/processed/target_coverage_metadata.json"

ONTOLOGY_PATH = ROOT / "data/processed/hpo_ontology.json.gz"
METADATA_PATH = ROOT / "data/processed/metadata.json"

LIMIT_NOTE = (
    "Consulta sobre dados versionados da HPO. Não constitui diagnóstico, não substitui "
    "julgamento profissional e exige revisão antes de qualquer uso."
)


def _milhar(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")

def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)

def _gene_id(valor: str) -> str:
    """O identificador ja vem prefixado (NCBIGene:10913); nao duplicar."""
    return valor if ":" in valor else f"NCBIGene:{valor}"

def _fonte_curta(valor: str) -> str:
    """As fontes vem como URL completa; exibir so o arquivo."""
    return valor.rstrip("/").rsplit("/", 1)[-1] or valor
