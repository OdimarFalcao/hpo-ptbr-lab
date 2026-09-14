"""Contratos do snapshot de associações gene <-> doença."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hpo_ptbr.gene_disease import (
    ASSOCIATION_LABELS,
    build_snapshot,
    disease_genes,
    load_snapshot,
)

ROOT = Path(__file__).resolve().parents[1]

CABECALHO = "ncbi_gene_id\tgene_symbol\tassociation_type\tdisease_id\tsource\n"
LINHAS = (
    "10913\tEDAR\tMENDELIAN\tOMIM:224900\tmim2gene\n"
    "10913\tEDAR\tMENDELIAN\tOMIM:129490\tmim2gene\n"
    "1958\tEGR1\tPOLYGENIC\tOMIM:224900\tmedgen\n"
    "9999\tFAKE1\tUNKNOWN\tORPHA:000001\torphadata\n"
    "\t\t\t\t\n"
)


@pytest.fixture
def snapshot(tmp_path: Path):
    bruto = tmp_path / "genes_to_disease.txt"
    bruto.write_text(CABECALHO + LINHAS, encoding="utf-8", newline="\n")
    csv_path, meta_path = tmp_path / "genes.csv", tmp_path / "manifesto.json"
    manifesto = build_snapshot(
        bruto,
        csv_path,
        meta_path,
        known_disease_ids=frozenset({"OMIM:224900", "OMIM:129490"}),
    )
    return csv_path, meta_path, manifesto


def test_recusa_cabecalho_incompativel(tmp_path: Path) -> None:
    """Coluna faltando precisa gerar erro nomeando o que foi encontrado."""
    bruto = tmp_path / "errado.txt"
    bruto.write_text("gene\tdoenca\n1\t2\n", encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="Colunas ausentes"):
        build_snapshot(bruto, tmp_path / "a.csv", tmp_path / "b.json")


def test_linhas_vazias_sao_descartadas(snapshot) -> None:
    _, _, manifesto = snapshot
    assert manifesto["counts"]["associations"] == 4


def test_manifesto_separa_tipos_de_associacao(snapshot) -> None:
    _, _, manifesto = snapshot
    tipos = manifesto["counts"]["by_association_type"]
    assert tipos == {"MENDELIAN": 2, "POLYGENIC": 1, "UNKNOWN": 1}
    assert manifesto["counts"]["mendelian_diseases"] == 2


def test_manifesto_registra_que_a_fonte_nao_declara_release(snapshot) -> None:
    """Honestidade de proveniencia: o arquivo nao tem versao no cabecalho."""
    _, _, manifesto = snapshot
    assert manifesto["source"]["declares_hpo_release"] is False
    assert len(manifesto["source"]["sha256"]) == 64


def test_consistencia_e_medida_nao_presumida(snapshot) -> None:
    _, _, manifesto = snapshot
    consistencia = manifesto["consistency"]
    assert consistencia["checked_against_hpoa_snapshot"] is True
    assert consistencia["diseases_cited"] == 3
    assert consistencia["also_present_in_hpoa_snapshot"] == 2
    assert consistencia["percent_overlap"] == pytest.approx(66.67, abs=0.01)


def test_consistencia_ausente_quando_nao_ha_referencia(tmp_path: Path) -> None:
    bruto = tmp_path / "genes_to_disease.txt"
    bruto.write_text(CABECALHO + LINHAS, encoding="utf-8", newline="\n")
    manifesto = build_snapshot(bruto, tmp_path / "g.csv", tmp_path / "m.json")
    assert manifesto["consistency"]["checked_against_hpoa_snapshot"] is False
    assert "percent_overlap" not in manifesto["consistency"]


def test_genes_da_doenca_com_rotulo_de_associacao(snapshot) -> None:
    csv_path, _, _ = snapshot
    resultado = disease_genes(load_snapshot(csv_path), "OMIM:224900")

    simbolos = [g["gene_symbol"] for g in resultado["genes"]]
    assert simbolos == ["EDAR", "EGR1"]
    edar = resultado["genes"][0]
    assert edar["is_mendelian"] is True
    assert edar["association_label"] == ASSOCIATION_LABELS["MENDELIAN"]
    assert edar["ncbi_gene_id"] == "10913"
    assert edar["term_source"] == "HPO genes_to_disease.txt"
    assert resultado["summary"] == {"genes": 2, "associations": 2, "mendelian": 1}


def test_filtro_monogenico(snapshot) -> None:
    csv_path, _, _ = snapshot
    resultado = disease_genes(load_snapshot(csv_path), "OMIM:224900", only_mendelian=True)
    assert [g["gene_symbol"] for g in resultado["genes"]] == ["EDAR"]
    assert resultado["only_mendelian"] is True


def test_filtro_que_descarta_tudo_registra_o_que_foi_omitido(snapshot) -> None:
    """Caso mais perigoso: a fonte nao classifica, o filtro zera, e ninguem ve.

    Todas as associacoes do Orphanet chegam como UNKNOWN. Filtrar por
    MENDELIAN remove o catalogo inteiro sem que isso signifique que as
    doencas nao sejam monogenicas.
    """
    csv_path, _, _ = snapshot
    resultado = disease_genes(load_snapshot(csv_path), "ORPHA:000001", only_mendelian=True)

    assert resultado["genes"] == []
    assert len(resultado["filtered_out"]) == 1
    omitida = resultado["filtered_out"][0]
    assert omitida["gene_symbol"] == "FAKE1"
    assert omitida["association_type"] == "UNKNOWN"
    assert omitida["reason"] == "fonte nao classifica o tipo de associacao"


def test_manifesto_nomeia_fontes_sem_classificacao(snapshot) -> None:
    _, _, manifesto = snapshot
    caveat = manifesto["association_type_caveat"]
    assert caveat["sources_without_classification"] == ["orphadata"]
    assert caveat["associations_unclassified"] == 1
    assert caveat["by_source"]["mim2gene"] == {"MENDELIAN": 2}


def test_doenca_sem_gene_devolve_lista_vazia_nao_erro(snapshot) -> None:
    """Ausencia de gene conhecido e informacao legitima, nao falha."""
    csv_path, _, _ = snapshot
    resultado = disease_genes(load_snapshot(csv_path), "OMIM:999999")
    assert resultado["genes"] == []
    assert resultado["summary"]["genes"] == 0


def test_busca_por_gene_e_case_insensitive(snapshot) -> None:
    csv_path, _, _ = snapshot
    indice = load_snapshot(csv_path)
    assert [a.disease_id for a in indice.for_gene("edar")] == ["OMIM:129490", "OMIM:224900"]
    assert indice.for_gene("edar") == indice.for_gene("EDAR")


def test_ordenacao_determinista(snapshot) -> None:
    csv_path, _, _ = snapshot
    indice = load_snapshot(csv_path)
    a = disease_genes(indice, "OMIM:224900")
    b = disease_genes(indice, "OMIM:224900")
    assert a == b
    assert list(indice.mendelian_disease_ids()) == ["OMIM:129490", "OMIM:224900"]


@pytest.mark.skipif(
    not (ROOT / "data/processed/gene_disease.csv").is_file(),
    reason="snapshot gene-doença real ainda não foi gerado",
)
def test_snapshot_real_tem_associacoes_mendelianas() -> None:
    manifesto = json.loads(
        (ROOT / "data/processed/gene_disease_metadata.json").read_text(encoding="utf-8")
    )
    assert manifesto["counts"]["mendelian_diseases"] > 0
    assert manifesto["source"]["declares_hpo_release"] is False
    consistencia = manifesto["consistency"]
    if consistencia["checked_against_hpoa_snapshot"]:
        assert consistencia["percent_overlap"] > 50, (
            "sobreposição baixa com o snapshot de anotações sugere releases divergentes"
        )
