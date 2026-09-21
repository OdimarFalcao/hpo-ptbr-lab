"""Anotações doença -> fenótipo da HPO (`phenotype.hpoa`).

O `hp.json` fornece o vocabulário: quais conceitos existem e como se
relacionam. O `phenotype.hpoa` fornece as afirmações: quais fenótipos
aparecem em cada doença, com que frequência, em que idade de início, com
que evidência e sob qual referência bibliográfica.

Este módulo faz duas coisas e nada além:

1. `build_snapshot` normaliza o arquivo bruto num CSV versionado, com
   manifesto de proveniência, recusando o arquivo se a release da HPO
   declarada no cabeçalho divergir do snapshot terminológico em uso.
2. `disease_profile` devolve o perfil fenotípico de uma doença, enriquecido
   com os rótulos do índice ontológico e com o status de tradução de cada
   termo.

Nada aqui inventa tradução. Conceito sem rótulo português oficial recebe
`label_pt_status = "unavailable"` e é apresentado pelo rótulo inglês, com a
fonte declarada.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .hashing import content_sha256, raw_sha256
from .ontology import OntologyIndex

HPOA_SOURCE_COLUMNS = (
    "database_id",
    "disease_name",
    "qualifier",
    "hpo_id",
    "reference",
    "evidence",
    "onset",
    "frequency",
    "sex",
    "modifier",
    "aspect",
    "biocuration",
)

SNAPSHOT_COLUMNS = (
    "database_id",
    "disease_name",
    "hpo_id",
    "aspect",
    "excluded",
    "frequency",
    "onset",
    "sex",
    "modifier",
    "evidence",
    "reference",
    "biocuration",
)

# `aspect` na HPOA. P é exatamente a subárvore de HP:0000118.
ASPECT_LABELS = {
    "P": "anormalidade fenotípica",
    "C": "curso clínico",
    "I": "modo de herança",
    "M": "modificador clínico",
    "H": "história médica pregressa",
}
ASPECT_ORDER = {"P": 0, "C": 1, "M": 2, "I": 3, "H": 4}

EVIDENCE_LABELS = {
    "IEA": "inferido por anotação eletrônica",
    "PCS": "estudo de caso publicado",
    "TAS": "afirmação rastreável do autor",
    "ICE": "evidência clínica individual",
}

_RELEASE_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_HPO_ID = re.compile(r"^HP:\d{7}$")


@dataclass(frozen=True)
class HpoaAnnotation:
    """Uma afirmação 'doença X apresenta fenótipo Y'."""

    database_id: str
    disease_name: str
    hpo_id: str
    aspect: str
    excluded: bool
    frequency: str
    onset: str
    sex: str
    modifier: str
    evidence: str
    reference: str
    biocuration: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class HpoaIndex:
    hpo_release: str
    hpoa_version: str
    annotations: tuple[HpoaAnnotation, ...]

    def disease_ids(self) -> tuple[str, ...]:
        return tuple(sorted({a.database_id for a in self.annotations}))

    def disease_name(self, database_id: str) -> str | None:
        for annotation in self.annotations:
            if annotation.database_id == database_id:
                return annotation.disease_name
        return None

    def for_term(self, hpo_id: str) -> tuple[HpoaAnnotation, ...]:
        """Índice reverso: quais doenças citam este termo.

        Devolve inclusive as anotações com `excluded=True` (qualificador NOT),
        que afirmam o contrário — 'esta doença não apresenta este fenótipo'.
        Filtrá-las aqui esconderia do chamador uma afirmação que existe na
        fonte; separá-las é responsabilidade de quem interpreta.
        """
        wanted = hpo_id.strip().upper()
        found = [a for a in self.annotations if a.hpo_id.upper() == wanted]
        return tuple(sorted(found, key=lambda a: (a.database_id, a.evidence, a.reference)))

    def search_diseases(self, term: str, limit: int = 20) -> list[tuple[str, str]]:
        """Busca por substring no nome da doença. Determinística."""
        needle = term.strip().casefold()
        if not needle:
            return []
        found: dict[str, str] = {}
        for annotation in self.annotations:
            if needle in annotation.disease_name.casefold():
                found.setdefault(annotation.database_id, annotation.disease_name)
        return sorted(found.items())[:limit]


def read_source_header(path: str | Path) -> dict[str, str]:
    """Lê os comentários `#chave: valor` do topo do arquivo bruto."""
    header: dict[str, str] = {}
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.startswith("#"):
                break
            if ":" in line:
                key, _, value = line[1:].partition(":")
                header[key.strip()] = value.strip()
    if "hpo-version" not in header:
        raise ValueError(
            "Arquivo HPOA sem '#hpo-version' no cabeçalho: não é possível "
            "verificar a compatibilidade com o snapshot terminológico."
        )
    return header


def declared_hpo_release(header: dict[str, str]) -> str:
    match = _RELEASE_DATE.search(header["hpo-version"])
    if match is None:
        raise ValueError(
            f"Não foi possível extrair a data da release de "
            f"'{header['hpo-version']}'."
        )
    return match.group(1)


def build_snapshot(
    source_path: str | Path,
    ontology: OntologyIndex,
    metadata: dict[str, object],
    output_csv: str | Path,
    output_metadata: str | Path,
    source_url: str = "",
    output_csv_label: str = "",
) -> dict[str, object]:
    """Normaliza `phenotype.hpoa` e grava o manifesto de proveniência.

    Recusa o arquivo se a release da HPO declarada no cabeçalho divergir da
    release do snapshot terminológico: perfis fenotípicos de uma release não
    podem ser lidos com o vocabulário de outra.
    """
    source = Path(source_path)
    header = read_source_header(source)
    release = declared_hpo_release(header)
    expected = str(metadata["hpo_release"])
    if release != expected:
        raise ValueError(
            f"HPOA declara a release {release}, mas o snapshot terminológico "
            f"em uso é {expected}. Baixe o phenotype.hpoa da mesma release."
        )

    lines = source.read_text(encoding="utf-8").splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.startswith("database_id"))
    except StopIteration as error:
        raise ValueError("Arquivo HPOA sem linha de cabeçalho de colunas.") from error

    columns = tuple(lines[start].split("\t"))
    if columns != HPOA_SOURCE_COLUMNS:
        raise ValueError(
            f"Colunas inesperadas no HPOA: {columns}. Esperado: {HPOA_SOURCE_COLUMNS}."
        )

    annotations: list[HpoaAnnotation] = []
    unknown_terms: set[str] = set()
    for row in csv.DictReader(lines[start:], delimiter="\t"):
        hpo_id = row["hpo_id"].strip()
        if not _HPO_ID.match(hpo_id):
            continue
        if hpo_id not in ontology.concepts:
            unknown_terms.add(hpo_id)
            continue
        annotations.append(
            HpoaAnnotation(
                database_id=row["database_id"].strip(),
                disease_name=row["disease_name"].strip(),
                hpo_id=hpo_id,
                aspect=row["aspect"].strip(),
                excluded=row["qualifier"].strip().upper() == "NOT",
                frequency=row["frequency"].strip(),
                onset=row["onset"].strip(),
                sex=row["sex"].strip(),
                modifier=row["modifier"].strip(),
                evidence=row["evidence"].strip(),
                reference=row["reference"].strip(),
                biocuration=row["biocuration"].strip(),
            )
        )

    if not annotations:
        raise ValueError("Nenhuma anotação válida encontrada no HPOA.")

    annotations.sort(
        key=lambda a: (a.database_id, ASPECT_ORDER.get(a.aspect, 9), a.hpo_id)
    )

    csv_path = Path(output_csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=SNAPSHOT_COLUMNS, lineterminator="\n"
        )
        writer.writeheader()
        for annotation in annotations:
            record = annotation.to_dict()
            record["excluded"] = "true" if annotation.excluded else "false"
            writer.writerow(record)

    used_p = {a.hpo_id for a in annotations if a.aspect == "P"}
    translated = {h for h in used_p if ontology.concepts[h].label_pt}
    aspect_counts: dict[str, int] = {}
    for annotation in annotations:
        aspect_counts[annotation.aspect] = aspect_counts.get(annotation.aspect, 0) + 1

    manifest = {
        "schema_version": "hpoa-snapshot-manifest-v1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source": {
            "url": source_url,
            "file": source.name,
            "sha256": raw_sha256(source),
            "hpoa_version": header.get("version", ""),
            "hpo_release_declared": release,
            "description": header.get("description", ""),
        },
        "terminology_snapshot": {
            "data_version": ontology.data_version,
            "hpo_release": expected,
        },
        "counts": {
            "annotations": len(annotations),
            "diseases": len({a.database_id for a in annotations}),
            "hpo_terms": len({a.hpo_id for a in annotations}),
            "by_aspect": dict(sorted(aspect_counts.items())),
            "excluded_qualifier_not": sum(1 for a in annotations if a.excluded),
            "terms_absent_from_terminology_snapshot": len(unknown_terms),
        },
        "portuguese_coverage_of_annotated_phenotypes": {
            "phenotypic_terms_used": len(used_p),
            "with_official_pt_label": len(translated),
            "without_pt_label": len(used_p) - len(translated),
            "percent_with_pt_label": round(100 * len(translated) / len(used_p), 2),
            "note": (
                "Cobertura medida sobre os termos que de fato aparecem em "
                "anotações de doença, não sobre a ontologia inteira."
            ),
        },
        "outputs": {
            "csv": output_csv_label or Path(output_csv).name,
            "csv_sha256": content_sha256(csv_path),
        },
        "invented_translation": False,
    }
    Path(output_metadata).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def load_snapshot(csv_path: str | Path, metadata_path: str | Path) -> HpoaIndex:
    manifest = json.loads(Path(metadata_path).read_text(encoding="utf-8"))
    with Path(csv_path).open(encoding="utf-8", newline="") as handle:
        annotations = tuple(
            HpoaAnnotation(
                database_id=row["database_id"],
                disease_name=row["disease_name"],
                hpo_id=row["hpo_id"],
                aspect=row["aspect"],
                excluded=row["excluded"] == "true",
                frequency=row["frequency"],
                onset=row["onset"],
                sex=row["sex"],
                modifier=row["modifier"],
                evidence=row["evidence"],
                reference=row["reference"],
                biocuration=row["biocuration"],
            )
            for row in csv.DictReader(handle)
        )
    if not annotations:
        raise ValueError(f"Snapshot HPOA vazio: {csv_path}")
    return HpoaIndex(
        hpo_release=str(manifest["terminology_snapshot"]["hpo_release"]),
        hpoa_version=str(manifest["source"]["hpoa_version"]),
        annotations=annotations,
    )


def _describe_hpo_coded_field(value: str, ontology: OntologyIndex) -> str:
    """Frequência e início podem vir como código HPO, fração ou percentual."""
    if _HPO_ID.match(value):
        concept = ontology.get(value)
        if concept is not None:
            return concept.label_pt or concept.label_en or value
    return value


def disease_profile(
    index: HpoaIndex,
    ontology: OntologyIndex,
    database_id: str,
    *,
    aspects: tuple[str, ...] = ("P",),
) -> dict[str, object]:
    """Perfil fenotípico de uma doença, com proveniência por linha.

    Levanta ValueError para doença inexistente: lista vazia silenciosa
    esconderia um erro de digitação do usuário.
    """
    wanted = database_id.strip().upper()
    rows = [a for a in index.annotations if a.database_id.upper() == wanted]
    if not rows:
        raise ValueError(
            f"Doença ausente no snapshot HPOA: {database_id}. "
            "Use a busca por nome para localizar o identificador correto."
        )

    selected = [a for a in rows if a.aspect in aspects]
    selected.sort(key=lambda a: (ASPECT_ORDER.get(a.aspect, 9), a.hpo_id))

    entries = []
    for annotation in selected:
        concept = ontology.require(annotation.hpo_id)
        entries.append(
            {
                "hpo_id": annotation.hpo_id,
                "label_pt": concept.label_pt,
                "label_en": concept.label_en,
                "label_pt_status": "official" if concept.label_pt else "unavailable",
                "in_phenotypic_tree": ontology.is_phenotypic_abnormality(
                    annotation.hpo_id
                ),
                "aspect": annotation.aspect,
                "aspect_label": ASPECT_LABELS.get(annotation.aspect, annotation.aspect),
                "excluded": annotation.excluded,
                "frequency": annotation.frequency,
                "frequency_label": _describe_hpo_coded_field(
                    annotation.frequency, ontology
                ),
                "onset": annotation.onset,
                "onset_label": _describe_hpo_coded_field(annotation.onset, ontology),
                "sex": annotation.sex,
                "modifier": annotation.modifier,
                "evidence": annotation.evidence,
                "evidence_label": EVIDENCE_LABELS.get(
                    annotation.evidence, annotation.evidence
                ),
                "reference": annotation.reference,
                "biocuration": annotation.biocuration,
                "term_source": "HPO phenotype.hpoa",
            }
        )

    return {
        "schema_version": "hpo-ptbr-disease-profile-v1",
        "database_id": rows[0].database_id,
        "disease_name": rows[0].disease_name,
        "aspects_requested": list(aspects),
        "provenance": {
            "hpo_release": index.hpo_release,
            "hpoa_version": index.hpoa_version,
            "terminology_data_version": ontology.data_version,
        },
        "summary": {
            "annotations": len(entries),
            "present": sum(1 for e in entries if not e["excluded"]),
            "excluded": sum(1 for e in entries if e["excluded"]),
            "with_official_pt_label": sum(
                1 for e in entries if e["label_pt_status"] == "official"
            ),
            "without_pt_label": sum(
                1 for e in entries if e["label_pt_status"] == "unavailable"
            ),
            "with_frequency": sum(1 for e in entries if e["frequency"]),
            "with_onset": sum(1 for e in entries if e["onset"]),
        },
        "annotations": entries,
        "limitations": [
            "Perfil terminológico versionado; não constitui diagnóstico.",
            "Frequência e início refletem a curadoria da HPO, não uma coorte própria.",
            "Rótulo ausente em português é marcado como indisponível, nunca traduzido automaticamente.",
        ],
    }
