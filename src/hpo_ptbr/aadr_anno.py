"""Descrição estrutural do arquivo de metadados ``.anno`` do AADR.

Este módulo não classifica indivíduos nem aplica filtros. Ele preserva os
nomes de coluna e os valores como publicados, conta ausências e ambiguidades
e produz uma descrição auditável da fonte.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from .hashing import raw_sha256


EXPECTED_COLUMNS = (
    'Genetic ID (suffices: ".DG" is a high coverage shotgun genome with diploid genotype calls; ".SG" is a high coverage shotgun genome with diploid genotype calls; ".AG,  .TW, .BY, .AA, .EC, .WGC"  are Agilent 1240K or Twist Ancient DNA or "Big Yoruba" or "Archaic Admixture" or "Exome" or "Whole-Genome Capture" data respectively; each analyzed position is represented by a randomly chosen sequence allowing for combinations when merged (separable by readgroups if possible).  ".HO" is Affymetrix Human Origins genotype data and "REF" is reference haploid data.',
    "Persistent Genetic ID",
    "Individual ID",
    "Skeletal code",
    "Skeletal element",
    "First publication: Abbreviation for earliest paper that reported data from this individual (this is not always the same as the data being analyzed, which may be from a different or improved dataset)",
    "Publication abbreviation",
    "doi for publication of this representation of the data",
    "Link to the most permanent repository hosting these data",
    "Method for Determining Date; unless otherwise specified, calibrations use 95.4% intervals from OxCal v4.4.2 Bronk Ramsey (2009); r5; Atmospheric data from Reimer et al (2020)",
    "Date mean in BP in years before 1950 CE [OxCal mu for a direct radiocarbon date, and average of range for a contextual date]",
    "Date standard deviation in BP [OxCal sigma for a direct radiocarbon date, and standard deviation of the uniform distribution between the two bounds for a contextual date]",
    "Full Date One of two formats. (Format 1) 95.4% CI calibrated radiocarbon age (Conventional Radiocarbon Age BP, Lab number) e.g. 2624-2350 calBCE (3990+-40 BP, Ua-35016). (Format 2) Archaeological context range, e.g. 2500-1700 BCE",
    "Age at death, Morphological sex from physical anthropology",
    "Group ID",
    "Locality",
    "Political Entity",
    "Latitude",
    "Longitude",
    "Pulldown Strategy",
    "Suffices (indicating data types used for sources which can be a subset of that in bam)",
    "Data type",
    "No. Libraries",
    'Mean coverage on 1.15M autosomal targets for full bam (if no off-target entry not up-to-date)',
    'Mean coverage on non-targeted autosomal SNPs for full bam - not yet computed if "".."" and bam restricted to on-target SNPs if ""0""',
    "SNPs hit on autosomal targets (Computed using easystats on enhance 2M capture subset)\N{NO-BREAK SPACE}",
    "SNPs hit on autosomal targets (Computed using easystats on 1240k snpset)",
    "SNPs hit on autosomal targets (Computed using easystats on HO snpset)",
    "SNPs hit on autosomal targets (Computed using easystats on Compatibility snpset)",
    "SNPs hit on autosomal targets (Computed using easystats on Compatibility_HO snpset)",
    "Molecular Sex",
    "Family relations",
    "Sum total of ROH segments >20cM",
    "Sum total of ROH segments >20cM",
    "Y haplogroup in terminal mutation notation automatically called based on Y-full 12.03 with the software described in Lazaridis et al. Science 2022",
    "Y haplogroup  in ISOGG notation automatically called based on Yfull 12.03 with the software described in Lazaridis et al. Science 2022",
    "Y haplogroup manually called if different from automatic",
    "mtDNA coverage (merged data)",
    "mtDNA haplogroup if >2x or published",
    "mtDNA match to consensus if >10x (merged data) [estimates are typically off by (uncorrected + power(10,-0.271*LOG(mt-coverage)-1.120)]",
    "Damage rate in first nucleotide on sequences overlapping 1240k targets (merged data)",
    "Sex ratio [Y/(Y+X) counts] (merged data)",
    "ANGSD MOM 95% CI truncated at 0 (only if male and >=200 SNPs) [estimates are typically 0.005 too high]",
    "hapConX 95% CI truncated at 0 (only if male and >=2000 SNPs covered on X chromosome) [estimates are typically 0.005 too high]",
    "Library type (minus=no.damage.correction, half=damage.retained.at.last.position, plus=damage.fully.corrected, ds=double.stranded.library.preparation, ss=single.stranded.library.preparation)",
    "Libraries",
    "endogenous by library (computed on shotgun data)",
    "ASSESSMENT",
    'ASSESSMENT WARNINGS: X contamination interval is listed if lower bound is >=0.005 for either ANGSD or hapConX, "QUESTIONABLE" if lower bound is 0.015-0.035 for hapConX (or ANGSD if no hapConX computation), "CRITICAL" or "FAIL" if lower bound is >0.03  for hapConX (or ANGSD if no hapConX computation) |mtcontam confidence interval is listed if coverage >10 and upper bound is <0.98, "QUESTIONABLE" if upper bound is 0.9-0.95; "CRITICAL" if upper bound is <0.9, QUESTIONABLE status gets overriden by ANGSD or hapConX if upper bound of contamination estimate is <0.01 | damage for ds.half is "CRITICAL/FAIL" if <0.01, and recorded but passed if 0.01-0.03; libraries with untreated last base are "CRITICAL" or "FAIL" if <0.01, "QUESTIONABLE" if 0.01-0.03, and recorded but passed if 0.03-0.1 | sex.ratio is QUESTIONABLE if [0.03,0.1) or (0.30,0.32]; CRITICAL/FAIL if [0.1,0.3] | f4(All,Damage;CEU,CHB) for non-damage-restricted samples is "CRITICAL/FAIL" if |Z|>=3.5, QUESTIONABLE if 3.5>Z>=3.0, listed if Z>=2.0',
)

# Índices, não nomes: a fonte contém dois cabeçalhos idênticos (colunas 33 e
# 34), e a descrição precisa preservar ambos sem colisão.
DESCRIBED_COLUMNS = {
    "local": (15, 16, 17, 18),
    "tipo_de_dado": (19, 20, 21, 44),
    # Além das três colunas chamadas explicitamente de coverage, os cinco
    # campos "SNPs hit" medem a cobertura observada em conjuntos de alvos.
    "cobertura": (23, 24, 25, 26, 27, 28, 29, 37),
    "data": (9, 10, 11, 12),
}

INDIVIDUAL_ID_INDEX = 2
DATE_MEAN_BP_INDEX = 10
FULL_DATE_INDEX = 12
FULL_DISTRIBUTION_MAX_DISTINCT = 200
RELATED_SNP_FILE = "v66.p1_1240K.aadr.patch.PUB.snp"

AMBIGUOUS_EXACT = frozenset(
    {"..", ".", "...", "n/a", "na", "n.a.", "?", "unknown", "undetermined", "not available"}
)
AMBIGUOUS_PREFIXES = ("n/a ", "n/a(", "unknown ", "unknown(", "not available ")


def _is_ambiguous(value: str) -> bool:
    normalized = value.strip().casefold()
    return normalized in AMBIGUOUS_EXACT or normalized.startswith(AMBIGUOUS_PREFIXES)


def _header_error(found: list[str]) -> ValueError:
    first_difference = next(
        (
            index
            for index, (expected, actual) in enumerate(
                zip(EXPECTED_COLUMNS, found, strict=False), start=1
            )
            if expected != actual
        ),
        min(len(EXPECTED_COLUMNS), len(found)) + 1,
    )
    rendered = " | ".join(found) if found else "<arquivo vazio>"
    return ValueError(
        "Cabeçalho inesperado no arquivo AADR .anno. "
        f"Primeira diferença na coluna {first_difference}. "
        f"Cabeçalho encontrado ({len(found)} colunas): {rendered}"
    )


def describe_anno(
    anno_path: str | Path,
    *,
    source_url: str = "",
    top_n: int = 30,
) -> dict[str, object]:
    """Lê um ``.anno`` AADR e devolve uma descrição sem filtrar linhas."""
    if top_n < 1:
        raise ValueError("top_n precisa ser pelo menos 1")

    path = Path(anno_path)
    selected = {index for indices in DESCRIBED_COLUMNS.values() for index in indices}
    counters = {index: Counter() for index in selected}
    individual_id_counts: Counter[str] = Counter()
    individuals = 0
    date_mean_zero = 0
    full_date_present = 0
    current_by_both_fields = 0

    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        try:
            header = next(reader)
        except StopIteration:
            raise _header_error([]) from None
        if tuple(header) != EXPECTED_COLUMNS:
            raise _header_error(header)

        for line_number, row in enumerate(reader, start=2):
            if len(row) != len(header):
                raise ValueError(
                    f"Linha {line_number} tem {len(row)} campos; o cabeçalho tem "
                    f"{len(header)}. Nenhuma linha foi descartada."
                )
            individuals += 1
            individual_id_counts[row[INDIVIDUAL_ID_INDEX]] += 1
            has_zero_date_mean = row[DATE_MEAN_BP_INDEX] == "0"
            has_present_full_date = row[FULL_DATE_INDEX] == "present"
            date_mean_zero += has_zero_date_mean
            full_date_present += has_present_full_date
            current_by_both_fields += has_zero_date_mean and has_present_full_date
            for index in selected:
                counters[index][row[index]] += 1

    distributions = []
    for category, indices in DESCRIBED_COLUMNS.items():
        for index in indices:
            counts = counters[index]
            ordered_values = sorted(
                counts.items(), key=lambda item: (-item[1], item[0].casefold(), item[0])
            )
            complete = len(counts) <= FULL_DISTRIBUTION_MAX_DISTINCT
            displayed_values = ordered_values if complete else ordered_values[:top_n]
            distributions.append(
                {
                    "category": category,
                    "column_number": index + 1,
                    "column": header[index],
                    "distinct_values": len(counts),
                    "empty_values": counts.get("", 0),
                    "ambiguous_values": sum(
                        count for value, count in counts.items() if value and _is_ambiguous(value)
                    ),
                    "distribution_complete": complete,
                    "values_shown": len(displayed_values),
                    "display_rule": (
                        f"distribuição completa (até {FULL_DISTRIBUTION_MAX_DISTINCT} valores distintos)"
                        if complete
                        else f"{top_n} valores mais frequentes"
                    ),
                    "value_counts": [
                        {"value": value, "count": count} for value, count in displayed_values
                    ],
                }
            )

    nonempty_ids = {value: count for value, count in individual_id_counts.items() if value}

    return {
        "schema_version": "aadr-anno-description-v1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source": {
            "url": source_url,
            "file": path.name,
            "sha256": raw_sha256(path),
            "format": "AADR .anno (TSV com campos entre aspas)",
            "version_declared_in_file": None,
            "version_note": (
                "O conteúdo do arquivo não declara versão; a identificação v66.p1 "
                "vem do nome publicado e a proveniência é fixada pelo sha256."
            ),
            "related_snp_file": RELATED_SNP_FILE,
            "related_snp_correspondence_confirmed": False,
            "related_snp_note": (
                "Este é o arquivo .snp usado pelos outros comandos para o painel "
                "de genotipagem 1240K; a correspondência entre ele e este .anno "
                "ainda não foi confirmada."
            ),
        },
        "individuals": individuals,
        "individual_counts": {
            "rows": individuals,
            "distinct_nonempty_individual_ids": len(nonempty_ids),
            "individual_ids_in_multiple_rows": sum(
                count > 1 for count in nonempty_ids.values()
            ),
            "rows_with_empty_individual_id": individual_id_counts.get("", 0),
        },
        "current_records": {
            "date_mean_bp_equals_0": date_mean_zero,
            "full_date_equals_present": full_date_present,
            "both_fields": current_by_both_fields,
            "rows_excluded": 0,
            "note": (
                "Contagens descritivas de indivíduos atuais; estes registros "
                "permanecem no arquivo e em todas as demais contagens."
            ),
        },
        "column_count": len(header),
        "columns": list(header),
        "described_columns": distributions,
        "parsing": {
            "data_rows_read": individuals,
            "rows_excluded": 0,
            "malformed_rows": 0,
            "filters_applied": [],
            "empty_definition": "Campo de comprimento zero entre separadores TSV.",
            "ambiguous_exact_values_case_insensitive": sorted(AMBIGUOUS_EXACT),
            "ambiguous_prefixes_case_insensitive": list(AMBIGUOUS_PREFIXES),
            "note": (
                "Valores vazios e ambíguos são preservados na distribuição e "
                "também contados separadamente; nenhum indivíduo é classificado."
            ),
        },
    }


def write_manifest(description: dict[str, object], output_path: str | Path) -> None:
    """Grava a descrição com bytes determinísticos, exceto pelo timestamp."""
    Path(output_path).write_text(
        json.dumps(description, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
