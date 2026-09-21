"""`snapshot`: normaliza phenotype.hpoa e genes_to_disease.txt."""

from __future__ import annotations

import argparse
import sys

from .. import gene_disease, hpoa
from ..data import load_metadata
from ..ontology import load_ontology_index
from ._comum import (
    GENES_CSV,
    GENES_MANIFEST,
    GENES_SOURCE,
    HPOA_CSV,
    HPOA_MANIFEST,
    HPOA_SOURCE,
    METADATA_PATH,
    ONTOLOGY_PATH,
    RELEASE_BASE,
    _milhar,
    _rel,
)


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
