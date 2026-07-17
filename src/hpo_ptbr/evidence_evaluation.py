from __future__ import annotations

import statistics

from .evidence import EvidenceExtractor


def validate_evidence_cases(
    cases: list[dict[str, object]], valid_hpo_ids: set[str]
) -> None:
    if not cases:
        raise ValueError("Informe ao menos um caso de evidência textual.")
    case_ids = [str(case.get("id", "")) for case in cases]
    if any(not case_id for case_id in case_ids) or len(case_ids) != len(set(case_ids)):
        raise ValueError("Os casos devem possuir IDs únicos e não vazios.")

    detectable_count = 0
    for case in cases:
        text = str(case.get("text", ""))
        mentions = case.get("mentions")
        if not text or not isinstance(mentions, list) or not mentions:
            raise ValueError(f"Caso inválido: {case['id']}.")
        mention_hpo_ids = []
        for mention in mentions:
            if not isinstance(mention, dict):
                raise ValueError(f"Menção inválida no caso {case['id']}.")
            start = int(mention["start"])
            end = int(mention["end"])
            mention_text = str(mention["text"])
            hpo_id = str(mention["hpo_id"])
            mention_hpo_ids.append(hpo_id)
            if start < 0 or end <= start or text[start:end] != mention_text:
                raise ValueError(f"Offsets inválidos no caso {case['id']}: {mention_text}.")
            if hpo_id not in valid_hpo_ids:
                raise ValueError(f"HPO ID inválido no caso {case['id']}: {hpo_id}.")
            if not isinstance(mention.get("detectable"), bool):
                raise ValueError(f"detectable deve ser booleano no caso {case['id']}.")
            detectable_count += bool(mention["detectable"])
        if case.get("expected_hpo_ids") != mention_hpo_ids:
            raise ValueError(f"expected_hpo_ids diverge das menções no caso {case['id']}.")
    if not detectable_count:
        raise ValueError("O conjunto deve possuir ao menos uma menção detectável.")


def evaluate_evidence_cases(
    extractor: EvidenceExtractor,
    cases: list[dict[str, object]],
    *,
    top_k: int = 5,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    valid_hpo_ids = {record.hpo_id for record in extractor.mapper.records}
    validate_evidence_cases(cases, valid_hpo_ids)

    details: list[dict[str, object]] = []
    matched_detectable_spans: set[tuple[str, int, int]] = set()
    prediction_count = 0
    invalid_id_count = 0
    candidate_count = 0
    latencies = []

    for case in cases:
        case_id = str(case["id"])
        result = extractor.map_text(str(case["text"]), top_k=top_k)
        latencies.append(result.latency_ms)
        prediction_count += len(result.spans)
        spans_by_offsets = {(span.start, span.end): span for span in result.spans}
        for span in result.spans:
            for candidate in span.candidates:
                candidate_count += 1
                invalid_id_count += candidate.hpo_id not in valid_hpo_ids

        for mention in case["mentions"]:
            start = int(mention["start"])
            end = int(mention["end"])
            target_hpo_id = str(mention["hpo_id"])
            span = spans_by_offsets.get((start, end))
            candidate_ids = [candidate.hpo_id for candidate in span.candidates] if span else []
            target_rank = next(
                (
                    candidate.rank
                    for candidate in span.candidates
                    if candidate.hpo_id == target_hpo_id
                ),
                None,
            ) if span else None
            detectable = bool(mention["detectable"])
            if detectable and span:
                matched_detectable_spans.add((case_id, start, end))
            details.append(
                {
                    "case_id": case_id,
                    "mention_text": mention["text"],
                    "start": start,
                    "end": end,
                    "target_hpo_id": target_hpo_id,
                    "detectable": detectable,
                    "span_detected": span is not None,
                    "target_rank": target_rank,
                    "top_hpo_ids": candidate_ids,
                    "detector_score": span.detector_score if span else None,
                    "latency_ms": result.latency_ms,
                }
            )

    detectable_rows = [row for row in details if row["detectable"]]
    known_miss_rows = [row for row in details if not row["detectable"]]
    summary = {
        "n_cases": len(cases),
        "n_gold_mentions": len(details),
        "n_detectable_mentions": len(detectable_rows),
        "n_known_miss_mentions": len(known_miss_rows),
        "exact_span_recall": round(
            len(matched_detectable_spans) / len(detectable_rows), 4
        ),
        "predicted_span_precision": round(
            len(matched_detectable_spans) / prediction_count, 4
        ) if prediction_count else 0.0,
        "hpo_accuracy_at_1": round(
            sum(row["target_rank"] == 1 for row in detectable_rows)
            / len(detectable_rows),
            4,
        ),
        "hpo_accuracy_at_5": round(
            sum(
                bool(row["target_rank"]) and int(row["target_rank"]) <= 5
                for row in detectable_rows
            )
            / len(detectable_rows),
            4,
        ),
        "known_miss_reproduction_rate": round(
            sum(not row["span_detected"] for row in known_miss_rows)
            / len(known_miss_rows),
            4,
        ) if known_miss_rows else 0.0,
        "invalid_id_rate": round(invalid_id_count / candidate_count, 4)
        if candidate_count
        else 0.0,
        "latency_mean_ms": round(statistics.fmean(latencies), 3),
        "latency_median_ms": round(statistics.median(latencies), 3),
    }
    return details, summary
