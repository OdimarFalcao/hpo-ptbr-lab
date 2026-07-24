from __future__ import annotations

import hashlib
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
