"""Contratos do caminho inverso: termo fenotípico -> doenças -> genes."""

from __future__ import annotations

import pytest

from hpo_ptbr.gene_disease import GeneDiseaseAssociation, GeneDiseaseIndex
from hpo_ptbr.hpoa import HpoaAnnotation, HpoaIndex
from hpo_ptbr.ontology import HpoConcept, OntologyIndex
from hpo_ptbr.term_targets import term_diseases


def _conceito(hpo_id: str, en: str, pt: str, pais: tuple[str, ...] = ()) -> HpoConcept:
    return HpoConcept(
        hpo_id=hpo_id, label_en=en, label_pt=pt, definition_en="", definition_pt="",
        definition_sources=(), synonyms=(), parent_ids=pais, child_ids=(),
    )


@pytest.fixture
def ontologia() -> OntologyIndex:
    conceitos = {
        "HP:0000118": _conceito("HP:0000118", "Phenotypic abnormality", "Anomalia fenotípica"),
        "HP:0000002": _conceito("HP:0000002", "Short stature", "Baixa estatura", ("HP:0000118",)),
        "HP:0000003": _conceito("HP:0000003", "Seizure", "", ("HP:0000118",)),
        "HP:0000009": _conceito("HP:0000009", "Termo nunca anotado", "", ("HP:0000118",)),
    }
    return OntologyIndex(conceitos, "teste-2026-06-23")


def _anotacao(doenca: str, nome: str, hpo_id: str, excluded: bool = False) -> HpoaAnnotation:
    return HpoaAnnotation(
        database_id=doenca, disease_name=nome, hpo_id=hpo_id, aspect="P",
        excluded=excluded, frequency="3/4", onset="", sex="", modifier="",
        evidence="PCS", reference="PMID:1", biocuration="HPO:x[2026-01-01]",
    )


@pytest.fixture
def anotacoes() -> HpoaIndex:
    return HpoaIndex(
        hpo_release="2026-06-23",
        hpoa_version="2026-06-23",
        annotations=(
            _anotacao("OMIM:000001", "Doenca mendeliana", "HP:0000002"),
            _anotacao("OMIM:000002", "Doenca poligenica", "HP:0000002"),
            _anotacao("ORPHA:000003", "Doenca do Orphanet", "HP:0000002"),
            _anotacao("OMIM:000004", "Doenca sem gene", "HP:0000002"),
            # A mesma doenca descarta explicitamente o termo: afirmacao oposta.
            _anotacao("OMIM:000005", "Doenca que descarta", "HP:0000002", excluded=True),
            _anotacao("OMIM:000001", "Doenca mendeliana", "HP:0000003"),
        ),
    )


@pytest.fixture
def genes() -> GeneDiseaseIndex:
    def associacao(gene: str, tipo: str, doenca: str, fonte: str) -> GeneDiseaseAssociation:
        return GeneDiseaseAssociation(
            ncbi_gene_id="1", gene_symbol=gene, association_type=tipo,
            disease_id=doenca, source=fonte,
        )

    return GeneDiseaseIndex(
        (
            associacao("EDAR", "MENDELIAN", "OMIM:000001", "mim2gene"),
            associacao("EGR1", "POLYGENIC", "OMIM:000002", "medgen"),
            associacao("ATM", "UNKNOWN", "ORPHA:000003", "orphadata"),
        )
    )


def test_termo_inexistente_e_erro_nao_lista_vazia(anotacoes, ontologia) -> None:
    """Identificador errado precisa falhar: vazio silencioso esconde o erro."""
    with pytest.raises(ValueError, match="ausente do vocabulário"):
        term_diseases(anotacoes, ontologia, "HP:1234567")


def test_termo_valido_sem_anotacao_devolve_vazio_sem_erro(anotacoes, ontologia) -> None:
    """Existir no vocabulario e nunca ter sido anotado e informacao legitima."""
    alvo = term_diseases(anotacoes, ontologia, "HP:0000009")
    assert alvo["diseases"] == []
    assert alvo["summary"]["diseases_presenting"] == 0


def test_lista_doencas_que_apresentam_o_termo(anotacoes, ontologia) -> None:
    alvo = term_diseases(anotacoes, ontologia, "HP:0000002")
    assert [d["database_id"] for d in alvo["diseases"]] == [
        "OMIM:000001", "OMIM:000002", "OMIM:000004", "ORPHA:000003",
    ]
    assert alvo["summary"]["diseases_presenting"] == 4


def test_anotacao_com_not_nao_entra_na_lista(anotacoes, ontologia) -> None:
    """A protecao central: NOT afirma ausencia, o oposto de apresentar."""
    alvo = term_diseases(anotacoes, ontologia, "HP:0000002")
    identificadores = [d["database_id"] for d in alvo["diseases"]]
    assert "OMIM:000005" not in identificadores
    assert alvo["excluded_in"] == [
        {"database_id": "OMIM:000005", "disease_name": "Doenca que descarta"}
    ]
    assert alvo["summary"]["diseases_excluding_term"] == 1


def test_genes_entram_quando_o_indice_e_fornecido(anotacoes, ontologia, genes) -> None:
    alvo = term_diseases(anotacoes, ontologia, "HP:0000002", gene_index=genes)
    por_doenca = {d["database_id"]: d for d in alvo["diseases"]}
    assert por_doenca["OMIM:000001"]["genes"][0]["gene_symbol"] == "EDAR"
    assert por_doenca["OMIM:000001"]["has_mendelian_gene"] is True
    assert por_doenca["OMIM:000002"]["has_mendelian_gene"] is False
    assert por_doenca["OMIM:000004"]["genes"] == []
    assert alvo["genes"] == ["ATM", "EDAR", "EGR1"]
    assert alvo["mendelian_genes"] == ["EDAR"]


def test_sem_indice_de_genes_a_saida_declara_isso(anotacoes, ontologia) -> None:
    alvo = term_diseases(anotacoes, ontologia, "HP:0000002")
    assert alvo["filters"]["gene_source_linked"] is False
    assert alvo["genes"] == []


def test_filtro_mendeliano_conta_o_que_removeu(anotacoes, ontologia, genes) -> None:
    """O caso perigoso: o filtro tira o Orphanet inteiro e ninguem ve.

    ORPHA:000003 tem gene (ATM) e e monogenica no mundo real, mas a fonte
    nao classifica o tipo de associacao. O filtro a remove; o resultado
    precisa dizer que foi por isso.
    """
    alvo = term_diseases(
        anotacoes, ontologia, "HP:0000002", gene_index=genes, only_mendelian=True
    )
    assert [d["database_id"] for d in alvo["diseases"]] == ["OMIM:000001"]
    descartes = alvo["dropped_by_filter"]
    assert descartes["without_known_gene"] == 1
    assert descartes["with_gene_but_not_mendelian"] == 2
    assert descartes["of_which_source_does_not_classify"] == 1


def test_filtro_por_gene_conhecido(anotacoes, ontologia, genes) -> None:
    alvo = term_diseases(
        anotacoes, ontologia, "HP:0000002", gene_index=genes, only_with_gene=True
    )
    assert [d["database_id"] for d in alvo["diseases"]] == [
        "OMIM:000001", "OMIM:000002", "ORPHA:000003",
    ]
    assert alvo["summary"]["diseases_returned"] == 3


def test_saida_declara_que_nao_houve_expansao_por_ancestrais(anotacoes, ontologia) -> None:
    """Nenhum resultado desta versao pode ser lido como exaustivo."""
    alvo = term_diseases(anotacoes, ontologia, "HP:0000002")
    assert alvo["filters"]["ancestor_expansion"] is False
    assert any("descendente" in linha for linha in alvo["limitations"])


def test_frequencia_codificada_recebe_rotulo(ontologia) -> None:
    """Frequencia pode vir como termo HPO; exibir o codigo cru seria ruido."""
    ocasional = _conceito("HP:0040283", "Occasional", "Ocasional")
    ontologia = OntologyIndex({**ontologia.concepts, "HP:0040283": ocasional}, "teste")
    indice = HpoaIndex(
        hpo_release="2026-06-23",
        hpoa_version="2026-06-23",
        annotations=(
            HpoaAnnotation(
                database_id="OMIM:000001", disease_name="X", hpo_id="HP:0000002",
                aspect="P", excluded=False, frequency="HP:0040283", onset="",
                sex="", modifier="", evidence="PCS", reference="PMID:1", biocuration="",
            ),
        ),
    )
    alvo = term_diseases(indice, ontologia, "HP:0000002")
    assert alvo["diseases"][0]["frequency"] == "HP:0040283"
    assert alvo["diseases"][0]["frequency_label"] == "Ocasional"


def test_termo_sem_rotulo_portugues_e_marcado(anotacoes, ontologia) -> None:
    alvo = term_diseases(anotacoes, ontologia, "HP:0000003")
    assert alvo["label_pt_status"] == "unavailable"
    assert alvo["label_en"] == "Seizure"


def test_proveniencia_acompanha_o_resultado(anotacoes, ontologia) -> None:
    alvo = term_diseases(anotacoes, ontologia, "HP:0000002")
    assert alvo["provenance"] == {
        "hpo_release": "2026-06-23",
        "hpoa_version": "2026-06-23",
        "terminology_data_version": "teste-2026-06-23",
    }


def test_resultado_e_determinista(anotacoes, ontologia, genes) -> None:
    a = term_diseases(anotacoes, ontologia, "HP:0000002", gene_index=genes)
    b = term_diseases(anotacoes, ontologia, "HP:0000002", gene_index=genes)
    assert a == b


def test_indice_reverso_devolve_tudo_inclusive_o_not(anotacoes) -> None:
    """O primitivo nao filtra: quem interpreta e que separa."""
    citando = anotacoes.for_term("hp:0000002")
    assert len(citando) == 5
    assert sum(1 for a in citando if a.excluded) == 1
