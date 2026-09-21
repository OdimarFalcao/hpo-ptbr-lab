"""`panel`: caracteriza um .snp EIGENSTRAT e verifica o build declarado."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .. import genotype_panel
from ._comum import (
    PANEL_MANIFEST,
    _milhar,
    _rel,
)


def command_panel(args: argparse.Namespace) -> int:
    caminho = Path(args.snp)
    if not caminho.is_file():
        print(f"Arquivo .snp ausente: {caminho}", file=sys.stderr)
        return 1
    try:
        painel = genotype_panel.load_panel(caminho, args.build, panel_label=args.rotulo)
    except ValueError as erro:
        print(str(erro), file=sys.stderr)
        return 1

    manifesto = genotype_panel.build_manifest(
        caminho, painel, PANEL_MANIFEST, source_url=args.url
    )
    dados = manifesto["panel"]
    verificacao = manifesto["genome_build"]["verification"]
    simbolo = {"consistente": "verificado", "contradiz_declaracao": "CONTRADITO",
               "contraditorio": "CONTRADITORIO", "inconclusivo": "não verificável",
               "impossivel": "IMPOSSÍVEL"}[verificacao["verdict"]]
    print(f"Painel: {dados['label']}")
    print(f"  build declarado       : {manifesto['genome_build']['declared']}  ({simbolo})")
    print(f"  posições ensaiadas    : {_milhar(dados['assayed_positions'])}")
    print(f"  autossômicas          : {_milhar(dados['autosomal_positions'])}")
    print(f"  parece               : {dados['resembles_known_panel']}")
    por_cromossomo = dados["by_chromosome"]
    nao_autossomicos = {c: n for c, n in por_cromossomo.items() if not c.isdigit()}
    if nao_autossomicos:
        print(f"  não autossômicos      : {nao_autossomicos}")
    desconhecidos = manifesto["parsing"]["unknown_chromosome_codes"]
    if desconhecidos:
        print(f"  códigos não mapeados  : {desconhecidos} (contados, não descartados)")
    print("\nVerificação do build (evidência interna, sem consulta externa):")
    print(f"  {verificacao['explanation']}")
    print(f"\nManifesto: {_rel(PANEL_MANIFEST)}")
    if verificacao["verdict"] in {"contradiz_declaracao", "contraditorio", "impossivel"}:
        print(
            "\nO build declarado não sobrevive à verificação. Corrija antes de "
            "cruzar com qualquer outra fonte: interseção entre builds diferentes "
            "produz resultado numericamente válido e cientificamente falso.",
            file=sys.stderr,
        )
        return 1
    if verificacao["verdict"] == "inconclusivo":
        print(
            "\nO arquivo não permite verificar o build. Confirme na documentação "
            "do conjunto de dados antes de prosseguir."
        )
    return 0
