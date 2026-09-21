"""Contratos da ingestão do ClinVar."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from hpo_ptbr.clinvar import (
    build_snapshot,
    disease_ids_from_phenotype_field,
    load_snapshot,
    primary_significance,
)

CABECALHO = (
    "#AlleleID", "Type", "Name", "GeneID", "GeneSymbol", "HGNC_ID",
    "ClinicalSignificance", "ClinSigSimple", "LastEvaluated", "RS# (dbSNP)",
    "nsv/esv (dbVar)", "RCVaccession", "PhenotypeIDS", "PhenotypeList", "Origin",
    "OriginSimple", "Assembly", "ChromosomeAccession", "Chromosome", "Start", "Stop",
    "ReferenceAllele", "AlternateAllele", "Cytogenetic", "ReviewStatus",
    "NumberSubmitters", "Guidelines", "TestedInGTR", "OtherIDs",
    "SubmitterCategories", "VariationID", "PositionVCF", "ReferenceAlleleVCF",
    "AlternateAlleleVCF",
)


def linha(**campos: str) -> str:
    padrao = {
        "#AlleleID": "1", "Type": "single nucleotide variant", "Name": "x",
        "GeneID": "472", "GeneSymbol": "ATM", "HGNC_ID": "HGNC:795",
        "ClinicalSignificance": "Pathogenic", "ClinSigSimple": "1",
        "LastEvaluated": "Mar 01, 2025", "RS# (dbSNP)": "-1", "nsv/esv (dbVar)": "-",
        "RCVaccession": "RCV1", "PhenotypeIDS": "MedGen:C0004135,OMIM:208900,Orphanet:100",
        "PhenotypeList": "Ataxia-telangiectasia", "Origin": "germline",
        "OriginSimple": "germline", "Assembly": "GRCh37", "ChromosomeAccession": "NC_1",
        "Chromosome": "11", "Start": "108098576", "Stop": "108098576",
        "ReferenceAllele": "na", "AlternateAllele": "na", "Cytogenetic": "11q22.3",
        "ReviewStatus": "criteria provided, multiple submitters, no conflicts",
        "NumberSubmitters": "3", "Guidelines": "-", "TestedInGTR": "N", "OtherIDs": "-",
        "SubmitterCategories": "2", "VariationID": "100", "PositionVCF": "108098576",
        "ReferenceAlleleVCF": "C", "AlternateAlleleVCF": "T",
    }
    padrao.update(campos)
    return "\t".join(padrao[c] for c in CABECALHO)


LINHAS = [
    linha(),                                                    # retida
    linha(Assembly="GRCh38", PositionVCF="108227849"),          # mesma, outro build
    linha(VariationID="101", OriginSimple="somatic"),           # somatica
    linha(VariationID="102",
          ClinicalSignificance="Conflicting classifications of pathogenicity"),
    linha(VariationID="103", ClinicalSignificance="Benign"),
    linha(VariationID="104", ClinicalSignificance="Likely pathogenic; risk factor",
          LastEvaluated="Jul 10, 2026"),                        # retida, modificador
    linha(VariationID="105", Type="Deletion", ReferenceAlleleVCF="CA",
          AlternateAlleleVCF="C", ReviewStatus="no assertion criteria provided"),
    linha(VariationID="106", PhenotypeIDS="MedGen:CN169374", PhenotypeList="not provided"),
    linha(VariationID="107", PositionVCF="-1"),                 # sem posicao VCF
    linha(),                                                    # duplicata exata
]


@pytest.fixture
def fonte(tmp_path: Path) -> Path:
    caminho = tmp_path / "variant_summary.txt.gz"
    with gzip.open(caminho, "wt", encoding="utf-8", newline="\n") as handle:
        handle.write("\t".join(CABECALHO) + "\n")
        handle.write("\n".join(LINHAS) + "\n")
    return caminho


@pytest.fixture
def snapshot(fonte: Path, tmp_path: Path):
    csv_path, meta = tmp_path / "clinvar.csv", tmp_path / "clinvar.json"
    manifesto = build_snapshot(fonte, csv_path, meta, genome_build="GRCh37")
    return csv_path, manifesto


def test_build_precisa_ser_declarado(fonte: Path, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Build precisa ser declarado"):
        build_snapshot(fonte, tmp_path / "a.csv", tmp_path / "b.json", genome_build="hg19")


def test_cabecalho_inesperado_nomeia_o_que_encontrou(tmp_path: Path) -> None:
    ruim = tmp_path / "v.txt"
    ruim.write_text("a\tb\n1\t2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Cabeçalho encontrado"):
        build_snapshot(ruim, tmp_path / "a.csv", tmp_path / "b.json", genome_build="GRCh37")


def test_aceita_nome_novo_da_coluna_de_classificacao(tmp_path: Path) -> None:
    """O ClinVar renomeou a coluna; o arquivo novo nao pode quebrar a ingestao."""
    cabecalho = [c if c != "ClinicalSignificance" else "GermlineClassification" for c in CABECALHO]
    caminho = tmp_path / "v.txt"
    caminho.write_text("\t".join(cabecalho) + "\n" + linha() + "\n", encoding="utf-8")
    manifesto = build_snapshot(caminho, tmp_path / "a.csv", tmp_path / "b.json",
                               genome_build="GRCh37")
    assert manifesto["source"]["significance_column"] == "GermlineClassification"
    assert manifesto["funnel"]["retained"] == 1


def test_funil_contabiliza_cada_filtro(snapshot) -> None:
    _, manifesto = snapshot
    funil = manifesto["funnel"]
    assert funil["rows_read"] == 10
    assert funil["rows_in_build"] == 9          # uma linha e GRCh38
    assert funil["germline"] == 8               # uma e somatica
    assert funil["pathogenic_or_likely"] == 6   # conflito e benigna saem
    assert funil["without_vcf_position"] == 1
    assert funil["duplicates"] == 1
    assert funil["retained"] == 4


def test_conflito_e_contado_a_parte(snapshot) -> None:
    """O grupo onde submetedores discordam precisa estar visivel, nao sumir."""
    _, manifesto = snapshot
    assert manifesto["excluded"]["conflicting_classifications"] == 1
    assert manifesto["excluded"]["by_origin"] == {"somatic": 1}
    assert manifesto["excluded"]["pathogenic_by_origin"] == {"somatic": 1}


def test_exclusao_por_origem_conta_so_patogenicas(tmp_path: Path) -> None:
    """Benigna de origem desconhecida nao pode inflar a contagem que importa."""
    caminho = tmp_path / "v.txt"
    linhas = [
        linha(VariationID="1", OriginSimple="unknown"),
        linha(VariationID="2", OriginSimple="unknown", ClinicalSignificance="Benign"),
        linha(VariationID="3"),
    ]
    caminho.write_text("\t".join(CABECALHO) + "\n" + "\n".join(linhas) + "\n", encoding="utf-8")
    manifesto = build_snapshot(caminho, tmp_path / "a.csv", tmp_path / "b.json",
                               genome_build="GRCh37")
    assert manifesto["excluded"]["by_origin"] == {"unknown": 2}
    assert manifesto["excluded"]["pathogenic_by_origin"] == {"unknown": 1}
    assert manifesto["filters"]["include_undeclared_origin"] is False


def test_origem_desconhecida_so_entra_quando_pedido(tmp_path: Path) -> None:
    caminho = tmp_path / "v.txt"
    linhas = [
        linha(VariationID="1", OriginSimple="unknown"),
        linha(VariationID="2", OriginSimple="not provided"),
        linha(VariationID="3", OriginSimple="somatic"),
        linha(VariationID="4"),
    ]
    caminho.write_text("\t".join(CABECALHO) + "\n" + "\n".join(linhas) + "\n", encoding="utf-8")
    manifesto = build_snapshot(caminho, tmp_path / "a.csv", tmp_path / "b.json",
                               genome_build="GRCh37", include_undeclared_origin=True)
    assert manifesto["funnel"]["retained"] == 3          # somatica continua fora
    assert manifesto["filters"]["include_undeclared_origin"] is True
    assert "unknown" in manifesto["filters"]["origin_accepted"]
    assert manifesto["excluded"]["pathogenic_by_origin"] == {"somatic": 1}


def test_so_o_build_declarado_sem_liftover(snapshot) -> None:
    csv_path, manifesto = snapshot
    assert manifesto["genome_build"] == {"declared": "GRCh37", "liftover": False}
    posicoes = {v.position for v in load_snapshot(csv_path)}
    assert 108227849 not in posicoes  # coordenada GRCh38 nao entra


def test_classificacao_com_modificador_e_retida(snapshot) -> None:
    csv_path, _ = snapshot
    por_id = {v.variation_id: v for v in load_snapshot(csv_path)}
    assert por_id["104"].clinical_significance == "Likely pathogenic"


def test_orphanet_e_traduzido_para_o_prefixo_da_hpo(snapshot) -> None:
    """Sem isso, nenhuma variante do Orphanet casaria com o painel de alvos."""
    csv_path, _ = snapshot
    variante = {v.variation_id: v for v in load_snapshot(csv_path)}["100"]
    assert variante.disease_ids == ("OMIM:208900", "ORPHA:100")


def test_variante_sem_doenca_e_retida_e_contada(snapshot) -> None:
    _, manifesto = snapshot
    assert manifesto["retained"]["without_disease_link"] == 1


def test_estrelas_e_tipo_registrados(snapshot) -> None:
    csv_path, manifesto = snapshot
    por_id = {v.variation_id: v for v in load_snapshot(csv_path)}
    assert por_id["100"].review_stars == 2
    assert por_id["105"].review_stars == 0
    assert por_id["105"].is_snv is False
    assert manifesto["retained"]["snv"] == 3


def test_data_de_corte_aproximada(snapshot) -> None:
    _, manifesto = snapshot
    assert manifesto["source"]["declares_release"] is False
    assert manifesto["source"]["latest_last_evaluated"] == "2026-07-10"


def test_saida_deterministica(fonte: Path, tmp_path: Path) -> None:
    a = build_snapshot(fonte, tmp_path / "a.csv", tmp_path / "a.json", genome_build="GRCh37")
    b = build_snapshot(fonte, tmp_path / "b.csv", tmp_path / "b.json", genome_build="GRCh37")
    assert a["outputs"]["csv_sha256"] == b["outputs"]["csv_sha256"]


def test_extracao_de_identificadores() -> None:
    assert disease_ids_from_phenotype_field(
        "MedGen:C1|OMIM:123456,Orphanet:77;MONDO:MONDO:0001"
    ) == ("OMIM:123456", "ORPHA:77")
    assert disease_ids_from_phenotype_field("MedGen:CN169374") == ()


def test_classificacao_primaria() -> None:
    assert primary_significance("Pathogenic/Likely pathogenic; other") == (
        "Pathogenic/Likely pathogenic"
    )


def test_manifesto_gravado_em_disco(snapshot, tmp_path: Path) -> None:
    gravado = json.loads((tmp_path / "clinvar.json").read_text(encoding="utf-8"))
    assert gravado["schema_version"] == "clinvar-pathogenic-snapshot-manifest-v1"
