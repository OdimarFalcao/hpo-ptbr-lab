"""Ferramentas do protótipo HPO-PTBR.

As importações são preguiçosas (PEP 562) por um motivo concreto: a bancada
de ranqueamento depende de `rapidfuzz`, `rank_bm25` e dos modelos
semânticos, enquanto o painel de alvos fenotípicos depende apenas da
biblioteca padrão. Importar tudo aqui fazia com que `hpo_panel_cli.py`
falhasse com `ModuleNotFoundError: rapidfuzz` sem nunca ter precisado de
correspondência aproximada.

Cada nome continua acessível como antes (`from hpo_ptbr import FuzzyMapper`);
o módulo correspondente só é carregado no primeiro acesso.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS = {
    "HpoRecord": "data",
    "load_metadata": "data",
    "load_snapshot": "data",
    "EvidenceExtractor": "evidence",
    "EvidenceSpan": "evidence",
    "TextMappingResult": "evidence",
    "SemanticEvidenceExtractor": "semantic_evidence",
    "evaluate_cases": "evaluation",
    "HybridMapper": "hybrid",
    "HybridEvidenceExtractor": "hybrid_evidence",
    "Bm25Mapper": "rankers",
    "ExactMapper": "rankers",
    "FuzzyMapper": "rankers",
    "BilingualSemanticMapper": "semantic",
    "SemanticMapper": "semantic",
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    modulo = _EXPORTS.get(name)
    if modulo is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(import_module(f".{modulo}", __name__), name)


def __dir__() -> list[str]:
    return sorted({*globals(), *_EXPORTS})
