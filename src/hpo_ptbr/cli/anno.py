"""`anno`: descreve, sem filtrar, os metadados de indivíduos do AADR."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..aadr_anno import describe_anno, write_manifest
from ._comum import AADR_ANNO_MANIFEST, _milhar, _rel


def command_anno(args: argparse.Namespace) -> int:
    path = Path(args.arquivo)
    if not path.is_file():
        print(f"Arquivo .anno ausente: {path}", file=sys.stderr)
        return 1
    try:
        description = describe_anno(path, source_url=args.url)
    except (OSError, UnicodeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1

    write_manifest(description, AADR_ANNO_MANIFEST)
    individual_counts = description["individual_counts"]
    current_records = description["current_records"]
    print(f"Arquivo AADR .anno: {path.name}")
    print(f"Registros (linhas): {_milhar(individual_counts['rows'])}")
    print(
        "Individual IDs distintos (não vazios): "
        f"{_milhar(individual_counts['distinct_nonempty_individual_ids'])}"
    )
    print(
        "Individual IDs em mais de uma linha: "
        f"{_milhar(individual_counts['individual_ids_in_multiple_rows'])}"
    )
    print(
        "Linhas com Individual ID vazio: "
        f"{_milhar(individual_counts['rows_with_empty_individual_id'])}"
    )
    print("Registros atuais (preservados, sem filtro):")
    print(
        f"  Date mean in BP = 0 : {_milhar(current_records['date_mean_bp_equals_0'])}"
    )
    print(
        f"  Full Date = present : {_milhar(current_records['full_date_equals_present'])}"
    )
    print(f"  ambos os campos     : {_milhar(current_records['both_fields'])}")
    print(f"Colunas: {description['column_count']}")
    for number, name in enumerate(description["columns"], start=1):
        print(f"  {number:02}. {name}")

    current_category = None
    for distribution in description["described_columns"]:
        category = distribution["category"]
        if category != current_category:
            print(f"\nDistribuições — {category.replace('_', ' ')}:")
            current_category = category
        print(
            f"  [{distribution['column_number']:02}] {distribution['column']}\n"
            f"       distintos={_milhar(distribution['distinct_values'])} · "
            f"vazios={_milhar(distribution['empty_values'])} · "
            f"ambíguos={_milhar(distribution['ambiguous_values'])} · "
            f"exibição={distribution['display_rule']}"
        )
        for item in distribution["value_counts"]:
            value = item["value"] if item["value"] else '<vazio>'
            print(f"       {_milhar(item['count']):>7}  {value}")

    print("\nFiltros aplicados: nenhum; linhas excluídas: 0")
    print(f"Manifesto: {_rel(AADR_ANNO_MANIFEST)}")
    return 0
