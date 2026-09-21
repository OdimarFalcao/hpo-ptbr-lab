"""`search`, `profile` e `term`: consultas sobre os snapshots."""

from __future__ import annotations

import argparse
import json
import sys

from .. import gene_disease, hpoa, term_targets
from ..ontology import load_ontology_index
from ._comum import (
    GENES_CSV,
    HPOA_CSV,
    HPOA_MANIFEST,
    LIMIT_NOTE,
    ONTOLOGY_PATH,
    _fonte_curta,
    _gene_id,
)


def command_search(args: argparse.Namespace) -> int:
    indice = hpoa.load_snapshot(HPOA_CSV, HPOA_MANIFEST)
    resultados = indice.search_diseases(args.termo, limit=args.limite)
    if not resultados:
        print(f"Nenhuma doença com '{args.termo}' no nome.")
        return 1
    genes = gene_disease.load_snapshot(GENES_CSV) if GENES_CSV.is_file() else None
    for database_id, nome in resultados:
        simbolos = ""
        if genes is not None:
            associados = sorted({a.gene_symbol for a in genes.for_disease(database_id)})
            if associados:
                simbolos = "  [" + ", ".join(associados[:4]) + ("…" if len(associados) > 4 else "") + "]"
        print(f"  {database_id:<16} {nome}{simbolos}")
    print(f"\n{len(resultados)} resultado(s). Use o identificador com 'profile'.")
    return 0


def command_profile(args: argparse.Namespace) -> int:
    ontology = load_ontology_index(ONTOLOGY_PATH)
    indice = hpoa.load_snapshot(HPOA_CSV, HPOA_MANIFEST)
    try:
        perfil = hpoa.disease_profile(indice, ontology, args.doenca, aspects=tuple(args.aspects))
    except ValueError as erro:
        print(str(erro), file=sys.stderr)
        return 1

    perfil_genes = None
    if GENES_CSV.is_file():
        perfil_genes = gene_disease.disease_genes(
            gene_disease.load_snapshot(GENES_CSV),
            perfil["database_id"],
            only_mendelian=args.somente_mendelianas,
        )
        perfil["genes"] = perfil_genes

    if args.json:
        print(json.dumps(perfil, ensure_ascii=False, indent=2))
        return 0

    print(f"\n{perfil['database_id']} — {perfil['disease_name']}")
    print("=" * 96)

    if perfil_genes is not None:
        print("GENES ASSOCIADOS")
        if perfil_genes["genes"]:
            for entrada in perfil_genes["genes"]:
                marca = "monogênica" if entrada["is_mendelian"] else entrada["association_label"]
                print(
                    f"  {entrada['gene_symbol']:<14} {_gene_id(entrada['ncbi_gene_id']):<20} "
                    f"{marca:<22} {_fonte_curta(entrada['source'])}"
                )
        elif not perfil_genes.get("filtered_out"):
            print("  nenhum gene associado nesta fonte")
        # O aviso precisa aparecer inclusive quando o filtro descartou tudo:
        # e justamente o caso em que a omissao passaria despercebida.
        for descartada in perfil_genes.get("filtered_out") or []:
            print(
                f"  {descartada['gene_symbol']:<14} {'omitido pelo filtro':<20} "
                f"{descartada['association_type']:<22} {descartada['reason']}"
            )
        print()

    print("FENÓTIPOS")
    print(f"{'HPO ID':<13} {'rótulo':<46} {'freq.':<10} {'início':<14} {'?':<3}")
    print("-" * 96)
    for entrada in perfil["annotations"]:
        rotulo = (
            entrada["label_pt"]
            if entrada["label_pt_status"] == "official"
            else f"{entrada['label_en']} [sem PT]"
        )
        marca = "NÃO" if entrada["excluded"] else ""
        print(
            f"{entrada['hpo_id']:<13} {rotulo[:46]:<46} "
            f"{entrada['frequency_label'][:10]:<10} {entrada['onset_label'][:14]:<14} {marca:<3}"
        )
    print("-" * 96)

    resumo = perfil["summary"]
    linha = (
        f"{resumo['annotations']} anotações · {resumo['present']} presentes · "
        f"{resumo['excluded']} descartadas · {resumo['with_official_pt_label']} com PT · "
        f"{resumo['without_pt_label']} sem tradução"
    )
    if perfil_genes is not None:
        linha += f" · {perfil_genes['summary']['genes']} gene(s)"
    print(linha)

    proveniencia = perfil["provenance"]
    print(
        f"\nFonte: HPO phenotype.hpoa {proveniencia['hpoa_version']}"
        + (" + genes_to_disease.txt" if perfil_genes is not None else "")
        + f" · release HPO {proveniencia['hpo_release']}"
        + f" · snapshot {proveniencia['terminology_data_version']}"
    )
    print("'NÃO' marca fenótipo explicitamente descartado nesta doença.")
    print(LIMIT_NOTE)
    return 0


def command_term(args: argparse.Namespace) -> int:
    ontology = load_ontology_index(ONTOLOGY_PATH)
    indice = hpoa.load_snapshot(HPOA_CSV, HPOA_MANIFEST)
    genes = gene_disease.load_snapshot(GENES_CSV) if GENES_CSV.is_file() else None
    try:
        alvo = term_targets.term_diseases(
            indice,
            ontology,
            args.termo,
            gene_index=genes,
            only_mendelian=args.somente_mendelianas,
            only_with_gene=args.somente_com_gene,
        )
    except ValueError as erro:
        print(str(erro), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(alvo, ensure_ascii=False, indent=2))
        return 0

    rotulo = (
        alvo["label_pt"] if alvo["label_pt_status"] == "official"
        else f"{alvo['label_en']} [sem PT]"
    )
    print(f"\n{alvo['hpo_id']} — {rotulo}")
    if alvo["label_pt_status"] == "official":
        print(f"{'':13}  ({alvo['label_en']})")
    print("=" * 96)

    resumo = alvo["summary"]
    if not alvo["diseases"]:
        if resumo["diseases_presenting"] == 0:
            print("Nenhuma doença anotada com este termo nesta release.")
            print("O termo existe no vocabulário; simplesmente não foi usado em anotação.")
        else:
            print(
                f"{resumo['diseases_presenting']} doença(s) apresentam o termo, "
                "mas nenhuma sobreviveu aos filtros aplicados."
            )
    else:
        print(f"{'doença':<16} {'nome':<40} {'freq.':<13} genes")
        print("-" * 96)
        for doenca in alvo["diseases"][: args.limite]:
            simbolos = [
                g["gene_symbol"] + ("" if g["is_mendelian"] else "*")
                for g in doenca["genes"]
            ]
            lista = ", ".join(simbolos[:4]) + ("…" if len(simbolos) > 4 else "")
            print(
                f"{doenca['database_id']:<16} {doenca['disease_name'][:40]:<40} "
                f"{doenca['frequency_label'][:13]:<13} {lista}"
            )
        print("-" * 96)
        if len(alvo["diseases"]) > args.limite:
            print(f"... {len(alvo['diseases']) - args.limite} doença(s) além do limite de exibição.")
        print("* associação não classificada como mendeliana pela fonte.")

    print(
        f"\n{resumo['diseases_presenting']} doença(s) apresentam · "
        f"{resumo['diseases_returned']} após filtros · "
        f"{resumo['distinct_genes']} gene(s) distintos "
        f"({resumo['distinct_mendelian_genes']} mendeliano(s))"
    )

    # O que os filtros tiraram e a informacao que decide se o recorte faz
    # sentido; omiti-la transformaria um filtro em um resultado.
    descartes = alvo["dropped_by_filter"]
    if alvo["filters"]["only_with_gene"] and descartes["without_known_gene"]:
        print(f"  {descartes['without_known_gene']} sem gene conhecido nesta fonte")
    if alvo["filters"]["only_mendelian"] and descartes["with_gene_but_not_mendelian"]:
        print(
            f"  {descartes['with_gene_but_not_mendelian']} com gene não mendeliano, "
            f"das quais {descartes['of_which_source_does_not_classify']} apenas porque "
            "a fonte não classifica o tipo de associação (todo o Orphanet chega assim)"
        )
    if resumo["diseases_excluding_term"]:
        print(
            f"  {resumo['diseases_excluding_term']} doença(s) descartam explicitamente "
            "este fenótipo (qualificador NOT) e não entram na lista"
        )

    print(
        "\nApenas anotação direta: doença anotada num termo descendente deste "
        "não aparece. A expansão por ancestrais ainda não está implementada."
    )
    proveniencia = alvo["provenance"]
    print(
        f"Fonte: HPO phenotype.hpoa {proveniencia['hpoa_version']}"
        + (" + genes_to_disease.txt" if alvo["filters"]["gene_source_linked"] else "")
        + f" · release HPO {proveniencia['hpo_release']}"
        + f" · snapshot {proveniencia['terminology_data_version']}"
    )
    print(LIMIT_NOTE)
    return 0
