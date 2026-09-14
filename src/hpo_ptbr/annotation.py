from __future__ import annotations

import re
from datetime import UTC, datetime

from rapidfuzz import fuzz

from .assertion import PortugueseContextCueClassifier
from .normalize import normalize_text
from .ontology import OntologyIndex
from .rankers import BaseMapper, FuzzyMapper

ASSERTION_LABELS = {
    "present": "Presente",
    "absent": "Ausente",
    "uncertain": "Incerto",
    "family_history": "Histórico familiar",
}
RETRIEVAL_REASONS = {
    "exact": "correspondência exata normalizada",
    "fuzzy": "proximidade lexical",
    "bm25": "sobreposição de termos BM25",
    "semantic": "similaridade semântica experimental",
    "manual_search": "busca manual por rótulo",
    "hpo_id_lookup": "consulta direta por HPO ID",
    "ontology_term_search": "rótulo ou sinônimo oficial da HPO",
}

CHARACTERIZATION_FIELDS = (
    ("onset_age", "idade ou início"),
    ("severity", "gravidade"),
    ("evolution", "evolução"),
    ("frequency", "frequência"),
    ("laterality", "lateralidade, quando aplicável"),
    ("family_history", "histórico familiar"),
)


def find_occurrences(text: str, phrase: str) -> list[tuple[int, int]]:
    cleaned_phrase = phrase.strip()
    if not cleaned_phrase:
        return []
    return [
        (match.start(), match.end())
        for match in re.finditer(re.escape(cleaned_phrase), text, flags=re.IGNORECASE)
    ]


def occurrence_label(text: str, start: int, end: int, context_chars: int = 30) -> str:
    left = max(0, start - context_chars)
    right = min(len(text), end + context_chars)
    prefix = "…" if left else ""
    suffix = "…" if right < len(text) else ""
    return f"{start}–{end}: {prefix}{text[left:start]}[{text[start:end]}]{text[end:right]}{suffix}"


def rank_candidates(
    text: str,
    mappers: dict[str, BaseMapper],
    *,
    top_k: int = 5,
) -> dict[str, list[dict[str, object]]]:
    rankings = {}
    for method_name, mapper in mappers.items():
        result = mapper.map(text, top_k=top_k)
        rankings[method_name] = [
            candidate.to_dict()
            | {
                "method": result.method,
                "reason": RETRIEVAL_REASONS[result.method],
                "matched_term": candidate.label_pt,
                "matched_language": "pt",
                "term_source": "HPO Portuguese translation snapshot",
                "label_pt_status": "official",
            }
            for candidate in result.candidates
        ]
    return rankings


def candidate_union(
    rankings: dict[str, list[dict[str, object]]],
) -> list[dict[str, object]]:
    candidates = {}
    for method_name in rankings:
        for candidate in rankings[method_name]:
            candidates.setdefault(str(candidate["hpo_id"]), candidate)
    return list(candidates.values())


def search_candidates(
    query: str,
    mapper: FuzzyMapper,
    ontology: OntologyIndex,
    *,
    top_k: int = 5,
) -> list[dict[str, object]]:
    cleaned_query = query.strip()
    if not cleaned_query:
        return []
    direct_id = cleaned_query.upper()
    if re.fullmatch(r"HP:\d{7}", direct_id):
        concept = ontology.get(direct_id)
        if concept is None:
            return []
        return [
            {
                "hpo_id": concept.hpo_id,
                "label_pt": concept.label_pt,
                "label_en": concept.label_en,
                "score": None,
                "rank": 1,
                "method": "hpo_id_lookup",
                "reason": RETRIEVAL_REASONS["hpo_id_lookup"],
                "matched_term": concept.label_pt or concept.label_en,
                "matched_language": "pt" if concept.label_pt else "en",
                "term_source": (
                    "HPO Portuguese translation snapshot"
                    if concept.label_pt
                    else "HPO ontology snapshot"
                ),
                "label_pt_status": "official" if concept.label_pt else "unavailable",
            }
        ]
    result = mapper.map(cleaned_query, top_k=top_k)
    translated = [
        candidate.to_dict()
        | {
            "method": "manual_search",
            "reason": RETRIEVAL_REASONS["manual_search"],
            "matched_term": candidate.label_pt,
            "matched_language": "pt",
            "term_source": "HPO Portuguese translation snapshot",
            "label_pt_status": "official",
        }
        for candidate in result.candidates
    ]
    translated_ids = {str(candidate["hpo_id"]) for candidate in translated}
    normalized_query = normalize_text(cleaned_query)
    official_terms: list[tuple[float, str, str, str, str]] = []
    for concept in ontology.concepts.values():
        terms = [(concept.label_en, "label_en", "clinical")]
        terms.extend(
            (synonym.text, "synonym_en", synonym.audience)
            for synonym in concept.synonyms
        )
        best: tuple[float, str, str, str] | None = None
        for term, field, audience in terms:
            score = fuzz.WRatio(normalized_query, normalize_text(term)) / 100.0
            candidate = (score, term, field, audience)
            if best is None or (-score, term.casefold(), field) < (
                -best[0], best[1].casefold(), best[2]
            ):
                best = candidate
        if best is not None and concept.hpo_id not in translated_ids:
            official_terms.append((*best, concept.hpo_id))
    official_terms.sort(key=lambda item: (-item[0], item[4], item[1].casefold()))
    supplemental = []
    for rank, (score, term, field, audience, hpo_id) in enumerate(
        official_terms[:top_k], start=1
    ):
        concept = ontology.require(hpo_id)
        supplemental.append(
            {
                "hpo_id": hpo_id,
                "label_pt": concept.label_pt,
                "label_en": concept.label_en,
                "score": round(score, 6),
                "rank": rank,
                "method": "ontology_term_search",
                "reason": RETRIEVAL_REASONS["ontology_term_search"],
                "matched_term": term,
                "matched_language": "en",
                "matched_field": field,
                "matched_audience": audience,
                "term_source": "HPO ontology snapshot",
                "label_pt_status": "official" if concept.label_pt else "unavailable",
            }
        )
    return translated + supplemental


def build_annotation_span(
    text: str,
    start: int,
    end: int,
    *,
    source: str,
    mappers: dict[str, BaseMapper],
    classifier: PortugueseContextCueClassifier,
    detector_score: float | None = None,
    top_k: int = 5,
) -> dict[str, object]:
    if start < 0 or end <= start or end > len(text):
        raise ValueError("Offsets inválidos para anotação.")
    if source not in {"lexical", "manual"}:
        raise ValueError("Origem de anotação inválida.")
    span_text = text[start:end]
    return {
        "text": span_text,
        "start": start,
        "end": end,
        "source": source,
        "detector_score": detector_score,
        "suggested_assertion": classifier.predict(text, start, end),
        "rankings": rank_candidates(span_text, mappers, top_k=top_k),
    }


def replace_overlapping_span(
    spans: list[dict[str, object]],
    replacement: dict[str, object],
) -> list[dict[str, object]]:
    start = int(replacement["start"])
    end = int(replacement["end"])
    retained = [
        span
        for span in spans
        if not (start < int(span["end"]) and int(span["start"]) < end)
    ]
    return sorted(retained + [replacement], key=lambda span: (span["start"], span["end"]))


def retrieval_for_candidate(
    rankings: dict[str, list[dict[str, object]]],
    hpo_id: str,
) -> list[dict[str, object]]:
    retrieval = [
        {
            "method": str(candidate["method"]),
            "rank": int(candidate["rank"]),
            "score": (
                float(candidate["score"])
                if candidate.get("score") is not None
                else None
            ),
            "reason": str(candidate["reason"]),
            "matched_term": candidate.get("matched_term"),
            "matched_language": candidate.get("matched_language"),
            "term_source": candidate.get("term_source"),
        }
        for candidates in rankings.values()
        for candidate in candidates
        if candidate["hpo_id"] == hpo_id
    ]
    return sorted(
        retrieval,
        key=lambda item: (
            str(item["method"]),
            int(item["rank"]),
            str(item.get("matched_term") or "").casefold(),
        ),
    )


def normalize_characterization(
    characterization: dict[str, object] | None,
) -> tuple[dict[str, str | None], list[dict[str, str]]]:
    raw = characterization or {}
    normalized: dict[str, str | None] = {}
    pending = []
    for field, label in CHARACTERIZATION_FIELDS:
        value = raw.get(field)
        cleaned = str(value).strip() if value is not None else ""
        normalized[field] = cleaned or None
        if not cleaned:
            pending.append({"field": field, "label": label})
    return normalized, pending


def build_workbench_export(
    *,
    text: str,
    data_version: str,
    reviews: list[dict[str, object]],
    ontology: OntologyIndex,
    terminology_provenance: dict[str, object] | None = None,
    generated_at: str | None = None,
) -> dict[str, object]:
    annotations = []
    for review in sorted(reviews, key=lambda item: (item["start"], item["end"])):
        decision = str(review["decision"])
        selected_hpo_id = review.get("selected_hpo_id")
        selected = None
        retrieval = []
        if decision == "include":
            if not selected_hpo_id:
                raise ValueError("Anotação incluída sem HPO selecionado.")
            concept = ontology.require(str(selected_hpo_id))
            selected = {
                "hpo_id": concept.hpo_id,
                "label_pt": concept.label_pt,
                "label_en": concept.label_en,
                "label_pt_status": "official" if concept.label_pt else "unavailable",
            }
            retrieval = retrieval_for_candidate(
                review.get("rankings", {}), concept.hpo_id
            )
        characterization, pending_characterization = normalize_characterization(
            review.get("characterization")
        )
        annotations.append(
            {
                "text": str(review["text"]),
                "start": int(review["start"]),
                "end": int(review["end"]),
                "source": str(review["source"]),
                "origin": (
                    "automatic" if review["source"] == "lexical" else "manual"
                ),
                "decision": decision,
                "human_decision": {
                    "status": decision,
                    "reviewed": True,
                    "modified_suggestion": bool(review["human_modified"]),
                },
                "assertion": str(review["assertion"]),
                "suggested_assertion": str(review["suggested_assertion"]),
                "selected_hpo": selected,
                "retrieval": retrieval,
                "human_modified": bool(review["human_modified"]),
                "characterization": characterization,
                "pending_characterization": pending_characterization,
            }
        )

    summary = {
        "automatic": sum(item["source"] == "lexical" for item in annotations),
        "manual": sum(item["source"] == "manual" for item in annotations),
        "included": sum(item["decision"] == "include" for item in annotations),
        "discarded": sum(item["decision"] == "discard" for item in annotations),
        "human_modified": sum(item["human_modified"] for item in annotations),
        "included_with_pending_characterization": sum(
            item["decision"] == "include" and bool(item["pending_characterization"])
            for item in annotations
        ),
        "pending_characterization_fields": sum(
            len(item["pending_characterization"])
            for item in annotations
            if item["decision"] == "include"
        ),
    }
    return {
        "schema_version": "hpo-ptbr-review-v1",
        "generated_at": generated_at or datetime.now(UTC).isoformat(),
        "data_version": data_version,
        "terminology_provenance": terminology_provenance or {
            "data_version": data_version
        },
        "text": text,
        "annotations": annotations,
        "summary": summary,
        "limitations": [
            "Conteúdo público ou sintético; não usar dados clínicos reais.",
            "Scores de recuperação ordenam candidatos e não representam confiança clínica.",
            "O arquivo registra revisão fenotípica e não constitui diagnóstico ou Phenopacket.",
        ],
    }
