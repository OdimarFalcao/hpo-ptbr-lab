"""Regressão: o congelamento não pode depender do sistema operacional.

Até 2026-09-14 os hashes eram calculados sobre os bytes crus. Artefatos
gerados em Windows nascem com CRLF e o git os devolve com LF, então a
verificação de congelamento só passava na máquina que gerou os arquivos.
A emenda que regravou os hashes da época está preservada na etiqueta
`frente-a-final`, em `data/protocol/hash_normalization_amendment.json`.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from hpo_ptbr.hashing import content_sha256, normalize_newlines, raw_sha256

ROOT = Path(__file__).resolve().parents[1]


def _write(path: Path, text: str, newline: str) -> Path:
    path.write_bytes(text.replace("\n", newline).encode("utf-8"))
    return path


def test_content_hash_ignores_line_ending_convention(tmp_path: Path) -> None:
    conteudo = "hpo_id,label_pt\nHP:0000118,Anomalia fenotípica\nHP:0000508,Ptose\n"
    lf = _write(tmp_path / "lf.csv", conteudo, "\n")
    crlf = _write(tmp_path / "crlf.csv", conteudo, "\r\n")

    assert lf.read_bytes() != crlf.read_bytes()
    assert content_sha256(lf) == content_sha256(crlf)


def test_content_hash_still_detects_real_content_change(tmp_path: Path) -> None:
    original = _write(tmp_path / "a.json", '{"data_version": "x"}\n', "\n")
    alterado = _write(tmp_path / "b.json", '{"data_version": "y"}\n', "\n")

    assert content_sha256(original) != content_sha256(alterado)


def test_raw_hash_preserves_bytes_for_external_sources(tmp_path: Path) -> None:
    """Fonte externa é atestada byte a byte: normalizar quebraria o match upstream."""
    conteudo = "col\nvalor\n"
    lf = _write(tmp_path / "fonte_lf.tsv", conteudo, "\n")
    crlf = _write(tmp_path / "fonte_crlf.tsv", conteudo, "\r\n")

    assert raw_sha256(lf) != raw_sha256(crlf)
    assert raw_sha256(lf) == hashlib.sha256(lf.read_bytes()).hexdigest()


def test_binary_files_are_not_normalized(tmp_path: Path) -> None:
    """Um .gz com a sequência 0d0a não pode ser alterado antes do hash."""
    binario = tmp_path / "dados.gz"
    binario.write_bytes(b"\x1f\x8b\x08\x00\r\n\x00\x03payload")

    assert content_sha256(binario) == hashlib.sha256(binario.read_bytes()).hexdigest()
    assert content_sha256(binario) != hashlib.sha256(
        normalize_newlines(binario.read_bytes())
    ).hexdigest()


@pytest.mark.parametrize(
    "relative_path",
    [
        "data/processed/hpo_ptbr.csv",
        "data/processed/metadata.json",
        "data/processed/gene_disease.csv",
        "data/processed/target_coverage.csv",
    ],
)
def test_repository_artifacts_hash_identically_in_both_conventions(
    relative_path: str, tmp_path: Path
) -> None:
    origem = ROOT / relative_path
    base = origem.read_bytes().replace(b"\r\n", b"\n")
    lf = tmp_path / ("lf" + origem.suffix)
    crlf = tmp_path / ("crlf" + origem.suffix)
    lf.write_bytes(base)
    crlf.write_bytes(base.replace(b"\n", b"\r\n"))

    assert content_sha256(lf) == content_sha256(crlf) == content_sha256(origem)
