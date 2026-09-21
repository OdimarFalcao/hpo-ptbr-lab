"""`clinvar`: filtra o ClinVar para variantes patogênicas germinativas."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .. import clinvar
from ._comum import (
    CLINVAR_CSV,
    CLINVAR_MANIFEST,
    CLINVAR_SOURCE,
    CLINVAR_URL,
    _milhar,
    _rel,
)


def command_clinvar(args: argparse.Namespace) -> int:
    fonte = Path(args.arquivo) if args.arquivo else CLINVAR_SOURCE
    if not fonte.is_file():
        print(f"Fonte ausente: {fonte}", file=sys.stderr)
        print(f"Baixe de {CLINVAR_URL}", file=sys.stderr)
        print(f"e salve em {_rel(CLINVAR_SOURCE)}", file=sys.stderr)
        return 1
    print(f"Lendo {fonte.name} (arquivo grande, pode levar alguns minutos)...")
    try:
        manifesto = clinvar.build_snapshot(
            fonte, CLINVAR_CSV, CLINVAR_MANIFEST,
            genome_build=args.build,
            source_url=CLINVAR_URL,
            output_csv_label=_rel(CLINVAR_CSV),
            include_undeclared_origin=args.incluir_origem_desconhecida,
        )
    except ValueError as erro:
        print(str(erro), file=sys.stderr)
        return 1

    funil = manifesto["funnel"]
    excluidas = manifesto["excluded"]
    retidas = manifesto["retained"]
    print(f"\nClinVar  ->  {_rel(CLINVAR_CSV)}")
    print(f"  data de avaliação mais recente : {manifesto['source']['latest_last_evaluated']}")
    print(f"  coluna de classificação        : {manifesto['source']['significance_column']}")
    print("\nFunil:")
    print(f"  linhas lidas                   : {_milhar(funil['rows_read'])}")
    print(f"  no build {args.build:<21}: {_milhar(funil['rows_in_build'])}")
    print(f"  germinativas                   : {_milhar(funil['germline'])}")
    print(f"  patogênica / provável          : {_milhar(funil['pathogenic_or_likely'])}")
    print(f"  retidas                        : {_milhar(funil['retained'])}")
    print(f"\n  origens aceitas                           : {', '.join(manifesto['filters']['origin_accepted'])}")
    print(f"  excluídas por conflito entre submetedores : {_milhar(excluidas['conflicting_classifications'])}")
    for origem, n in excluidas["pathogenic_by_origin"].items():
        print(f"  patogênicas excluídas por origem '{origem}'{'':<{max(0, 8 - len(origem))}}: {_milhar(n)}")
    print(f"  SNV entre as retidas                      : {_milhar(retidas['snv'])}")
    print(f"  ligadas a OMIM/Orphanet                   : {_milhar(retidas['linked_to_omim_or_orphanet'])}")
    print(f"  sem vínculo com doença                    : {_milhar(retidas['without_disease_link'])}")
    print(f"  por estrelas de revisão                   : {retidas['by_review_stars']}")
    print(f"\nManifesto: {_rel(CLINVAR_MANIFEST)}")
    return 0
