"""Contratos do snapshot de anotações doença -> fenótipo."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hpo_ptbr.hpoa import (
    ASPECT_LABELS,
    HpoaAnnotation,
    HpoaIndex,
    build_snapshot,
    declared_hpo_release,
    disease_profile,
    load_snapshot,
    read_source_header,
)
from hpo_ptbr.ontology import HpoConcept, OntologyIndex

ROOT = Path(__file__).resolve().parents[1]

CABECALHO = (
    '#description: "HPO annotations for rare diseases"\n'
    "#version: 2026-06-23\n"
    "#tracker: https://example.test/issues\n"
    "#hpo-version: http://purl.obolibrary.org/obo/hp/releases/2026-06-23/hp.json\n"
)
COLUNAS = (
    "database_id\tdisease_name\tqualifier\thpo_id\treference\tevidence\tonset\t"
    "frequency\tsex\tmodifier\taspect\tbiocuration\n"
)
LINHAS = (
    "OMIM:000001\tDoenca de teste\t\tHP:0000002\tPMID:1\tPCS\tHP:0003593\t3/4\t\t\tP\tHPO:x[2026-01-01]\n"
    "OMIM:000001\tDoenca de teste\tNOT\tHP:0000003\tPMID:1\tPCS\t\t\t\t\tP\tHPO:x[2026-01-01]\n"
    "OMIM:000001\tDoenca de teste\t\tHP:0000004\tOMIM:000001\tIEA\t\t\t\t\tI\tHPO:iea[2026-01-01]\n"
    "OMIM:000001\tDoenca de teste\t\tHP:9999999\tPMID:1\tPCS\t\t\t\t\tP\tHPO:x[2026-01-01]\n"
    "OMIM:000002\tOutra doenca\t\tHP:0000002\tPMID:2\tTAS\t\t\t\t\tP\tHPO:y[2026-01-01]\n"
)

METADATA = {"hpo_release": "2026-06-23", "data_version": "teste-2026-06-23"}


def _ontologia() -> OntologyIndex:
    def conceito(hpo_id, en, pt, pais):
        return HpoConcept(
            hpo_id=hpo_id, label_en=en, label_pt=pt, definition_en="", definition_pt="",
            definition_sources=(), synonyms=(), parent_ids=tuple(pais), child_ids=(),
        )

    conceitos = {
        "HP:0000118": conceito("HP:0000118", "Phenotypic abnormality", "Anomalia fenotípica", []),
        "HP:0000002": conceito("HP:0000002", "Short stature", "Baixa estatura", ["HP:0000118"]),
        "HP:0000003": conceito("HP:0000003", "Seizure", "", ["HP:0000118"]),
        "HP:0000004": conceito("HP:0000004", "Autosomal recessive inheritance", "Herança autossômica recessiva", []),
        "HP:0003593": conceito("HP:0003593", "Infantile onset", "Início na infância", []),
    }
    return OntologyIndex(conceitos, "teste-2026-06-23")


@pytest.fixture
def snapshot(tmp_path: Path):
    bruto = tmp_path / "phenotype.hpoa"
    bruto.write_text(CABECALHO + COLUNAS + LINHAS, encoding="utf-8", newline="\n")
    csv_path, meta_path = tmp_path / "anotacoes.csv", tmp_path / "manifesto.json"
    manifesto = build_snapshot(bruto, _ontologia(), METADATA, csv_path, meta_path)
    return csv_path, meta_path, manifesto


def test_recusa_release_divergente(tmp_path: Path) -> None:
    """Perfil de uma release nao pode ser lido com o vocabulario de outra."""
    bruto = tmp_path / "outra.hpoa"
    bruto.write_text(
        CABECALHO.replace("2026-06-23/hp.json", "2024-04-26/hp.json") + COLUNAS + LINHAS,
        encoding="utf-8", newline="\n",
    )
    with pytest.raises(ValueError, match="2024-04-26"):
        build_snapshot(bruto, _ontologia(), METADATA, tmp_path / "a.csv", tmp_path / "b.json")


def test_recusa_arquivo_sem_versao_declarada(tmp_path: Path) -> None:
    bruto = tmp_path / "sem_versao.hpoa"
    bruto.write_text("#version: 2026-06-23\n" + COLUNAS + LINHAS, encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="hpo-version"):
        read_source_header(bruto)


def test_extrai_data_da_release() -> None:
    header = {"hpo-version": "http://purl.obolibrary.org/obo/hp/releases/2026-06-23/hp.json"}
    assert declared_hpo_release(header) == "2026-06-23"


def test_termo_ausente_do_snapshot_nao_entra_e_e_contado(snapshot) -> None:
    _, _, manifesto = snapshot
    assert manifesto["counts"]["terms_absent_from_terminology_snapshot"] == 1
    assert manifesto["counts"]["annotations"] == 4


def test_qualifier_not_vira_excluido_e_nao_some(snapshot) -> None:
    csv_path, meta_path, manifesto = snapshot
    assert manifesto["counts"]["excluded_qualifier_not"] == 1
    indice = load_snapshot(csv_path, meta_path)
    excluidos = [a for a in indice.annotations if a.excluded]
    assert [a.hpo_id for a in excluidos] == ["HP:0000003"]


def test_perfil_enriquece_com_status_de_traducao(snapshot) -> None:
    csv_path, meta_path, _ = snapshot
    perfil = disease_profile(load_snapshot(csv_path, meta_path), _ontologia(), "OMIM:000001")

    por_id = {e["hpo_id"]: e for e in perfil["annotations"]}
    assert por_id["HP:0000002"]["label_pt_status"] == "official"
    assert por_id["HP:0000002"]["label_pt"] == "Baixa estatura"
    assert por_id["HP:0000003"]["label_pt_status"] == "unavailable"
    assert por_id["HP:0000003"]["label_pt"] == ""
    assert por_id["HP:0000003"]["label_en"] == "Seizure"
    assert perfil["summary"]["without_pt_label"] == 1


def test_perfil_nao_inventa_traducao(snapshot) -> None:
    csv_path, meta_path, manifesto = snapshot
    assert manifesto["invented_translation"] is False
    perfil = disease_profile(load_snapshot(csv_path, meta_path), _ontologia(), "OMIM:000001")
    for entrada in perfil["annotations"]:
        if entrada["label_pt_status"] == "unavailable":
            assert entrada["label_pt"] == ""
            assert entrada["term_source"] == "HPO phenotype.hpoa"


def test_aspect_padrao_traz_somente_fenotipo(snapshot) -> None:
    csv_path, meta_path, _ = snapshot
    indice = load_snapshot(csv_path, meta_path)
    perfil = disease_profile(indice, _ontologia(), "OMIM:000001")
    assert {e["aspect"] for e in perfil["annotations"]} == {"P"}

    completo = disease_profile(indice, _ontologia(), "OMIM:000001", aspects=("P", "I"))
    aspectos = {e["aspect"] for e in completo["annotations"]}
    assert aspectos == {"P", "I"}
    heranca = next(e for e in completo["annotations"] if e["aspect"] == "I")
    assert heranca["aspect_label"] == ASPECT_LABELS["I"]
    assert heranca["in_phenotypic_tree"] is False


def test_campos_codificados_recebem_rotulo_legivel(snapshot) -> None:
    csv_path, meta_path, _ = snapshot
    perfil = disease_profile(load_snapshot(csv_path, meta_path), _ontologia(), "OMIM:000001")
    entrada = next(e for e in perfil["annotations"] if e["hpo_id"] == "HP:0000002")
    assert entrada["onset"] == "HP:0003593"
    assert entrada["onset_label"] == "Início na infância"
    assert entrada["frequency"] == "3/4"
    assert entrada["frequency_label"] == "3/4"


def test_doenca_inexistente_levanta_erro(snapshot) -> None:
    """Lista vazia silenciosa esconderia erro de digitacao."""
    csv_path, meta_path, _ = snapshot
    with pytest.raises(ValueError, match="OMIM:999999"):
        disease_profile(load_snapshot(csv_path, meta_path), _ontologia(), "OMIM:999999")


def test_busca_por_nome_e_deterministica(snapshot) -> None:
    csv_path, meta_path, _ = snapshot
    indice = load_snapshot(csv_path, meta_path)
    assert indice.search_diseases("doenca") == indice.search_diseases("DOENCA")
    assert [i for i, _ in indice.search_diseases("doenca")] == ["OMIM:000001", "OMIM:000002"]
    assert indice.search_diseases("   ") == []


def test_ordenacao_estavel_entre_execucoes(snapshot) -> None:
    csv_path, meta_path, _ = snapshot
    indice = load_snapshot(csv_path, meta_path)
    a = disease_profile(indice, _ontologia(), "OMIM:000001")
    b = disease_profile(indice, _ontologia(), "OMIM:000001")
    assert [e["hpo_id"] for e in a["annotations"]] == [e["hpo_id"] for e in b["annotations"]]


def test_manifesto_registra_proveniencia_completa(snapshot) -> None:
    _, _, manifesto = snapshot
    assert manifesto["schema_version"] == "hpoa-snapshot-manifest-v1"
    assert len(manifesto["source"]["sha256"]) == 64
    assert manifesto["source"]["hpo_release_declared"] == "2026-06-23"
    assert manifesto["terminology_snapshot"]["hpo_release"] == "2026-06-23"
    assert len(manifesto["outputs"]["csv_sha256"]) == 64
    cobertura = manifesto["portuguese_coverage_of_annotated_phenotypes"]
    assert cobertura["with_official_pt_label"] + cobertura["without_pt_label"] == cobertura["phenotypic_terms_used"]


@pytest.mark.skipif(
    not (ROOT / "data/processed/hpo_annotations.csv").is_file(),
    reason="snapshot HPOA real ainda não foi gerado (rode hpo-painel snapshot)",
)
def test_snapshot_real_casa_com_o_vocabulario_em_uso() -> None:
    manifesto = json.loads((ROOT / "data/processed/hpoa_metadata.json").read_text(encoding="utf-8"))
    terminologia = json.loads((ROOT / "data/processed/metadata.json").read_text(encoding="utf-8"))
    assert manifesto["source"]["hpo_release_declared"] == terminologia["hpo_release"]
    assert manifesto["counts"]["annotations"] > 0
    assert manifesto["invented_translation"] is False
