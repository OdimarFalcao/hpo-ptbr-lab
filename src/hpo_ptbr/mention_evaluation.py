from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MentionPrediction:
    case_id: str
    text: str
    start: int
    end: int
    label: str
    score: float | None = None


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


def evaluate_mention_predictions(
    cases: list[dict[str, object]],
    predictions: list[MentionPrediction],
    *,
    accepted_labels: frozenset[str] = frozenset({"PROBLEM"}),
    relaxed_iou_threshold: float = 0.5,
) -> dict[str, object]:
    if not cases:
        raise ValueError("Informe ao menos um caso para avaliar menções.")
    if not 0 < relaxed_iou_threshold <= 1:
        raise ValueError("relaxed_iou_threshold deve estar entre 0 e 1.")

    texts_by_case: dict[str, str] = {}
    gold_spans: set[tuple[str, int, int]] = set()
    critical_spans: set[tuple[str, int, int]] = set()
    for case in cases:
        case_id = str(case.get("id", ""))
        text = str(case.get("text", ""))
        if not case_id or case_id in texts_by_case or not text:
            raise ValueError("Casos devem possuir IDs únicos e texto não vazio.")
        texts_by_case[case_id] = text
        mentions = case.get("mentions")
        if not isinstance(mentions, list) or not mentions:
            raise ValueError(f"Caso sem menções: {case_id}.")
        for mention in mentions:
            if not isinstance(mention, dict):
                raise ValueError(f"Menção inválida no caso {case_id}.")
            start = int(mention["start"])
            end = int(mention["end"])
            mention_text = str(mention["text"])
            if start < 0 or end <= start or text[start:end] != mention_text:
                raise ValueError(f"Offsets de ouro inválidos no caso {case_id}.")
            key = (case_id, start, end)
            if key in gold_spans:
                raise ValueError(f"Menção de ouro duplicada no caso {case_id}.")
            gold_spans.add(key)
            if mention.get("detectable") is False:
                critical_spans.add(key)

    valid_predictions: list[MentionPrediction] = []
    invalid_predictions = 0
    unsupported_predictions = 0
    for prediction in predictions:
        if prediction.label not in accepted_labels:
            unsupported_predictions += 1
            continue
        text = texts_by_case.get(prediction.case_id)
        if (
            text is None
            or prediction.start < 0
            or prediction.end <= prediction.start
            or prediction.end > len(text)
            or text[prediction.start : prediction.end] != prediction.text
        ):
            invalid_predictions += 1
            continue
        valid_predictions.append(prediction)

    exact_prediction_spans = {
        (prediction.case_id, prediction.start, prediction.end)
        for prediction in valid_predictions
    }
    exact_matches = gold_spans & exact_prediction_spans
    exact_precision = (
        len(exact_matches) / len(valid_predictions)
        if valid_predictions
        else 0.0
    )
    exact_recall = len(exact_matches) / len(gold_spans)

    unmatched_gold = set(gold_spans)
    relaxed_matches = 0
    for prediction in sorted(
        valid_predictions,
        key=lambda item: (item.case_id, item.start, item.end, item.label),
    ):
        candidates = [
            (
                _span_iou(
                    prediction.start,
                    prediction.end,
                    gold_start,
                    gold_end,
                ),
                (case_id, gold_start, gold_end),
            )
            for case_id, gold_start, gold_end in unmatched_gold
            if case_id == prediction.case_id
        ]
        if not candidates:
            continue
        overlap, matched_gold = max(
            candidates,
            key=lambda item: (item[0], -item[1][1], -item[1][2]),
        )
        if overlap >= relaxed_iou_threshold:
            relaxed_matches += 1
            unmatched_gold.remove(matched_gold)

    relaxed_precision = (
        relaxed_matches / len(valid_predictions)
        if valid_predictions
        else 0.0
    )
    relaxed_recall = relaxed_matches / len(gold_spans)
    critical_matches = exact_matches & critical_spans
    total_predictions = len(predictions)

    return {
        "n_cases": len(cases),
        "n_gold_mentions": len(gold_spans),
        "n_critical_mentions": len(critical_spans),
        "n_predictions": total_predictions,
        "n_valid_predictions": len(valid_predictions),
        "invalid_predictions": invalid_predictions,
        "unsupported_predictions": unsupported_predictions,
        "exact_span_precision": round(exact_precision, 4),
        "exact_span_recall": round(exact_recall, 4),
        "exact_span_f1": round(_f1(exact_precision, exact_recall), 4),
        "relaxed_span_precision": round(relaxed_precision, 4),
        "relaxed_span_recall": round(relaxed_recall, 4),
        "relaxed_span_f1_iou_0_5": round(
            _f1(relaxed_precision, relaxed_recall),
            4,
        ),
        "critical_paraphrase_recall": round(
            len(critical_matches) / len(critical_spans),
            4,
        )
        if critical_spans
        else 0.0,
        "invalid_prediction_rate": round(
            invalid_predictions / total_predictions,
            4,
        )
        if total_predictions
        else 0.0,
    }
