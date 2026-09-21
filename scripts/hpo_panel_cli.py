"""CLI do painel de alvos fenotípicos.

    python scripts/hpo_panel_cli.py snapshot
    python scripts/hpo_panel_cli.py search "ectodermal dysplasia"
    python scripts/hpo_panel_cli.py profile OMIM:224900
    python scripts/hpo_panel_cli.py term HP:0001251
    python scripts/hpo_panel_cli.py panel data/raw/<painel>.snp --build GRCh37
    python scripts/hpo_panel_cli.py clinvar --build GRCh37
    python scripts/hpo_panel_cli.py coverage data/raw/<painel>.snp --build GRCh37

Ingere e consulta apenas dados versionados locais. Não baixa nada.
Sucessor de `hpoa_cli.py`, que cobria só o phenotype.hpoa.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hpo_ptbr import clinvar  # noqa: E402
from hpo_ptbr import gene_disease  # noqa: E402
from hpo_ptbr import genotype_panel  # noqa: E402
from hpo_ptbr import hpoa  # noqa: E402
from hpo_ptbr import target_coverage  # noqa: E402
from hpo_ptbr import term_targets  # noqa: E402
from hpo_ptbr.data import load_metadata  # noqa: E402
from hpo_ptbr.ontology import load_ontology_index  # noqa: E402

RELEASE_BASE = (
    "https://github.com/obophenotype/human-phenotype-ontology/releases/download/v2026-06-23"
)

HPOA_SOURCE = ROOT / "data/raw/phenotype.hpoa"
HPOA_CSV = ROOT / "data/processed/hpo_annotations.csv"
HPOA_MANIFEST = ROOT / "data/processed/hpoa_metadata.json"

GENES_SOURCE = ROOT / "data/raw/genes_to_disease.txt"
GENES_CSV = ROOT / "data/processed/gene_disease.csv"
GENES_MANIFEST = ROOT / "data/processed/gene_disease_metadata.json"

PANEL_MANIFEST = ROOT / "data/processed/genotype_panel_metadata.json"

CLINVAR_URL = "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz"
CLINVAR_SOURCE = ROOT / "data/raw/variant_summary.txt.gz"
CLINVAR_CSV = ROOT / "data/processed/clinvar_pathogenic.csv"
CLINVAR_MANIFEST = ROOT / "data/processed/clinvar_pathogenic_metadata.json"

COVERAGE_CSV = ROOT / "data/processed/target_coverage.csv"
COVERAGE_MANIFEST = ROOT / "data/processed/target_coverage_metadata.json"

ONTOLOGY_PATH = ROOT / "data/processed/hpo_ontology.json.gz"
METADATA_PATH = ROOT / "data/processed/metadata.json"

LIMIT_NOTE = (
    "Painel terminológico versionado. Não constitui diagnóstico, não substitui "
    "julgamento profissional e exige revisão antes de qualquer uso."
)


def _milhar(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _gene_id(valor: str) -> str:
    """O identificador ja vem prefixado (NCBIGene:10913); nao duplicar."""
    return valor if ":" in valor else f"NCBIGene:{valor}"


def _fonte_curta(valor: str) -> str:
    """As fontes vem como URL completa; exibir so o arquivo."""
    return valor.rstrip("/").rsplit("/", 1)[-1] or valor


def command_snapshot(args: argparse.Namespace) -> int:
    ontology = load_ontology_index(ONTOLOGY_PATH)

    if not HPOA_SOURCE.is_file():
        print(f"Fonte ausente: {_rel(HPOA_SOURCE)}", file=sys.stderr)
        print(f"Baixe de {RELEASE_BASE}/phenotype.hpoa", file=sys.stderr)
        return 1

    manifesto = hpoa.build_snapshot(
        HPOA_SOURCE,
        ontology,
        load_metadata(METADATA_PATH),
        HPOA_CSV,
        HPOA_MANIFEST,
        source_url=f"{RELEASE_BASE}/phenotype.hpoa",
        output_csv_label=_rel(HPOA_CSV),
    )
    contagens = manifesto["counts"]
    cobertura = manifesto["portuguese_coverage_of_annotated_phenotypes"]
    print(f"[1/2] anotações doença->fenótipo  ->  {_rel(HPOA_CSV)}")
    print(f"      release HPO declarada : {manifesto['source']['hpo_release_declared']}")
    print(f"      anotações / doenças   : {_milhar(contagens['annotations'])} / {_milhar(contagens['diseases'])}")
    print(f"      descartados (NOT)     : {contagens['excluded_qualifier_not']}")
    print(
        f"      cobertura PT          : {cobertura['with_official_pt_label']}/"
        f"{cobertura['phenotypic_terms_used']} ({cobertura['percent_with_pt_label']}%)"
    )

    if not GENES_SOURCE.is_file():
        print(f"\n[2/2] associações gene-doença: fonte ausente ({_rel(GENES_SOURCE)})")
        print(f"      Baixe de {RELEASE_BASE}/genes_to_disease.txt")
        return 0

    indice_hpoa = hpoa.load_snapshot(HPOA_CSV, HPOA_MANIFEST)
    manifesto_genes = gene_disease.build_snapshot(
        GENES_SOURCE,
        GENES_CSV,
        GENES_MANIFEST,
        known_disease_ids=frozenset(indice_hpoa.disease_ids()),
        source_url=f"{RELEASE_BASE}/genes_to_disease.txt",
        output_csv_label=_rel(GENES_CSV),
    )
    contagens = manifesto_genes["counts"]
    consistencia = manifesto_genes["consistency"]
    print(f"\n[2/2] associações gene-doença    ->  {_rel(GENES_CSV)}")
    print(f"      associações / genes   : {_milhar(contagens['associations'])} / {_milhar(contagens['genes'])}")
    print(f"      por tipo              : {contagens['by_association_type']}")
    print(f"      doenças mendelianas   : {_milhar(contagens['mendelian_diseases'])}")
    if "percent_overlap" in consistencia:
        print(
            f"      consistência          : {consistencia['percent_overlap']}% das doenças "
            f"citadas existem no snapshot de anotações"
        )
    return 0


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
    print(f"\nVerificação do build (evidência interna, sem consulta externa):")
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
    snvs_na_posicao = {
        (v.chromosome, v.position)
        for v in variantes
        if v.is_snv and painel.is_assayed(v.chromosome, v.position)
    }
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Painel de alvos fenotípicos, a partir de dados versionados locais."
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    sub.add_parser("snapshot", help="Normaliza as fontes presentes em data/raw e grava os manifestos.")

    painel = sub.add_parser(
        "panel", help="Caracteriza um painel de posições genotipadas (.snp EIGENSTRAT)."
    )
    painel.add_argument("snp", help="Caminho do arquivo .snp (formato EIGENSTRAT).")
    painel.add_argument(
        "--build",
        required=True,
        choices=list(genotype_panel.GENOME_BUILDS),
        help="Build do genoma do painel. Obrigatório: não é inferido do arquivo.",
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
        help="Build a reter. Precisa ser o mesmo do painel (AADR 1240K: GRCh37).",
    )
    variantes.add_argument(
        "--incluir-origem-desconhecida", action="store_true",
        help="Aceita também origem 'unknown'/'not provided' (padrão: só germinativa declarada).",
    )

    cobertura = sub.add_parser(
        "coverage", help="Cruza doenças-alvo, ClinVar e painel: de quantas doenças o painel fala."
    )
    cobertura.add_argument("snp", help="Caminho do arquivo .snp do painel.")
    cobertura.add_argument(
        "--build", required=True, choices=list(genotype_panel.GENOME_BUILDS),
        help="Build do painel. É verificado contra o arquivo.",
    )
    cobertura.add_argument("--rotulo", default="", help="Nome do painel no relatório.")
    cobertura.add_argument(
        "--estrelas-minimas", type=int, default=0, choices=[0, 1, 2, 3, 4],
        help="Estrelas de revisão mínimas no ClinVar (0 = todas).",
    )

    args = parser.parse_args()
    return {
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
