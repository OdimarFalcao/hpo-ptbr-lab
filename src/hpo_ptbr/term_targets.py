"""Caminho reverso: termo fenotípico -> doenças -> genes.

O `disease_profile` responde 'dada esta doença, que fenótipos ela
apresenta'. Este módulo responde a pergunta inversa, que é a que interessa
quando o ponto de partida é o achado e não o diagnóstico: 'dado este
fenótipo, que doenças o apresentam, e que genes estão por trás delas'.

Três decisões deste módulo merecem ser lidas antes de usar o resultado:

1. **Anotação com qualificador NOT não é ocorrência.** A HPO registra tanto
   'a doença X apresenta o fenótipo Y' quanto 'a doença X explicitamente
   NÃO apresenta Y'. As duas afirmações citam o mesmo termo. Somá-las
   produziria uma lista de doenças que inclui aquelas onde o achado foi
   descartado. Elas saem separadas, em `excluded_in`.

2. **Só anotação direta.** Nenhuma expansão por ancestrais nesta versão.
   Doença anotada em um termo filho do consultado não aparece aqui, e isso
   é uma limitação real de cobertura, não um detalhe: doença rara costuma
   ser anotada em termos muito específicos. O campo
   `ancestor_expansion` registra `False` para que nenhum resultado seja
   lido como exaustivo.

3. **O filtro monogênico descarta catálogo inteiro.** `association_type` só
   é preenchido pelo OMIM; todo o Orphanet chega como `UNKNOWN`. Filtrar
   por MENDELIAN remove essas doenças sem que isso signifique que não sejam
   monogênicas. O que o filtro tirou é contado e devolvido.
"""

from __future__ import annotations

from .gene_disease import MENDELIAN, ASSOCIATION_LABELS, GeneDiseaseIndex
from .hpoa import HpoaIndex, _describe_hpo_coded_field
from .ontology import OntologyIndex


def _genes_da_doenca(
    gene_index: GeneDiseaseIndex | None, disease_id: str
) -> list[dict[str, object]]:
    if gene_index is None:
        return []
    vistos: dict[str, dict[str, object]] = {}
    for association in gene_index.for_disease(disease_id):
        entrada = vistos.setdefault(
            association.gene_symbol,
            {
                "gene_symbol": association.gene_symbol,
                "ncbi_gene_id": association.ncbi_gene_id,
                "association_type": association.association_type,
                "association_label": ASSOCIATION_LABELS.get(
                    association.association_type, association.association_type
                ),
                "is_mendelian": association.association_type == MENDELIAN,
                "sources": [],
            },
        )
        if association.source not in entrada["sources"]:
            entrada["sources"].append(association.source)
    return [vistos[simbolo] for simbolo in sorted(vistos)]


def term_diseases(
    hpoa_index: HpoaIndex,
    ontology: OntologyIndex,
    hpo_id: str,
    *,
    gene_index: GeneDiseaseIndex | None = None,
    only_mendelian: bool = False,
    only_with_gene: bool = False,
) -> dict[str, object]:
    """Doenças que apresentam um termo fenotípico, com os genes associados.

    Levanta ValueError para termo ausente do vocabulário: identificador
    inexistente é erro de digitação, e lista vazia silenciosa o esconderia.
    Termo que existe mas nunca foi usado em anotação devolve lista vazia —
    isso é informação legítima sobre a curadoria, não falha.
    """
    concept = ontology.get(hpo_id.strip().upper())
    if concept is None:
        raise ValueError(
            f"Termo ausente do vocabulário desta release: {hpo_id}. "
            "Confira o identificador contra o snapshot terminológico em uso."
        )

    annotations = hpoa_index.for_term(concept.hpo_id)
    presentes = [a for a in annotations if not a.excluded]
    descartadas = [a for a in annotations if a.excluded]

    por_doenca: dict[str, dict[str, object]] = {}
    for annotation in presentes:
        entrada = por_doenca.setdefault(
            annotation.database_id,
            {
                "database_id": annotation.database_id,
                "disease_name": annotation.disease_name,
                "frequency": annotation.frequency,
                # Frequencia e inicio podem vir codificados como termo HPO
                # (HP:0040283 = "ocasional"). Exibir o codigo cru seria ruido.
                "frequency_label": _describe_hpo_coded_field(
                    annotation.frequency, ontology
                ),
                "onset": annotation.onset,
                "onset_label": _describe_hpo_coded_field(annotation.onset, ontology),
                "evidence": annotation.evidence,
                "reference": annotation.reference,
                "genes": _genes_da_doenca(gene_index, annotation.database_id),
            },
        )
        entrada["has_mendelian_gene"] = any(g["is_mendelian"] for g in entrada["genes"])
        entrada["has_gene"] = bool(entrada["genes"])

    diseases = [por_doenca[chave] for chave in sorted(por_doenca)]

    # O que os filtros removeram precisa ser contado antes de remover: o caso
    # perigoso e o filtro zerar o resultado sem que ninguem veja o porque.
    sem_gene = [d for d in diseases if not d["has_gene"]]
    sem_gene_mendeliano = [
        d for d in diseases if d["has_gene"] and not d["has_mendelian_gene"]
    ]
    nao_classificadas = [
        d
        for d in sem_gene_mendeliano
        if all(g["association_type"] == "UNKNOWN" for g in d["genes"])
    ]

    selecionadas = diseases
    if only_with_gene or only_mendelian:
        selecionadas = [d for d in selecionadas if d["has_gene"]]
    if only_mendelian:
        selecionadas = [d for d in selecionadas if d["has_mendelian_gene"]]

    genes_distintos = sorted(
        {g["gene_symbol"] for d in selecionadas for g in d["genes"]}
    )
    genes_mendelianos = sorted(
        {g["gene_symbol"] for d in selecionadas for g in d["genes"] if g["is_mendelian"]}
    )

    return {
        "schema_version": "hpo-ptbr-term-targets-v1",
        "hpo_id": concept.hpo_id,
        "label_pt": concept.label_pt,
        "label_en": concept.label_en,
        "label_pt_status": "official" if concept.label_pt else "unavailable",
        "in_phenotypic_tree": ontology.is_phenotypic_abnormality(concept.hpo_id),
        "filters": {
            "only_mendelian": only_mendelian,
            "only_with_gene": only_with_gene or only_mendelian,
            "ancestor_expansion": False,
            "gene_source_linked": gene_index is not None,
        },
        "provenance": {
            "hpo_release": hpoa_index.hpo_release,
            "hpoa_version": hpoa_index.hpoa_version,
            "terminology_data_version": ontology.data_version,
        },
        "summary": {
            "annotations_citing_term": len(annotations),
            "diseases_presenting": len(diseases),
            "diseases_returned": len(selecionadas),
            "diseases_excluding_term": len({a.database_id for a in descartadas}),
            "distinct_genes": len(genes_distintos),
            "distinct_mendelian_genes": len(genes_mendelianos),
        },
        "dropped_by_filter": {
            "without_known_gene": len(sem_gene),
            "with_gene_but_not_mendelian": len(sem_gene_mendeliano),
            "of_which_source_does_not_classify": len(nao_classificadas),
        },
        "diseases": selecionadas,
        "excluded_in": [
            {"database_id": a.database_id, "disease_name": a.disease_name}
            for a in sorted({(a.database_id, a.disease_name): a for a in descartadas}.values(),
                            key=lambda a: a.database_id)
        ],
        "genes": genes_distintos,
        "mendelian_genes": genes_mendelianos,
        "limitations": [
            "Apenas anotação direta: doença anotada em termo descendente não aparece.",
            "Anotação com qualificador NOT afirma ausência e sai em excluded_in, "
            "nunca somada às doenças que apresentam o termo.",
            "association_type só é preenchido por parte das fontes; UNKNOWN significa "
            "'a fonte não declara', nunca 'não é monogênica'.",
            "Associação curada gene-doença; não é evidência de causalidade em um indivíduo.",
        ],
    }
