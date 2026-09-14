"""CLI das anotações doença -> fenótipo da HPO.

    python scripts/hpoa_cli.py snapshot
    python scripts/hpoa_cli.py search "ectodermal dysplasia"
    python scripts/hpoa_cli.py profile OMIM:224900

Executa apenas com dados versionados locais. Não baixa nada.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hpo_ptbr.data import load_metadata  # noqa: E402
from hpo_ptbr.hpoa import build_snapshot, disease_profile, load_snapshot  # noqa: E402
from hpo_ptbr.ontology import load_ontology_index  # noqa: E402

SOURCE_PATH = ROOT / "data/raw/phenotype.hpoa"
SOURCE_URL = (
    "https://github.com/obophenotype/human-phenotype-ontology/releases/"
    "download/v2026-06-23/phenotype.hpoa"
)
CSV_PATH = ROOT / "data/processed/hpo_annotations.csv"
MANIFEST_PATH = ROOT / "data/processed/hpoa_metadata.json"
ONTOLOGY_PATH = ROOT / "data/processed/hpo_ontology.json.gz"
METADATA_PATH = ROOT / "data/processed/metadata.json"

LIMIT_NOTE = (
    "Perfil terminológico versionado. Não constitui diagnóstico, não substitui "
    "julgamento profissional e exige revisão antes de qualquer uso."
)


def _ontology():
    return load_ontology_index(ONTOLOGY_PATH)


def command_snapshot(args: argparse.Namespace) -> int:
    if not SOURCE_PATH.is_file():
        print(f"Arquivo bruto ausente: {SOURCE_PATH}", file=sys.stderr)
        print(f"Baixe da release correspondente: {SOURCE_URL}", file=sys.stderr)
        return 1
    manifest = build_snapshot(
        SOURCE_PATH,
        _ontology(),
        load_metadata(METADATA_PATH),
        CSV_PATH,
        MANIFEST_PATH,
        source_url=SOURCE_URL,
        output_csv_label=CSV_PATH.relative_to(ROOT).as_posix(),
    )
    counts = manifest["counts"]
    cobertura = manifest["portuguese_coverage_of_annotated_phenotypes"]
    print(f"Snapshot HPOA gravado em {CSV_PATH.relative_to(ROOT).as_posix()}")
    print(f"  release HPO declarada : {manifest['source']['hpo_release_declared']}")
    print(f"  anotações             : {counts['annotations']:,}".replace(",", "."))
    print(f"  doenças               : {counts['diseases']:,}".replace(",", "."))
    print(f"  termos HPO            : {counts['hpo_terms']:,}".replace(",", "."))
    print(f"  por aspect            : {counts['by_aspect']}")
    print(f"  descartados (NOT)     : {counts['excluded_qualifier_not']}")
    print(
        f"  cobertura PT dos fenótipos anotados: "
        f"{cobertura['with_official_pt_label']}/{cobertura['phenotypic_terms_used']} "
        f"({cobertura['percent_with_pt_label']}%)"
    )
    return 0


def command_search(args: argparse.Namespace) -> int:
    index = load_snapshot(CSV_PATH, MANIFEST_PATH)
    results = index.search_diseases(args.termo, limit=args.limite)
    if not results:
        print(f"Nenhuma doença com '{args.termo}' no nome.")
        return 1
    for database_id, name in results:
        print(f"  {database_id:<16} {name}")
    print(f"\n{len(results)} resultado(s). Use o identificador com 'profile'.")
    return 0


def command_profile(args: argparse.Namespace) -> int:
    ontology = _ontology()
    index = load_snapshot(CSV_PATH, MANIFEST_PATH)
    try:
        profile = disease_profile(
            index, ontology, args.doenca, aspects=tuple(args.aspects)
        )
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(profile, ensure_ascii=False, indent=2))
        return 0

    resumo = profile["summary"]
    print(f"\n{profile['database_id']} — {profile['disease_name']}")
    print("=" * 96)
    cabecalho = (
        f"{'HPO ID':<13} {'rótulo':<46} {'freq.':<10} {'início':<14} {'?':<3}"
    )
    print(cabecalho)
    print("-" * 96)
    for entry in profile["annotations"]:
        if entry["label_pt_status"] == "official":
            rotulo = entry["label_pt"]
        else:
            rotulo = f"{entry['label_en']} [sem PT]"
        marca = "NÃO" if entry["excluded"] else ""
        print(
            f"{entry['hpo_id']:<13} {rotulo[:46]:<46} "
            f"{entry['frequency_label'][:10]:<10} {entry['onset_label'][:14]:<14} {marca:<3}"
        )
    print("-" * 96)
    print(
        f"{resumo['annotations']} anotações · {resumo['present']} presentes · "
        f"{resumo['excluded']} descartadas · "
        f"{resumo['with_official_pt_label']} com rótulo PT oficial · "
        f"{resumo['without_pt_label']} sem tradução"
    )
    proveniencia = profile["provenance"]
    print(
        f"\nFonte: HPO phenotype.hpoa {proveniencia['hpoa_version']} · "
        f"release HPO {proveniencia['hpo_release']} · "
        f"snapshot {proveniencia['terminology_data_version']}"
    )
    print(f"'NÃO' marca fenótipo explicitamente descartado nesta doença.")
    print(LIMIT_NOTE)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Anotações doença -> fenótipo da HPO, a partir de dados versionados locais."
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    sub.add_parser("snapshot", help="Normaliza data/raw/phenotype.hpoa e grava o manifesto.")

    busca = sub.add_parser("search", help="Procura doenças por substring do nome.")
    busca.add_argument("termo")
    busca.add_argument("--limite", type=int, default=20)

    perfil = sub.add_parser("profile", help="Perfil fenotípico de uma doença.")
    perfil.add_argument("doenca", help="Identificador, por exemplo OMIM:224900 ou ORPHA:238468.")
    perfil.add_argument(
        "--aspects",
        nargs="+",
        default=["P"],
        choices=["P", "C", "I", "M", "H"],
        help="P=fenótipo (padrão), C=curso clínico, I=herança, M=modificador, H=história pregressa.",
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
