from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean

from .mention_evaluation import MentionPrediction


@dataclass(frozen=True)
class TokenPrediction:
    start: int
    end: int
    label: str
    score: float


def decode_bioes_mentions(
    case_id: str,
    text: str,
    tokens: list[TokenPrediction],
    *,
    accepted_entity_groups: frozenset[str] = frozenset({"PROBLEM"}),
) -> list[MentionPrediction]:
    mentions: list[MentionPrediction] = []
    current_start: int | None = None
    current_end: int | None = None
    current_group: str | None = None
    current_scores: list[float] = []

    def flush() -> None:
        nonlocal current_start, current_end, current_group, current_scores
        if (
            current_start is not None
            and current_end is not None
            and current_group is not None
        ):
            mentions.append(
                MentionPrediction(
                    case_id=case_id,
                    text=text[current_start:current_end],
                    start=current_start,
                    end=current_end,
                    label=current_group,
                    score=round(fmean(current_scores), 6),
                )
            )
        current_start = None
        current_end = None
        current_group = None
        current_scores = []

    for token in tokens:
        if (
            token.start < 0
            or token.end <= token.start
            or token.end > len(text)
        ):
            raise ValueError("Token com offsets inválidos.")
        if token.label == "O" or "-" not in token.label:
            flush()
            continue
        prefix, entity_group = token.label.split("-", 1)
        if entity_group not in accepted_entity_groups:
            flush()
            continue
        if prefix == "S":
            flush()
            current_start = token.start
            current_end = token.end
            current_group = entity_group
            current_scores = [token.score]
            flush()
        elif prefix == "B":
            flush()
            current_start = token.start
            current_end = token.end
            current_group = entity_group
            current_scores = [token.score]
        elif prefix in {"I", "E"}:
            if current_group != entity_group:
                flush()
                current_start = token.start
                current_group = entity_group
                current_scores = []
            current_end = token.end
            current_scores.append(token.score)
            if prefix == "E":
                flush()
        else:
            flush()

    flush()
    return mentions
