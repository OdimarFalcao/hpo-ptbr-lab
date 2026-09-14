"""Hashes de conteúdo independentes de plataforma.

Motivo: até 2026-09-14 os hashes de congelamento eram calculados sobre os
bytes crus do arquivo. Artefatos gerados em Windows nascem com quebra de
linha CRLF (`csv.DictWriter` usa `\\r\\n` por padrão e `Path.write_text`
traduz `\\n` para `os.linesep`), enquanto o git os armazena e devolve com
LF. O mesmo conteúdo produzia digests diferentes conforme a máquina, e a
verificação de congelamento só passava no computador que gerou os arquivos.

Distinção deliberada entre as duas funções:

- `content_sha256` atesta o CONTEÚDO de um artefato do próprio repositório.
  Quebras de linha são normalizadas para LF antes do hash, porque CRLF e LF
  representam o mesmo conteúdo. É o que deve ser usado em congelamentos,
  protocolos e manifestos internos.

- `raw_sha256` atesta os BYTES de um arquivo baixado de uma fonte externa
  (hp.json, hp-pt.babelon.tsv, pesos de modelo). Aqui a normalização seria
  errada: o hash precisa bater com o artefato publicado upstream, byte a
  byte.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

# Sufixos tratados como binários: normalizar quebras de linha corromperia
# o conteúdo.
BINARY_SUFFIXES = frozenset(
    {
        ".gz",
        ".zip",
        ".bz2",
        ".xz",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".pdf",
        ".docx",
        ".xlsx",
        ".pptx",
        ".ab1",
        ".bin",
        ".safetensors",
        ".pt",
        ".onnx",
        ".npy",
        ".npz",
        ".parquet",
        ".ipynb_checkpoints",
    }
)


def is_binary_path(path: str | Path) -> bool:
    return Path(path).suffix.lower() in BINARY_SUFFIXES


def normalize_newlines(data: bytes) -> bytes:
    """Converte CRLF e CR isolado para LF, sem alterar o restante."""
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def content_sha256(path: str | Path) -> str:
    """sha256 do conteúdo de um artefato do repositório.

    Arquivos de texto têm as quebras de linha normalizadas para LF antes do
    hash, de modo que Windows e Linux produzam o mesmo digest para o mesmo
    conteúdo. Arquivos binários são hasheados byte a byte.
    """
    target = Path(path)
    data = target.read_bytes()
    if not is_binary_path(target):
        data = normalize_newlines(data)
    return hashlib.sha256(data).hexdigest()


def raw_sha256(path: str | Path) -> str:
    """sha256 dos bytes crus, para atestar artefatos de fonte externa."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
