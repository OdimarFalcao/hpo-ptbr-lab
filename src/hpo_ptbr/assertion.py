from __future__ import annotations

from dataclasses import dataclass

from .normalize import normalize_text

SENTENCE_BOUNDARIES = ".!?;:\n"


@dataclass(frozen=True)
class PortugueseContextCueClassifier:
    method: str = "portuguese_context_cues_v1"

    family_history_cues: tuple[str, ...] = (
        "historico familiar",
        "antecedente familiar",
        "familia relata",
        "ocorrencia familiar",
    )
    uncertain_cues: tuple[str, ...] = (
        "hipotese de",
        "suspeita de",
        "como possibilidade",
        "se investiga",
    )
    absent_cues: tuple[str, ...] = (
        "nao ha",
        "nao identificou",
        "nega",
        "nao foram encontrados",
    )

    def predict(self, text: str, start: int, end: int) -> str:
        if start < 0 or end <= start or end > len(text):
            raise ValueError("Offsets inválidos para classificação de contexto.")
        left_context = self._left_sentence_context(text, start)
        normalized_context = normalize_text(left_context)
        for assertion, cues in (
            ("family_history", self.family_history_cues),
            ("uncertain", self.uncertain_cues),
            ("absent", self.absent_cues),
        ):
            if any(cue in normalized_context for cue in cues):
                return assertion
        return "present"

    @staticmethod
    def _left_sentence_context(text: str, start: int) -> str:
        boundary = max(text.rfind(character, 0, start) for character in SENTENCE_BOUNDARIES)
        return text[boundary + 1 : start]
