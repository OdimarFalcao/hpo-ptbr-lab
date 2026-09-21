"""Ponto de entrada da CLI: `alcance <comando>` ou `python -m hpo_ptbr.cli`.

Este arquivo só declara os argumentos e despacha. Cada comando vive no seu
módulo; o cálculo vive nos módulos de `hpo_ptbr`, onde é testado.
"""

from __future__ import annotations

import argparse

from .. import genotype_panel
from ._comum import AADR_ANNO_URL
from .anno import command_anno
from .cobertura import command_coverage
from .consulta import command_profile, command_search, command_term
from .painel import command_panel
from .snapshot import command_snapshot
from .variantes import command_clinvar


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="alcance",
        description=(
            "Alcance Genômico: de quais doenças monogênicas os dados de DNA antigo "
            "permitem perguntar. Usa só dados versionados locais."
        ),
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    sub.add_parser("snapshot", help="Normaliza as fontes presentes em data/raw e grava os manifestos.")

    anno = sub.add_parser(
        "anno", help="Descreve as colunas e os valores do arquivo .anno do AADR, sem filtrar."
    )
    anno.add_argument("arquivo", help="Caminho do arquivo .anno do AADR.")
    anno.add_argument("--url", default=AADR_ANNO_URL, help="URL de origem, para proveniência.")

    painel = sub.add_parser(
        "panel", help="Caracteriza um painel de genotipagem (.snp EIGENSTRAT) e verifica o build."
    )
    painel.add_argument("snp", help="Caminho do arquivo .snp (formato EIGENSTRAT).")
    painel.add_argument(
        "--build",
        required=True,
        choices=list(genotype_panel.GENOME_BUILDS),
        help="Build do genoma do painel de genotipagem. Obrigatório: não é inferido do arquivo.",
    )
    painel.add_argument("--rotulo", default="", help="Nome do painel no manifesto.")
    painel.add_argument("--url", default="", help="URL de origem, para proveniência.")

    busca = sub.add_parser("search", help="Procura doenças por substring do nome.")
    busca.add_argument("termo")
    busca.add_argument("--limite", type=int, default=20)

    perfil = sub.add_parser("profile", help="Perfil de uma doença: genes e fenótipos.")
    perfil.add_argument("doenca", help="Identificador, por exemplo OMIM:224900 ou ORPHA:238468.")
    perfil.add_argument(
        "--aspects",
        nargs="+",
        default=["P"],
        choices=["P", "C", "I", "M", "H"],
        help="P=fenótipo (padrão), C=curso clínico, I=herança, M=modificador, H=história pregressa.",
    )
    perfil.add_argument(
        "--somente-mendelianas",
        action="store_true",
        help="Mostra apenas associações gene-doença de herança mendeliana.",
    )
    perfil.add_argument("--json", action="store_true", help="Saída em JSON.")

    termo = sub.add_parser(
        "term", help="Caminho inverso: dado um termo HPO, quais doenças e genes."
    )
    termo.add_argument("termo", help="Identificador HPO, por exemplo HP:0001249.")
    termo.add_argument(
        "--somente-mendelianas",
        action="store_true",
        help="Só doenças com gene classificado como mendeliano pela fonte.",
    )
    termo.add_argument(
        "--somente-com-gene",
        action="store_true",
        help="Só doenças com algum gene associado, de qualquer tipo.",
    )
    termo.add_argument("--limite", type=int, default=30, help="Doenças exibidas (padrão 30).")
    termo.add_argument("--json", action="store_true", help="Saída em JSON.")

    variantes = sub.add_parser(
        "clinvar", help="Filtra o ClinVar para variantes patogênicas germinativas num build."
    )
    variantes.add_argument(
        "arquivo", nargs="?", default="",
        help="Caminho do variant_summary.txt.gz (padrão: data/raw/variant_summary.txt.gz).",
    )
    variantes.add_argument(
        "--build", required=True, choices=list(genotype_panel.GENOME_BUILDS),
        help="Build a reter. Precisa ser o mesmo do painel de genotipagem (AADR 1240K: GRCh37).",
    )
    variantes.add_argument(
        "--incluir-origem-desconhecida", action="store_true",
        help="Aceita também origem 'unknown'/'not provided' (padrão: só germinativa declarada).",
    )

    cobertura = sub.add_parser(
        "coverage", help="Cruza doenças-alvo, ClinVar e painel de genotipagem: de quantas doenças dá para perguntar."
    )
    cobertura.add_argument("snp", help="Caminho do arquivo .snp do painel de genotipagem.")
    cobertura.add_argument(
        "--build", required=True, choices=list(genotype_panel.GENOME_BUILDS),
        help="Build do painel de genotipagem. É verificado contra o arquivo.",
    )
    cobertura.add_argument("--rotulo", default="", help="Nome do painel no relatório.")
    cobertura.add_argument(
        "--estrelas-minimas", type=int, default=0, choices=[0, 1, 2, 3, 4],
        help="Estrelas de revisão mínimas no ClinVar (0 = todas).",
    )

    args = parser.parse_args()
    return {
        "anno": command_anno,
        "clinvar": command_clinvar,
        "coverage": command_coverage,
        "snapshot": command_snapshot,
        "panel": command_panel,
        "search": command_search,
        "profile": command_profile,
        "term": command_term,
    }[args.comando](args)


if __name__ == "__main__":
    raise SystemExit(main())
