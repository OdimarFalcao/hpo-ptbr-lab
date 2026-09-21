"""Contratos do painel de posições genotipadas."""

from __future__ import annotations

from pathlib import Path

import pytest

from hpo_ptbr.genotype_panel import (
    GENOME_BUILDS,
    build_manifest,
    check_coverage,
    load_panel,
    verify_declared_build,
)

SNP = """rs3094315     1 0.020130    752566 G A
rs7419119      1 0.022518    842013 T G
rs6696609     23 0.024116    891021 C T
rs2949420     24 0.024457    903426 T A
mt_073        90 0.000000        73 A G
rs_estranho   77 0.000000    123456 A G
linha_curta   1
"""


@pytest.fixture
def snp_file(tmp_path: Path) -> Path:
    caminho = tmp_path / "painel.snp"
    caminho.write_text(SNP, encoding="utf-8", newline="\n")
    return caminho


def test_build_precisa_ser_declarado(snp_file: Path) -> None:
    """Nao se adivinha build: coordenada sem montagem nao significa nada."""
    with pytest.raises(ValueError, match="declarado explicitamente"):
        load_panel(snp_file, "hg19")
    with pytest.raises(ValueError, match="declarado explicitamente"):
        load_panel(snp_file, "")


def test_codigos_de_cromossomo_sao_traduzidos(snp_file: Path) -> None:
    painel = load_panel(snp_file, "GRCh37")
    assert set(painel.positions) == {"1", "X", "Y", "MT"}
    assert painel.counts_by_chromosome() == {"1": 2, "X": 1, "Y": 1, "MT": 1}
    assert painel.total == 5


def test_codigo_desconhecido_e_contado_nao_descartado(snp_file: Path) -> None:
    painel = load_panel(snp_file, "GRCh37")
    assert painel.unknown_chromosome_codes == ("77",)


def test_consulta_de_posicao(snp_file: Path) -> None:
    painel = load_panel(snp_file, "GRCh37")
    assert painel.is_assayed("1", 752566) is True
    assert painel.is_assayed("1", 752567) is False
    assert painel.is_assayed("x", 891021) is True  # case-insensitive
    assert painel.is_assayed("MT", 73) is True


def test_arquivo_sem_posicoes_validas_levanta_erro(tmp_path: Path) -> None:
    vazio = tmp_path / "ruim.snp"
    vazio.write_text("cabecalho invalido\n", encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="Nenhuma posição válida"):
        load_panel(vazio, "GRCh37")


def test_cobertura_recusa_builds_divergentes(snp_file: Path) -> None:
    """A protecao central: intersecao entre builds e numericamente valida e falsa."""
    painel = load_panel(snp_file, "GRCh37")
    variantes = [{"chromosome": "1", "position": 752566}]
    with pytest.raises(ValueError, match="Build divergente"):
        check_coverage(painel, variantes, "GRCh38")


def test_cobertura_separa_ensaiadas_de_ausentes(snp_file: Path) -> None:
    painel = load_panel(snp_file, "GRCh37")
    variantes = [
        {"chromosome": "1", "position": 752566, "gene": "A"},
        {"chromosome": "1", "position": 999999, "gene": "B"},
        {"chromosome": "X", "position": 891021, "gene": "C"},
    ]
    resultado = check_coverage(painel, variantes, "GRCh37")

    assert resultado["summary"] == {
        "variants_checked": 3,
        "assayed": 2,
        "not_assayed": 1,
        "percent_assayed": pytest.approx(66.67, abs=0.01),
    }
    assert [v["gene"] for v in resultado["assayed"]] == ["A", "C"]
    assert [v["gene"] for v in resultado["not_assayed"]] == ["B"]


def test_cobertura_com_lista_vazia_nao_divide_por_zero(snp_file: Path) -> None:
    painel = load_panel(snp_file, "GRCh37")
    resultado = check_coverage(painel, [], "GRCh37")
    assert resultado["summary"]["percent_assayed"] is None


def test_manifesto_registra_build_como_declarado(snp_file: Path, tmp_path: Path) -> None:
    painel = load_panel(snp_file, "GRCh37", panel_label="teste")
    manifesto = build_manifest(snp_file, painel, tmp_path / "m.json")

    assert manifesto["genome_build"]["declared"] == "GRCh37"
    assert manifesto["genome_build"]["inferred"] is False
    assert len(manifesto["source"]["sha256"]) == 64
    assert manifesto["panel"]["assayed_positions"] == 5
    assert manifesto["panel"]["autosomal_positions"] == 2
    assert manifesto["parsing"]["unknown_chromosome_codes"] == ["77"]


def test_manifesto_nao_afirma_qual_painel_e(snp_file: Path, tmp_path: Path) -> None:
    """Semelhanca de tamanho e sugestiva, nunca identificacao."""
    painel = load_panel(snp_file, "GRCh37")
    manifesto = build_manifest(snp_file, painel, tmp_path / "m.json")
    assert manifesto["panel"]["size_match_is_suggestive_only"] is True
    assert "não corresponde" in manifesto["panel"]["resembles_known_panel"]


def test_builds_suportados_sao_explicitos() -> None:
    assert GENOME_BUILDS == ("GRCh37", "GRCh38")


# --- verificação do build por evidência interna -----------------------------
# Uma posição não pode exceder o comprimento do cromossomo naquela montagem.
# cr21: GRCh37 tem 48.129.895 bp; GRCh38 tem 46.709.983. Uma posição entre os
# dois valores só é possível em GRCh37.
SO_EM_37 = "rs_a 21 0.0 47000000 A G\n"
SO_EM_38 = "rs_b 17 0.0 82000000 A G\n"   # GRCh37 cr17 = 81.195.210; GRCh38 = 83.257.441
AMBIGUO = "rs_c  1 0.0   752566 G A\n"


def _painel(tmp_path: Path, conteudo: str, build: str):
    caminho = tmp_path / "p.snp"
    caminho.write_text(conteudo, encoding="utf-8", newline="\n")
    return load_panel(caminho, build)


def test_verificacao_confirma_build_correto(tmp_path: Path) -> None:
    resultado = verify_declared_build(_painel(tmp_path, SO_EM_37 + AMBIGUO, "GRCh37"))
    assert resultado["verdict"] == "consistente"
    assert resultado["chromosomes_exclusive_to"]["GRCh37"] == 1
    assert resultado["chromosomes_exclusive_to"]["GRCh38"] == 0


def test_verificacao_detecta_build_declarado_errado(tmp_path: Path) -> None:
    """A protecao que importa: declarar GRCh38 um arquivo que so cabe em GRCh37."""
    resultado = verify_declared_build(_painel(tmp_path, SO_EM_37, "GRCh38"))
    assert resultado["verdict"] == "contradiz_declaracao"
    assert "GRCh37" in resultado["explanation"]


def test_verificacao_detecta_evidencia_contraditoria(tmp_path: Path) -> None:
    resultado = verify_declared_build(_painel(tmp_path, SO_EM_37 + SO_EM_38, "GRCh37"))
    assert resultado["verdict"] == "contraditorio"


def test_verificacao_admite_ser_inconclusiva(tmp_path: Path) -> None:
    """Posicoes baixas cabem nos dois builds: o metodo nao decide, e diz isso."""
    resultado = verify_declared_build(_painel(tmp_path, AMBIGUO, "GRCh37"))
    assert resultado["verdict"] == "inconclusivo"
    assert resultado["chromosomes_exclusive_to"] == {"GRCh37": 0, "GRCh38": 0}


def test_verificacao_entra_no_manifesto(tmp_path: Path) -> None:
    painel = _painel(tmp_path, SO_EM_37, "GRCh37")
    manifesto = build_manifest(tmp_path / "p.snp", painel, tmp_path / "m.json")
    verificacao = manifesto["genome_build"]["verification"]
    assert verificacao["verdict"] == "consistente"
    assert verificacao["evidence"][0]["chromosome"] == "21"
    assert verificacao["evidence"][0]["decides_for"] == "GRCh37"
