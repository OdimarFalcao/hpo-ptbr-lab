from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Protocol

from .evidence import EvidenceExtractor, EvidenceSpan

ASSERTION_CLASSES = ("present", "absent", "uncertain", "family_history")


@dataclass(frozen=True)
class AlwaysPresentAssertionClassifier:
    method: str = "always_present"

    def predict(self, text: str, start: int, end: int) -> str:
        if start < 0 or end <= start or end > len(text):
            raise ValueError("Offsets inválidos para classificação de contexto.")
        return "present"


class AssertionClassifier(Protocol):
    method: str

    def predict(self, text: str, start: int, end: int) -> str: ...


def _f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _span_iou(
    first_start: int,
    first_end: int,
    second_start: int,
    second_end: int,
) -> float:
    intersection = max(
        0,
        min(first_end, second_end) - max(first_start, second_start),
    )
    if not intersection:
        return 0.0
    union = max(first_end, second_end) - min(first_start, second_start)
    return intersection / union


def _relaxed_match_count(
    gold_spans: list[tuple[str, int, int]],
    predicted_spans: list[tuple[str, int, int]],
    threshold: float,
) -> int:
    unmatched_gold = set(gold_spans)
    matches = 0
    for case_id, start, end in sorted(predicted_spans):
        candidates = [
            (
                _span_iou(start, end, gold_start, gold_end),
                (gold_case_id, gold_start, gold_end),
            )
            for gold_case_id, gold_start, gold_end in unmatched_gold
            if gold_case_id == case_id
        ]
        if not candidates:
            continue
        overlap, matched_gold = max(
            candidates,
            key=lambda item: (item[0], -item[1][1], -item[1][2]),
        )
        if overlap >= threshold:
            matches += 1
            unmatched_gold.remove(matched_gold)
    return matches


def _macro_f1(gold: list[str], predicted: list[str]) -> float:
    scores = []
    for assertion in ASSERTION_CLASSES:
        true_positive = sum(
            expected == assertion and observed == assertion
            for expected, observed in zip(gold, predicted, strict=True)
        )
        false_positive = sum(
            expected != assertion and observed == assertion
            for expected, observed in zip(gold, predicted, strict=True)
        )
        false_negative = sum(
            expected == assertion and observed != assertion
            for expected, observed in zip(gold, predicted, strict=True)
        )
        precision = (
            true_positive / (true_positive + false_positive)
            if true_positive + false_positive
            else 0.0
        )
        recall = (
            true_positive / (true_positive + false_negative)
            if true_positive + false_negative
            else 0.0
        )
        scores.append(_f1(precision, recall))
    return round(statistics.fmean(scores), 4)


def _target_rank(span: EvidenceSpan | None, target_hpo_id: str) -> int | None:
    if span is None:
        return None
    return next(
        (
            candidate.rank
            for candidate in span.candidates
            if candidate.hpo_id == target_hpo_id
        ),
        None,
    )


def _stratify(
    gold_details: list[dict[str, object]],
    field: str,
) -> dict[str, dict[str, float | int]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in gold_details:
        grouped[str(row[field])].append(row)
    result: dict[str, dict[str, float | int]] = {}
    for value, rows in sorted(grouped.items()):
        count = len(rows)
        result[value] = {
            "n": count,
            "exact_span_recall": round(
                sum(bool(row["exact_span_detected"]) for row in rows) / count,
                4,
            ),
            "linking_accuracy_at_1": round(
                sum(row["gold_span_target_rank"] == 1 for row in rows) / count,
                4,
            ),
            "linking_accuracy_at_5": round(
                sum(
                    bool(row["gold_span_target_rank"])
                    and int(row["gold_span_target_rank"]) <= 5
                    for row in rows
                )
                / count,
                4,
            ),
            "assertion_accuracy": round(
                sum(bool(row["assertion_correct"]) for row in rows) / count,
                4,
            ),
            "end_to_end_recall": round(
                sum(bool(row["end_to_end_correct"]) for row in rows) / count,
                4,
            ),
        }
    return result


def evaluate_benchmark_method(
    extractor: EvidenceExtractor,
    cases: list[dict[str, object]],
    *,
    assertion_classifier: AssertionClassifier | None = None,
    detected_span_top_k: int = 10,
    gold_span_top_k: int = 20,
    relaxed_iou_threshold: float = 0.5,
) -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
    dict[str, object],
]:
    if not cases:
        raise ValueError("Informe casos para avaliação do benchmark.")
    if not 0 < relaxed_iou_threshold <= 1:
        raise ValueError("relaxed_iou_threshold deve estar entre 0 e 1.")
    classifier = assertion_classifier or AlwaysPresentAssertionClassifier()
    valid_hpo_ids = {record.hpo_id for record in extractor.mapper.records}

    gold_details: list[dict[str, object]] = []
    prediction_details: list[dict[str, object]] = []
    gold_spans: list[tuple[str, int, int]] = []
    predicted_spans: list[tuple[str, int, int]] = []
    latencies: list[float] = []
    invalid_id_count = 0
    candidate_count = 0
    negative_control_cases = 0
    negative_control_cases_with_predictions = 0

    for case in cases:
        case_id = str(case["case_id"])
        text = str(case["text"])
        mentions = case["mentions"]
        result = extractor.map_text(
            text,
            top_k=detected_span_top_k,
            max_spans=20,
        )
        latencies.append(result.latency_ms)
        if case["case_type"] == "negative_control":
            negative_control_cases += 1
            negative_control_cases_with_predictions += bool(result.spans)

        gold_by_offsets = {
            (int(mention["start"]), int(mention["end"])): mention
            for mention in mentions
        }
        predictions_by_offsets = {
            (span.start, span.end): span for span in result.spans
        }
        for span in result.spans:
            predicted_spans.append((case_id, span.start, span.end))
            candidate_ids = [candidate.hpo_id for candidate in span.candidates]
            candidate_count += len(candidate_ids)
            invalid_id_count += sum(
                candidate_id not in valid_hpo_ids for candidate_id in candidate_ids
            )
            matched_gold = gold_by_offsets.get((span.start, span.end))
            predicted_assertion = classifier.predict(text, span.start, span.end)
            top_hpo_id = candidate_ids[0] if candidate_ids else None
            end_to_end_correct = bool(
                matched_gold
                and top_hpo_id == matched_gold["hpo_id"]
                and predicted_assertion == matched_gold["assertion"]
            )
            prediction_details.append(
                {
                    "case_id": case_id,
                    "domain": case["domain"],
                    "prediction_text": span.text,
                    "start": span.start,
                    "end": span.end,
                    "detector_score": span.detector_score,
                    "top_hpo_id": top_hpo_id,
                    "top_hpo_ids": candidate_ids,
                    "predicted_assertion": predicted_assertion,
                    "exact_gold_match": matched_gold is not None,
                    "target_hpo_id": matched_gold["hpo_id"] if matched_gold else None,
                    "end_to_end_correct": end_to_end_correct,
                }
            )

        for mention in mentions:
            start = int(mention["start"])
            end = int(mention["end"])
            target_hpo_id = str(mention["hpo_id"])
            gold_spans.append((case_id, start, end))
            detected_span = predictions_by_offsets.get((start, end))
            direct_mapping = extractor.mapper.map(
                str(mention["text"]),
                top_k=gold_span_top_k,
            )
            gold_target_rank = next(
                (
                    candidate.rank
                    for candidate in direct_mapping.candidates
                    if candidate.hpo_id == target_hpo_id
                ),
                None,
            )
            predicted_assertion = classifier.predict(text, start, end)
            detected_target_rank = _target_rank(detected_span, target_hpo_id)
            end_to_end_correct = bool(
                detected_span
                and detected_span.candidates
                and detected_span.candidates[0].hpo_id == target_hpo_id
                and predicted_assertion == mention["assertion"]
            )
            gold_details.append(
                {
                    "case_id": case_id,
                    "domain": case["domain"],
                    "mention_text": mention["text"],
                    "start": start,
                    "end": end,
                    "target_hpo_id": target_hpo_id,
                    "surface_form": mention["surface_form"],
                    "assertion": mention["assertion"],
                    "exact_span_detected": detected_span is not None,
                    "detected_span_target_rank": detected_target_rank,
                    "gold_span_target_rank": gold_target_rank,
                    "gold_span_top_hpo_ids": [
                        candidate.hpo_id for candidate in direct_mapping.candidates[:5]
                    ],
                    "predicted_assertion": predicted_assertion,
                    "assertion_correct": predicted_assertion == mention["assertion"],
                    "end_to_end_correct": end_to_end_correct,
                }
            )

    exact_gold = set(gold_spans)
    exact_predictions = set(predicted_spans)
    exact_matches = len(exact_gold & exact_predictions)
    relaxed_matches = _relaxed_match_count(
        gold_spans,
        predicted_spans,
        relaxed_iou_threshold,
    )
    detection_precision = exact_matches / len(predicted_spans) if predicted_spans else 0.0
    detection_recall = exact_matches / len(gold_spans)
    relaxed_precision = (
        relaxed_matches / len(predicted_spans) if predicted_spans else 0.0
    )
    relaxed_recall = relaxed_matches / len(gold_spans)

    target_ranks = [row["gold_span_target_rank"] for row in gold_details]
    gold_assertions = [str(row["assertion"]) for row in gold_details]
    predicted_assertions = [str(row["predicted_assertion"]) for row in gold_details]
    end_to_end_true_positives = sum(
        bool(row["end_to_end_correct"]) for row in prediction_details
    )
    end_to_end_precision = (
        end_to_end_true_positives / len(prediction_details)
        if prediction_details
        else 0.0
    )
    end_to_end_recall = end_to_end_true_positives / len(gold_details)

    summary: dict[str, object] = {
        "method": getattr(extractor, "method", extractor.mapper.method),
        "detector": extractor.detector_name,
        "assertion_method": classifier.method,
        "n_cases": len(cases),
        "n_gold_mentions": len(gold_details),
        "n_predictions": len(prediction_details),
        "exact_span_precision": round(detection_precision, 4),
        "exact_span_recall": round(detection_recall, 4),
        "exact_span_f1": round(_f1(detection_precision, detection_recall), 4),
        "relaxed_span_precision": round(relaxed_precision, 4),
        "relaxed_span_recall": round(relaxed_recall, 4),
        "relaxed_span_f1_iou_0_5": round(
            _f1(relaxed_precision, relaxed_recall),
            4,
        ),
        "linking_accuracy_at_1": round(
            sum(rank == 1 for rank in target_ranks) / len(target_ranks),
            4,
        ),
        "linking_accuracy_at_5": round(
            sum(bool(rank) and int(rank) <= 5 for rank in target_ranks)
            / len(target_ranks),
            4,
        ),
        "linking_mrr_at_20": round(
            statistics.fmean(1 / int(rank) if rank else 0.0 for rank in target_ranks),
            4,
        ),
        "assertion_accuracy": round(
            sum(
                expected == observed
                for expected, observed in zip(
                    gold_assertions,
                    predicted_assertions,
                    strict=True,
                )
            )
            / len(gold_assertions),
            4,
        ),
        "assertion_macro_f1": _macro_f1(gold_assertions, predicted_assertions),
        "end_to_end_exact_precision": round(end_to_end_precision, 4),
        "end_to_end_exact_recall": round(end_to_end_recall, 4),
        "end_to_end_exact_f1": round(
            _f1(end_to_end_precision, end_to_end_recall),
            4,
        ),
        "negative_control_false_positive_rate": round(
            negative_control_cases_with_predictions / negative_control_cases,
            4,
        )
        if negative_control_cases
        else 0.0,
        "invalid_hpo_id_rate": round(invalid_id_count / candidate_count, 4)
        if candidate_count
        else 0.0,
        "latency_mean_ms": round(statistics.fmean(latencies), 3),
        "latency_median_ms": round(statistics.median(latencies), 3),
        "by_domain": _stratify(gold_details, "domain"),
        "by_surface_form": _stratify(gold_details, "surface_form"),
        "by_assertion": _stratify(gold_details, "assertion"),
    }
    return gold_details, prediction_details, summary
