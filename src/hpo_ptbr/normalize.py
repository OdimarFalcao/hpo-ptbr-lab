from __future__ import annotations

import re
import unicodedata

_NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]+")
_WHITESPACE = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    """Normaliza caixa, acentos, pontuação e espaços sem traduzir o conteúdo."""
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    without_punctuation = _NON_ALPHANUMERIC.sub(" ", without_accents)
    return _WHITESPACE.sub(" ", without_punctuation).strip()


def tokenize(value: str) -> list[str]:
    normalized = normalize_text(value)
    return normalized.split() if normalized else []
