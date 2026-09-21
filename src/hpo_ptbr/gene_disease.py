"""Associações gene <-> doença da HPO (`genes_to_disease.txt`).

Terceira fonte da mesma release:

- `hp.json`            -> vocabulário (quais conceitos existem)
- `phenotype.hpoa`     -> doença apresenta fenótipo
- `genes_to_disease`   -> gene está associado a doença, e de que forma

A coluna `association_type` é o que interessa ao recorte monogênico:
`MENDELIAN` marca as associações de herança mendeliana, que é exatamente a
classe de doença do objetivo específico (c) do projeto. `POLYGENIC` e
`UNKNOWN` ficam registrados mas são filtráveis.

Diferença importante em relação ao `phenotype.hpoa`: este arquivo **não traz
cabeçalho com a versão da HPO**. Não há como verificar a release pelo próprio
arquivo. A verificação possível é de consistência: qual proporção das doenças
citadas aqui existe no snapshot de anotações já ingerido. Uma sobreposição
baixa indica releases divergentes, e o valor fica registrado no manifesto
para inspeção — não é adivinhação disfarçada de garantia.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .hashing import content_sha256, raw_sha256

SOURCE_COLUMNS = ("ncbi_gene_id", "gene_symbol", "association_type", "disease_id", "source")
SNAPSHOT_COLUMNS = SOURCE_COLUMNS

ASSOCIATION_LABELS = {
    "MENDELIAN": "mendeliana (monogênica)",
    "POLYGENIC": "poligênica",
    "UNKNOWN": "não classificada",
}

MENDELIAN = "MENDELIAN"


@dataclass(frozen=True)
class GeneDiseaseAssociation:
    ncbi_gene_id: str
    gene_symbol: str
    association_type: str
    disease_id: str
    source: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class GeneDiseaseIndex:
    associations: tuple[GeneDiseaseAssociation, ...]

    def for_disease(self, disease_id: str) -> tuple[GeneDiseaseAssociation, ...]:
        wanted = disease_id.strip().upper()
        found = [a for a in self.associations if a.disease_id.upper() == wanted]
        return tuple(sorted(found, key=lambda a: (a.gene_symbol, a.association_type, a.source)))

    def for_gene(self, gene_symbol: str) -> tuple[GeneDiseaseAssociation, ...]:
        wanted = gene_symbol.strip().upper()
        found = [a for a in self.associations if a.gene_symbol.upper() == wanted]
        return tuple(sorted(found, key=lambda a: (a.disease_id, a.association_type, a.source)))

    def mendelian_disease_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted({a.disease_id for a in self.associations if a.association_type == MENDELIAN})
        )


def _read_rows(source: Path) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    lines = [
        line
        for line in source.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    if not lines:
        raise ValueError(f"Arquivo vazio: {source}")
    columns = tuple(lines[0].split("\t"))
    faltando = [c for c in SOURCE_COLUMNS if c not in columns]
    if faltando:
        raise ValueError(
            f"Colunas ausentes em {source.name}: {faltando}. "
            f"Cabeçalho encontrado: {columns}. "
            "Confirme que o arquivo é o genes_to_disease.txt da release em uso."
        )
    return columns, list(csv.DictReader(lines, delimiter="\t"))


def build_snapshot(
    source_path: str | Path,
    output_csv: str | Path,
    output_metadata: str | Path,
    *,
    known_disease_ids: frozenset[str] | None = None,
    source_url: str = "",
    output_csv_label: str = "",
) -> dict[str, object]:
    """Normaliza `genes_to_disease.txt` e grava o manifesto de proveniência."""
    source = Path(source_path)
    _, rows = _read_rows(source)

    associations = [
        GeneDiseaseAssociation(
            ncbi_gene_id=row["ncbi_gene_id"].strip(),
            gene_symbol=row["gene_symbol"].strip(),
            association_type=row["association_type"].strip().upper(),
            disease_id=row["disease_id"].strip(),
            source=row["source"].strip(),
        )
        for row in rows
        if row.get("disease_id", "").strip() and row.get("gene_symbol", "").strip()
    ]
    if not associations:
        raise ValueError("Nenhuma associação gene-doença válida encontrada.")

    associations.sort(key=lambda a: (a.disease_id, a.gene_symbol, a.association_type, a.source))

    csv_path = Path(output_csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SNAPSHOT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for association in associations:
            writer.writerow(association.to_dict())

    tipos: dict[str, int] = {}
    fontes: dict[str, int] = {}
    prefixos: dict[str, int] = {}
    for association in associations:
        tipos[association.association_type] = tipos.get(association.association_type, 0) + 1
        fontes[association.source] = fontes.get(association.source, 0) + 1
        prefixo = association.disease_id.split(":")[0]
        prefixos[prefixo] = prefixos.get(prefixo, 0) + 1

    mendelianas = {a.disease_id for a in associations if a.association_type == MENDELIAN}

    # `association_type` nao e preenchido por todas as fontes. Quantificar por
    # fonte evita que um filtro por MENDELIAN descarte um catalogo inteiro sem
    # que ninguem perceba.
    tipos_por_fonte: dict[str, dict[str, int]] = {}
    for association in associations:
        alvo = tipos_por_fonte.setdefault(association.source, {})
        alvo[association.association_type] = alvo.get(association.association_type, 0) + 1
    fontes_sem_classificacao = sorted(
        fonte for fonte, tipos in tipos_por_fonte.items() if set(tipos) == {"UNKNOWN"}
    )

    consistencia: dict[str, object] = {
        "checked_against_hpoa_snapshot": known_disease_ids is not None,
        "note": (
            "genes_to_disease.txt não declara a release da HPO. A verificação "
            "possível é de sobreposição de identificadores de doença com o "
            "snapshot de anotações. Sobreposição baixa indica releases divergentes."
        ),
    }
    if known_disease_ids is not None:
        citadas = {a.disease_id for a in associations}
        presentes = citadas & known_disease_ids
        consistencia |= {
            "diseases_cited": len(citadas),
            "also_present_in_hpoa_snapshot": len(presentes),
            "percent_overlap": round(100 * len(presentes) / len(citadas), 2),
        }

    manifest = {
        "schema_version": "gene-disease-snapshot-manifest-v1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source": {
            "url": source_url,
            "file": source.name,
            "sha256": raw_sha256(source),
            "declares_hpo_release": False,
        },
        "counts": {
            "associations": len(associations),
            "genes": len({a.gene_symbol for a in associations}),
            "diseases": len({a.disease_id for a in associations}),
            "by_association_type": dict(sorted(tipos.items())),
            "by_source": dict(sorted(fontes.items())),
            "by_disease_prefix": dict(sorted(prefixos.items())),
            "mendelian_diseases": len(mendelianas),
        },
        "association_type_caveat": {
            "by_source": {f: dict(sorted(t.items())) for f, t in sorted(tipos_por_fonte.items())},
            "sources_without_classification": fontes_sem_classificacao,
            "associations_unclassified": sum(
                n for tipos in tipos_por_fonte.values() for tipo, n in tipos.items() if tipo == "UNKNOWN"
            ),
            "note": (
                "association_type nao e preenchido por todas as fontes. Filtrar por "
                "MENDELIAN remove integralmente as fontes listadas em "
                "sources_without_classification, e isso nao significa que essas "
                "doencas nao sejam monogenicas: significa que a fonte nao declara. "
                "Um conjunto de doencas-alvo construido com esse filtro precisa registrar a "
                "exclusao como decisao, nao herda-la sem aviso."
            ),
        },
        "consistency": consistencia,
        "outputs": {
            "csv": output_csv_label or csv_path.name,
            "csv_sha256": content_sha256(csv_path),
        },
    }
    Path(output_metadata).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def load_snapshot(csv_path: str | Path) -> GeneDiseaseIndex:
    with Path(csv_path).open(encoding="utf-8", newline="") as handle:
        associations = tuple(
            GeneDiseaseAssociation(
                ncbi_gene_id=row["ncbi_gene_id"],
                gene_symbol=row["gene_symbol"],
                association_type=row["association_type"],
                disease_id=row["disease_id"],
                source=row["source"],
            )
            for row in csv.DictReader(handle)
        )
    if not associations:
        raise ValueError(f"Snapshot gene-doença vazio: {csv_path}")
    return GeneDiseaseIndex(associations)


def disease_genes(
    index: GeneDiseaseIndex,
    disease_id: str,
    *,
    only_mendelian: bool = False,
) -> dict[str, object]:
    """Genes associados a uma doença.

    Ausência de associação é informação legítima (nem toda doença catalogada
    tem gene conhecido) e não é erro: devolve lista vazia com a contagem em
    zero, para que o chamador possa distinguir 'sem gene conhecido' de
    'identificador errado' — este último é responsabilidade de quem valida o
    identificador contra o snapshot de anotações.
    """
    associations = index.for_disease(disease_id)
    descartadas_pelo_filtro = ()
    if only_mendelian:
        descartadas_pelo_filtro = tuple(
            a for a in associations if a.association_type != MENDELIAN
        )
        associations = tuple(a for a in associations if a.association_type == MENDELIAN)

    entries = [
        {
            "gene_symbol": a.gene_symbol,
            "ncbi_gene_id": a.ncbi_gene_id,
            "association_type": a.association_type,
            "association_label": ASSOCIATION_LABELS.get(
                a.association_type, a.association_type
            ),
            "is_mendelian": a.association_type == MENDELIAN,
            "source": a.source,
            "term_source": "HPO genes_to_disease.txt",
        }
        for a in associations
    ]
    return {
        "schema_version": "hpo-ptbr-disease-genes-v1",
        "disease_id": disease_id.strip().upper(),
        "only_mendelian": only_mendelian,
        "summary": {
            "genes": len({e["gene_symbol"] for e in entries}),
            "associations": len(entries),
            "mendelian": sum(1 for e in entries if e["is_mendelian"]),
        },
        "genes": entries,
        "filtered_out": [
            {
                "gene_symbol": a.gene_symbol,
                "association_type": a.association_type,
                "source": a.source,
                "reason": (
                    "fonte nao classifica o tipo de associacao"
                    if a.association_type == "UNKNOWN"
                    else "tipo de associacao diferente de MENDELIAN"
                ),
            }
            for a in descartadas_pelo_filtro
        ],
        "limitations": [
            "Associação curada gene-doença; não é evidência de causalidade em um indivíduo.",
            "Ausência de gene associado não significa ausência de base genética.",
            "O tipo de associação reflete a curadoria da fonte, não uma análise própria.",
            "association_type só é preenchido por parte das fontes; UNKNOWN significa "
            "'a fonte não declara', nunca 'não é monogênica'.",
        ],
    }
