"""CLI do painel de alvos fenotípicos.

    python scripts/hpo_panel_cli.py snapshot
    python scripts/hpo_panel_cli.py search "ectodermal dysplasia"
    python scripts/hpo_panel_cli.py profile OMIM:224900

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

from hpo_ptbr import gene_disease  # noqa: E402
from hpo_ptbr import hpoa  # noqa: E402
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Painel de alvos fenotípicos, a partir de dados versionados locais."
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    sub.add_parser("snapshot", help="Normaliza as fontes presentes em data/raw e grava os manifestos.")

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

    args = parser.parse_args()
    return {
        "snapshot": command_snapshot,
        "search": command_search,
        "profile": command_profile,
    }[args.comando](args)


if __name__ == "__main__":
    raise SystemExit(main())
