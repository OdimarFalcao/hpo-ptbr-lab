from __future__ import annotations

from html import escape


def highlight_evidence(text: str, spans: list[dict[str, object]]) -> str:
    ordered = sorted(spans, key=lambda span: (int(span["start"]), int(span["end"])))
    parts = []
    cursor = 0
    for span in ordered:
        start = int(span["start"])
        end = int(span["end"])
        if start < cursor or end <= start or end > len(text):
            raise ValueError("Offsets de evidência inválidos para destaque.")
        parts.append(escape(text[cursor:start]))
        parts.append(f"<mark>{escape(text[start:end])}</mark>")
        cursor = end
    parts.append(escape(text[cursor:]))
    return '<div class="evidence-text">' + "".join(parts) + "</div>"


def unmatched_mentions(
    case: dict[str, object], spans: list[dict[str, object]]
) -> list[dict[str, object]]:
    predicted_offsets = {
        (int(span["start"]), int(span["end"])) for span in spans
    }
    return [
        mention
        for mention in case.get("mentions", [])
        if (int(mention["start"]), int(mention["end"])) not in predicted_offsets
    ]


def build_review_export(
    analysis: dict[str, object], reviews: list[dict[str, object]]
) -> dict[str, object]:
    spans = analysis.get("spans", [])
    if len(spans) != len(reviews):
        raise ValueError("Cada evidência deve possuir uma decisão de revisão.")
    return analysis | {"human_review": reviews}
