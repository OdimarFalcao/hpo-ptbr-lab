"""`coverage`: cruza doenças-alvo, ClinVar e painel genotipado."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .. import clinvar, gene_disease, genotype_panel, hpoa, target_coverage
from ._comum import (
    CLINVAR_CSV,
    CLINVAR_MANIFEST,
    COVERAGE_CSV,
    COVERAGE_MANIFEST,
    GENES_CSV,
    GENES_MANIFEST,
    HPOA_CSV,
    HPOA_MANIFEST,
    _milhar,
    _rel,
)


def command_coverage(args: argparse.Namespace) -> int:
    for exigido, como in (
        (HPOA_CSV, "rode 'snapshot'"),
        (GENES_CSV, "rode 'snapshot'"),
        (CLINVAR_CSV, "rode 'clinvar'"),
    ):
        if not exigido.is_file():
            print(f"Ausente: {_rel(exigido)} — {como} antes.", file=sys.stderr)
            return 1
    caminho_snp = Path(args.snp)
    if not caminho_snp.is_file():
        print(f"Arquivo .snp ausente: {caminho_snp}", file=sys.stderr)
        return 1

    manifesto_clinvar = json.loads(CLINVAR_MANIFEST.read_text(encoding="utf-8"))
    build_variantes = manifesto_clinvar["genome_build"]["declared"]
    ampliado = manifesto_clinvar["filters"].get("include_undeclared_origin", False)
    # Cada recorte do ClinVar grava em arquivo proprio: rodar o ampliado nao
    # apaga o conservador, e os dois podem ser comparados.
    sufixo = "_origem_ampliada" if ampliado else ""
    saida_csv = COVERAGE_CSV.with_name(f"target_coverage{sufixo}.csv")
    saida_manifesto = COVERAGE_MANIFEST.with_name(f"target_coverage{sufixo}_metadata.json")

    print("Carregando painel...")
    painel = genotype_panel.load_panel(caminho_snp, args.build, panel_label=args.rotulo)
    verificacao = genotype_panel.verify_declared_build(painel)
    if verificacao["verdict"] in {"contradiz_declaracao", "contraditorio", "impossivel"}:
        print(f"Build do painel não sobrevive à verificação: {verificacao['explanation']}",
              file=sys.stderr)
        return 1

    print("Carregando anotações, genes e variantes...")
    variantes = clinvar.load_snapshot(CLINVAR_CSV)
    snvs_na_posicao = target_coverage.snv_positions_on_panel(variantes, painel)
    print(f"Lendo alelos do painel em {_milhar(len(snvs_na_posicao))} posições...")
    alelos = genotype_panel.read_panel_alleles(caminho_snp, snvs_na_posicao)

    try:
        resultado = target_coverage.assess_targets(
            hpoa.load_snapshot(HPOA_CSV, HPOA_MANIFEST),
            gene_disease.load_snapshot(GENES_CSV),
            variantes,
            build_variantes,
            painel,
            alelos,
            min_review_stars=args.estrelas_minimas,
        )
    except ValueError as erro:
        print(str(erro), file=sys.stderr)
        return 1

    manifesto = target_coverage.write_report(
        resultado, saida_csv, saida_manifesto,
        sources={
            "hpoa_manifest": _rel(HPOA_MANIFEST),
            "gene_disease_manifest": _rel(GENES_MANIFEST),
            "clinvar_manifest": _rel(CLINVAR_MANIFEST),
            "clinvar_sha256": manifesto_clinvar["source"]["sha256"],
            "clinvar_origin_accepted": manifesto_clinvar["filters"]["origin_accepted"],
            "panel_file": caminho_snp.name,
            "panel_build_verification": verificacao["verdict"],
        },
        output_csv_label=_rel(saida_csv),
    )

    v = manifesto["variants"]
    print(f"\nPainel {painel.panel_label} ({painel.genome_build}, {verificacao['verdict']})"
          f" × ClinVar ({build_variantes})"
          + (f" · mínimo {args.estrelas_minimas} estrela(s)" if args.estrelas_minimas else "")
          + (" · origem ampliada" if ampliado else " · só germinativa declarada"))
    print("=" * 96)
    print("VARIANTES")
    print(f"  patogênicas germinativas retidas : {_milhar(v['pathogenic_retained'])}")
    print(f"  SNV consideradas                 : {_milhar(v['snv_considered'])}")
    print(f"  SNV em posição ensaiada          : {_milhar(v['snv_at_panel_position'])}")
    print(f"    alelo patogênico ensaiado      : {_milhar(v['allele_match'])}")
    print(f"    casa pela fita oposta          : {_milhar(v['strand_flip_match'])}")
    print(f"    posição certa, alelo diferente : {_milhar(v['different_alleles'])}")

    for chave, titulo in (
        ("mendelian_declared_by_omim", "DOENÇAS COM GENE MENDELIANO DECLARADO (OMIM)"),
        ("any_gene_association", "DOENÇAS COM QUALQUER GENE ASSOCIADO (inclui Orphanet)"),
    ):
        universo = manifesto["universes"][chave]
        total = universo["diseases"]
        print(f"\n{titulo}: {_milhar(total)}")
        for nivel in target_coverage.TIERS:
            n = universo["by_tier"][nivel]
            pct = f"{100 * n / total:5.1f}%" if total else "   - "
            print(f"  {target_coverage.TIER_LABELS[nivel]:<44} {_milhar(n):>7}  {pct}")

    print("\nO nível de cada doença é o mais fundo que ela alcança; só o último permite")
    print("perguntar se um indivíduo antigo carrega a variante patogênica.")
    print(f"\nPor doença: {_rel(saida_csv)}")
    print(f"Manifesto : {_rel(saida_manifesto)}")
    for limite in manifesto["limitations"]:
        print(f"  - {limite}")
    return 0
