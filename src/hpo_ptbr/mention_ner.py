from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from pathlib import Path
from time import perf_counter

from .mention_detection import TokenPrediction, decode_bioes_mentions
from .mention_evaluation import MentionPrediction

DEFAULT_MENTION_MODEL_NAME = "HUMADEX/portugese_medical_ner"
DEFAULT_MENTION_MODEL_REVISION = "51368a80d5b81aa211199aa1988574869197f288"
MODEL_ALLOW_PATTERNS = (
    "config.json",
    "model.safetensors",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.txt",
)
REQUIRED_MODEL_FILES = (
    "config.json",
    "model.safetensors",
    "tokenizer_config.json",
    "vocab.txt",
)
WORD_SEPARATOR_PATTERN = re.compile(r"^[\s-]*$")


def _entity_group(label: str) -> str:
    return "O" if label == "O" else label.split("-", 1)[-1]


def decode_word_group_mentions(
    case_id: str,
    text: str,
    *,
    offsets: list[tuple[int, int]],
    word_ids: list[int | None],
    probabilities: list[list[float]],
    id2label: dict[int, str],
    accepted_entity_groups: frozenset[str] = frozenset({"PROBLEM"}),
) -> list[MentionPrediction]:
    if not (len(offsets) == len(word_ids) == len(probabilities)):
        raise ValueError("Tokens, offsets e probabilidades possuem tamanhos diferentes.")

    label_groups: dict[str, list[int]] = defaultdict(list)
    for label_id, label in id2label.items():
        label_groups[_entity_group(label)].append(int(label_id))

    grouped_indices: dict[int, list[int]] = defaultdict(list)
    for token_index, word_id in enumerate(word_ids):
        if word_id is not None and offsets[token_index] != (0, 0):
            grouped_indices[int(word_id)].append(token_index)

    words: list[tuple[int, int, str, float]] = []
    for word_id in sorted(grouped_indices):
        token_indices = grouped_indices[word_id]
        start = min(offsets[index][0] for index in token_indices)
        end = max(offsets[index][1] for index in token_indices)
        if start < 0 or end <= start or end > len(text):
            raise ValueError("Offsets inválidos após agregação por palavra.")
        word_text = text[start:end]
        group_scores = {
            group: sum(
                sum(probabilities[index][label_id] for label_id in label_ids)
                for index in token_indices
            )
            / len(token_indices)
            for group, label_ids in label_groups.items()
        }
        group = max(
            group_scores,
            key=lambda name: (group_scores[name], name == "O", name),
        )
        if not any(character.isalnum() for character in word_text):
            group = "O"
        words.append((start, end, group, group_scores[group]))

    mentions: list[MentionPrediction] = []
    current: list[tuple[int, int, str, float]] = []

    def flush() -> None:
        nonlocal current
        if current:
            start = current[0][0]
            end = current[-1][1]
            mentions.append(
                MentionPrediction(
                    case_id=case_id,
                    text=text[start:end],
                    start=start,
                    end=end,
                    label=current[0][2],
                    score=round(sum(item[3] for item in current) / len(current), 6),
                )
            )
        current = []

    for word in words:
        start, _, group, _ = word
        separator = text[current[-1][1] : start] if current else ""
        if group in accepted_entity_groups and (
            not current or WORD_SEPARATOR_PATTERN.fullmatch(separator)
        ):
            current.append(word)
            continue
        flush()
        if group in accepted_entity_groups:
            current.append(word)
    flush()
    return mentions


def sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_file_manifest(snapshot_path: str | Path) -> list[dict[str, object]]:
    root = Path(snapshot_path)
    missing = [name for name in REQUIRED_MODEL_FILES if not (root / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"Arquivos obrigatórios ausentes no snapshot NER: {missing}"
        )
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in sorted(root.iterdir(), key=lambda item: item.name)
        if path.is_file() and path.name in MODEL_ALLOW_PATTERNS
    ]


class TransformerMentionDetector:
    def __init__(
        self,
        *,
        model_name: str = DEFAULT_MENTION_MODEL_NAME,
        revision: str = DEFAULT_MENTION_MODEL_REVISION,
        local_files_only: bool = True,
    ) -> None:
        import torch
        from transformers import AutoModelForTokenClassification, AutoTokenizer

        self.torch = torch
        self.model_name = model_name
        self.revision = revision
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            revision=revision,
            local_files_only=local_files_only,
            use_fast=True,
        )
        if not self.tokenizer.is_fast:
            raise ValueError("O detector requer tokenizer rápido com offsets.")
        self.model = AutoModelForTokenClassification.from_pretrained(
            model_name,
            revision=revision,
            local_files_only=local_files_only,
            use_safetensors=True,
        )
        self.model.eval()

    def predict(
        self,
        case_id: str,
        text: str,
    ) -> tuple[list[MentionPrediction], float]:
        started_at = perf_counter()
        encoded = self.tokenizer(
            text,
            return_offsets_mapping=True,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        )
        offsets = encoded.pop("offset_mapping")[0].tolist()
        with self.torch.no_grad():
            logits = self.model(**encoded).logits[0]
            probabilities = self.torch.softmax(logits, dim=-1)
            predicted_ids = logits.argmax(dim=-1).tolist()
            predicted_scores = probabilities.max(dim=-1).values.tolist()

        tokens = []
        for (start, end), label_id, score in zip(
            offsets,
            predicted_ids,
            predicted_scores,
            strict=True,
        ):
            if start == end == 0:
                continue
            tokens.append(
                TokenPrediction(
                    start=int(start),
                    end=int(end),
                    label=str(self.model.config.id2label[int(label_id)]),
                    score=float(score),
                )
            )
        mentions = decode_bioes_mentions(case_id, text, tokens)
        latency_ms = round((perf_counter() - started_at) * 1000, 3)
        return mentions, latency_ms

    def predict_word_aggregated(
        self,
        case_id: str,
        text: str,
    ) -> tuple[list[MentionPrediction], float]:
        started_at = perf_counter()
        encoded = self.tokenizer(
            text,
            return_offsets_mapping=True,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        )
        offsets = [tuple(item) for item in encoded.pop("offset_mapping")[0].tolist()]
        word_ids = encoded.word_ids(0)
        with self.torch.no_grad():
            logits = self.model(**encoded).logits[0]
            probabilities = self.torch.softmax(logits, dim=-1).tolist()
        mentions = decode_word_group_mentions(
            case_id,
            text,
            offsets=offsets,
            word_ids=word_ids,
            probabilities=probabilities,
            id2label={
                int(label_id): str(label)
                for label_id, label in self.model.config.id2label.items()
            },
        )
        latency_ms = round((perf_counter() - started_at) * 1000, 3)
        return mentions, latency_ms
