"""Contratos do cruzamento doença-alvo × ClinVar × painel genotipado."""

from __future__ import annotations

from pathlib import Path

import pytest

from hpo_ptbr.clinvar import SNV, PathogenicVariant
from hpo_ptbr.gene_disease import GeneDiseaseAssociation, GeneDiseaseIndex
from hpo_ptbr.genotype_panel import classify_allele, load_panel, read_panel_alleles
from hpo_ptbr.hpoa import HpoaAnnotation, HpoaIndex
from hpo_ptbr.target_coverage import TIERS, assess_targets, write_report

# Painel: cr1 posicoes 1000 (C/T), 2000 (G/A), 3000 (A/C); cr21 47.000.000 fixa GRCh37.
PAINEL = (
    "s1 1 0.0 1000 C T\n"
    "s2 1 0.0 2000 G A\n"
    "s3 1 0.0 3000 A C\n"
    "s4 21 0.0 47000000 A G\n"
)


def _variante(vid: str, doencas: tuple[str, ...], pos: int, ref: str, alt: str,
              tipo: str = SNV, estrelas: int = 2) -> PathogenicVariant:
    return PathogenicVariant(
        variation_id=vid, allele_id=vid, gene_symbol="G", gene_id="1",
        variant_type=tipo, clinical_significance="Pathogenic", review_status="",
        review_stars=estrelas, chromosome="1", position=pos, ref=ref, alt=alt,
        disease_ids=doencas, phenotype_list="",
    )


def _anotacao(doenca: str) -> HpoaAnnotation:
    return HpoaAnnotation(
        database_id=doenca, disease_name=f"nome {doenca}", hpo_id="HP:0000002",
        aspect="P", excluded=False, frequency="", onset="", sex="", modifier="",
        evidence="PCS", reference="", biocuration="",
    )


DOENCAS = {
    "OMIM:000001": "alelo casa exato",
    "OMIM:000002": "alelo casa pela fita oposta",
    "OMIM:000003": "posicao certa, alelo diferente",
    "OMIM:000004": "SNV fora do painel",
    "OMIM:000005": "so indel",
    "ORPHA:000006": "sem variante; gene nao classificado",
}

VARIANTES = (
    _variante("v1", ("OMIM:000001",), 1000, "C", "T"),
    _variante("v2", ("OMIM:000002",), 2000, "C", "T"),    # complemento de G/A
    _variante("v3", ("OMIM:000003",), 3000, "A", "G"),    # painel ensaia A/C
    _variante("v4", ("OMIM:000004",), 9999, "C", "T"),
    _variante("v5", ("OMIM:000005",), 1000, "CA", "C", tipo="Deletion"),
    _variante("v6", ("OMIM:999999",), 1000, "C", "T"),    # doenca fora do universo
)


@pytest.fixture
def cenario(tmp_path: Path):
    snp = tmp_path / "p.snp"
    snp.write_text(PAINEL, encoding="utf-8", newline="\n")
    painel = load_panel(snp, "GRCh37", panel_label="teste")
    posicoes = {(v.chromosome, v.position) for v in VARIANTES if v.is_snv}
    alelos = read_panel_alleles(snp, posicoes)
    hpoa = HpoaIndex("2026-06-23", "2026-06-23", tuple(_anotacao(d) for d in DOENCAS))
    genes = GeneDiseaseIndex(
        tuple(
            GeneDiseaseAssociation(
                ncbi_gene_id="1", gene_symbol=f"G{i}",
                association_type="UNKNOWN" if d.startswith("ORPHA") else "MENDELIAN",
                disease_id=d, source="teste",
            )
            for i, d in enumerate(DOENCAS)
        )
    )
    return hpoa, genes, painel, alelos


def _por_doenca(resultado) -> dict[str, dict]:
    return {linha["disease_id"]: linha for linha in resultado["diseases"]}


def test_recusa_variantes_de_outro_build(cenario) -> None:
    """A protecao central continua valendo pelo caminho novo."""
    hpoa, genes, painel, alelos = cenario
    with pytest.raises(ValueError, match="Build divergente"):
        assess_targets(hpoa, genes, VARIANTES, "GRCh38", painel, alelos)


def test_cada_doenca_cai_no_nivel_mais_fundo_que_alcanca(cenario) -> None:
    resultado = assess_targets(*cenario[:2], VARIANTES, "GRCh37", *cenario[2:])
    niveis = {d: l["tier"] for d, l in _por_doenca(resultado).items()}
    assert niveis == {
        "OMIM:000001": "alelo_patogenico_ensaiado",
        "OMIM:000002": "alelo_por_fita_oposta",
        "OMIM:000003": "posicao_alelo_diferente",
        "OMIM:000004": "snv_fora_do_painel",
        "OMIM:000005": "sem_snv",
        "ORPHA:000006": "sem_variante_patogenica",
    }


def test_posicao_certa_nao_basta(cenario) -> None:
    """O painel ensaia A/C; a variante e A>G. Estar na posicao nao e observar."""
    resultado = assess_targets(*cenario[:2], VARIANTES, "GRCh37", *cenario[2:])
    linha = _por_doenca(resultado)["OMIM:000003"]
    assert linha["snv_at_panel_position"] == 1
    assert linha["allele_match"] == 0
    assert resultado["variants"]["different_alleles"] == 1


def test_indel_na_mesma_posicao_nao_conta(cenario) -> None:
    """A delecao comeca em 1000, que e ensaiada. Painel de SNP nao a observa."""
    resultado = assess_targets(*cenario[:2], VARIANTES, "GRCh37", *cenario[2:])
    linha = _por_doenca(resultado)["OMIM:000005"]
    assert linha["pathogenic_variants"] == 1
    assert linha["pathogenic_snv"] == 0


def test_dois_universos_separam_o_orphanet(cenario) -> None:
    resultado = assess_targets(*cenario[:2], VARIANTES, "GRCh37", *cenario[2:])
    universos = resultado["universes"]
    assert universos["mendelian_declared_by_omim"]["diseases"] == 5
    assert universos["any_gene_association"]["diseases"] == 6
    assert set(universos["any_gene_association"]["by_tier"]) == set(TIERS)


def test_variante_de_doenca_fora_do_universo_nao_infla(cenario) -> None:
    resultado = assess_targets(*cenario[:2], VARIANTES, "GRCh37", *cenario[2:])
    assert "OMIM:999999" not in _por_doenca(resultado)


def test_filtro_por_estrelas(cenario) -> None:
    hpoa, genes, painel, alelos = cenario
    fracas = tuple(
        v if v.variation_id != "v1" else _variante("v1", ("OMIM:000001",), 1000, "C", "T",
                                                   estrelas=0)
        for v in VARIANTES
    )
    resultado = assess_targets(hpoa, genes, fracas, "GRCh37", painel, alelos,
                               min_review_stars=1)
    assert _por_doenca(resultado)["OMIM:000001"]["tier"] == "sem_variante_patogenica"
    assert resultado["variants"]["ignored_below_min_stars"] == 1


def test_relatorio_gravado(cenario, tmp_path: Path) -> None:
    resultado = assess_targets(*cenario[:2], VARIANTES, "GRCh37", *cenario[2:])
    manifesto = write_report(resultado, tmp_path / "c.csv", tmp_path / "c.json",
                             sources={"teste": True})
    linhas = (tmp_path / "c.csv").read_text(encoding="utf-8").splitlines()
    assert len(linhas) == 7
    assert manifesto["universes"]["any_gene_association"]["by_tier"][
        "alelo_patogenico_ensaiado"] == 1


def test_classificacao_de_alelo() -> None:
    assert classify_allele("C", "T", (("C", "T"),)) == "allele_match"
    assert classify_allele("C", "T", (("T", "C"),)) == "allele_match"
    assert classify_allele("C", "T", (("G", "A"),)) == "strand_flip_match"
    assert classify_allele("A", "G", (("A", "C"),)) == "different_alleles"
    assert classify_allele("A", "G", ()) == "different_alleles"


def test_leitura_de_alelos_guarda_so_o_pedido(tmp_path: Path) -> None:
    snp = tmp_path / "p.snp"
    snp.write_text(PAINEL, encoding="utf-8", newline="\n")
    alelos = read_panel_alleles(snp, {("1", 2000)})
    assert alelos == {("1", 2000): (("G", "A"),)}
