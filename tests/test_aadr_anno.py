"""Contratos da descrição do arquivo de metadados AADR ``.anno``."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from hpo_ptbr.aadr_anno import EXPECTED_COLUMNS, describe_anno, write_manifest
from hpo_ptbr.cli._comum import AADR_ANNO_URL


def _write_anno(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(EXPECTED_COLUMNS)
        writer.writerows(rows)


def _row(**values: str) -> list[str]:
    row = [""] * len(EXPECTED_COLUMNS)
    for column, value in values.items():
        row[EXPECTED_COLUMNS.index(column)] = value
    return row


def _distribution(description: dict[str, object], column: str) -> dict[str, object]:
    return next(
        item for item in description["described_columns"] if item["column"] == column
    )


def test_descreve_arquivo_sintetico_sem_filtrar_vazios_ou_ambiguos(
    tmp_path: Path,
) -> None:
    path = tmp_path / "pequeno.anno"
    _write_anno(
        path,
        [
            _row(
                Locality="Sítio A",
                **{
                    "Individual ID": "I1",
                    "Political Entity": "Brasil",
                    "Data type": "Shotgun",
                    "Mean coverage on 1.15M autosomal targets for full bam (if no off-target entry not up-to-date)": "1.5",
                    "Date mean in BP in years before 1950 CE [OxCal mu for a direct radiocarbon date, and average of range for a contextual date]": "0",
                    "Full Date One of two formats. (Format 1) 95.4% CI calibrated radiocarbon age (Conventional Radiocarbon Age BP, Lab number) e.g. 2624-2350 calBCE (3990+-40 BP, Ua-35016). (Format 2) Archaeological context range, e.g. 2500-1700 BCE": "present",
                },
            ),
            _row(
                Locality="",
                **{
                    "Individual ID": "I1",
                    "Political Entity": "..",
                    "Data type": "n/a",
                    "Mean coverage on 1.15M autosomal targets for full bam (if no off-target entry not up-to-date)": "..",
                    "Date mean in BP in years before 1950 CE [OxCal mu for a direct radiocarbon date, and average of range for a contextual date]": "0",
                    "Full Date One of two formats. (Format 1) 95.4% CI calibrated radiocarbon age (Conventional Radiocarbon Age BP, Lab number) e.g. 2624-2350 calBCE (3990+-40 BP, Ua-35016). (Format 2) Archaeological context range, e.g. 2500-1700 BCE": "present",
                },
            ),
            _row(
                Locality="Sítio A",
                **{
                    "Individual ID": "I2",
                    "Political Entity": "n/a (unknown)",
                    "Data type": "Capture",
                    "Mean coverage on 1.15M autosomal targets for full bam (if no off-target entry not up-to-date)": "",
                },
            ),
        ],
    )

    description = describe_anno(path)

    assert description["individuals"] == 3
    assert description["column_count"] == 49
    assert description["columns"] == list(EXPECTED_COLUMNS)
    assert description["parsing"]["rows_excluded"] == 0

    locality = _distribution(description, "Locality")
    assert locality["empty_values"] == 1
    assert locality["ambiguous_values"] == 0
    assert locality["value_counts"][:2] == [
        {"value": "Sítio A", "count": 2},
        {"value": "", "count": 1},
    ]

    political_entity = _distribution(description, "Political Entity")
    assert political_entity["empty_values"] == 0
    assert political_entity["ambiguous_values"] == 2

    data_type = _distribution(description, "Data type")
    assert data_type["ambiguous_values"] == 1

    coverage = _distribution(
        description,
        "Mean coverage on 1.15M autosomal targets for full bam (if no off-target entry not up-to-date)",
    )
    assert coverage["empty_values"] == 1
    assert coverage["ambiguous_values"] == 1

    assert description["individual_counts"] == {
        "rows": 3,
        "distinct_nonempty_individual_ids": 2,
        "individual_ids_in_multiple_rows": 1,
        "rows_with_empty_individual_id": 0,
    }
    assert description["current_records"] == {
        "date_mean_bp_equals_0": 2,
        "full_date_equals_present": 2,
        "both_fields": 2,
        "rows_excluded": 0,
        "note": (
            "Contagens descritivas de indivíduos atuais; estes registros "
            "permanecem no arquivo e em todas as demais contagens."
        ),
    }


def test_manifesto_registra_sha256_e_contagens(tmp_path: Path) -> None:
    source = tmp_path / "pequeno.anno"
    output = tmp_path / "manifesto.json"
    _write_anno(source, [_row(Locality="A")])

    description = describe_anno(source)
    write_manifest(description, output)
    saved = json.loads(output.read_text(encoding="utf-8"))

    assert saved["source"]["file"] == "pequeno.anno"
    assert saved["source"]["url"] == ""
    assert len(saved["source"]["sha256"]) == 64
    assert saved["individuals"] == 1
    assert saved["source"]["version_declared_in_file"] is None
    assert saved["source"]["related_snp_file"] == "v66.p1_1240K.aadr.patch.PUB.snp"
    assert saved["source"]["related_snp_correspondence_confirmed"] is False


def test_url_nao_verificada_nao_e_assumida() -> None:
    assert AADR_ANNO_URL == ""


def test_colunas_com_nome_duplicado_sao_preservadas(tmp_path: Path) -> None:
    source = tmp_path / "duplicadas.anno"
    _write_anno(source, [_row(**{"Individual ID": "I1"})])

    description = describe_anno(source)

    duplicate = "Sum total of ROH segments >20cM"
    assert description["columns"].count(duplicate) == 2
    assert description["columns"][32:34] == [duplicate, duplicate]


def test_distribuicao_e_completa_com_ate_200_valores_distintos(tmp_path: Path) -> None:
    source = tmp_path / "quarenta_paises.anno"
    rows = [
        _row(**{"Individual ID": f"I{index}", "Political Entity": f"País {index:02}"})
        for index in range(40)
    ]
    _write_anno(source, rows)

    description = describe_anno(source)
    political_entity = _distribution(description, "Political Entity")

    assert political_entity["distinct_values"] == 40
    assert political_entity["distribution_complete"] is True
    assert political_entity["values_shown"] == 40
    assert len(political_entity["value_counts"]) == 40


def test_cabecalho_inesperado_falha_nomeando_o_encontrado(tmp_path: Path) -> None:
    path = tmp_path / "errado.anno"
    path.write_text("Coluna inesperada\tOutra coluna\nA\tB\n", encoding="utf-8")

    with pytest.raises(ValueError) as captured:
        describe_anno(path)

    message = str(captured.value)
    assert "Cabeçalho inesperado" in message
    assert "Cabeçalho encontrado (2 colunas)" in message
    assert "Coluna inesperada | Outra coluna" in message


def test_linha_com_largura_errada_falha_sem_descartar(tmp_path: Path) -> None:
    path = tmp_path / "truncado.anno"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(EXPECTED_COLUMNS)
        writer.writerow(["curta"])

    with pytest.raises(ValueError, match="Nenhuma linha foi descartada"):
        describe_anno(path)
