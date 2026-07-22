"""Ferramentas do protótipo HPO-PTBR."""

from .data import HpoRecord, load_metadata, load_snapshot
from .evidence import EvidenceExtractor, EvidenceSpan, TextMappingResult
from .semantic_evidence import SemanticEvidenceExtractor
from .evaluation import evaluate_cases
from .hybrid import HybridMapper
from .hybrid_evidence import HybridEvidenceExtractor
from .rankers import Bm25Mapper, ExactMapper, FuzzyMapper
from .semantic import SemanticMapper

__all__ = [
    "Bm25Mapper",
    "ExactMapper",
    "EvidenceExtractor",
    "EvidenceSpan",
    "SemanticEvidenceExtractor",
    "FuzzyMapper",
    "HpoRecord",
    "HybridMapper",
    "HybridEvidenceExtractor",
    "SemanticMapper",
    "TextMappingResult",
    "evaluate_cases",
    "load_metadata",
    "load_snapshot",
]
