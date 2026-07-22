from __future__ import annotations

from collections.abc import Sequence

import numpy as np

DEFAULT_SAPBERT_MODEL_NAME = (
    "cambridgeltl/SapBERT-UMLS-2020AB-all-lang-from-XLMR"
)
DEFAULT_SAPBERT_MODEL_REVISION = "5731ee8d59538ce6557641b97ed5c83f4237dd06"
DEFAULT_SAPBERT_MODEL_SHA256 = (
    "a5102c2c09ac7fd04b685251bd467cf29f9d883c1fd97d5c09268b9e216ea243"
)


class SapBertEncoder:
    def __init__(
        self,
        *,
        model_name: str = DEFAULT_SAPBERT_MODEL_NAME,
        revision: str = DEFAULT_SAPBERT_MODEL_REVISION,
        batch_size: int = 64,
        max_length: int = 25,
        local_files_only: bool = True,
    ) -> None:
        if batch_size < 1:
            raise ValueError("batch_size deve ser positivo.")
        if max_length < 2:
            raise ValueError("max_length deve ser pelo menos 2.")

        import torch
        from transformers import AutoModel, AutoTokenizer

        self._torch = torch
        self.batch_size = batch_size
        self.max_length = max_length
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            revision=revision,
            local_files_only=local_files_only,
        )
        self.model = AutoModel.from_pretrained(
            model_name,
            revision=revision,
            local_files_only=local_files_only,
            use_safetensors=True,
        ).to(self.device)
        self.model.eval()

    def encode_document(
        self,
        sentences: list[str],
        *,
        normalize_embeddings: bool,
        show_progress_bar: bool,
    ) -> np.ndarray:
        return self._encode(sentences, normalize_embeddings=normalize_embeddings)

    def encode_query(
        self,
        sentences: list[str],
        *,
        normalize_embeddings: bool,
        show_progress_bar: bool,
    ) -> np.ndarray:
        return self._encode(sentences, normalize_embeddings=normalize_embeddings)

    def _encode(
        self,
        sentences: Sequence[str],
        *,
        normalize_embeddings: bool,
    ) -> np.ndarray:
        if not sentences:
            return np.empty((0, int(self.model.config.hidden_size)), dtype=np.float32)

        batches = []
        with self._torch.inference_mode():
            for start in range(0, len(sentences), self.batch_size):
                batch = list(sentences[start : start + self.batch_size])
                tokens = self.tokenizer(
                    batch,
                    padding="max_length",
                    truncation=True,
                    max_length=self.max_length,
                    return_tensors="pt",
                )
                tokens = {key: value.to(self.device) for key, value in tokens.items()}
                embeddings = self.model(**tokens).last_hidden_state[:, 0, :]
                if normalize_embeddings:
                    embeddings = self._torch.nn.functional.normalize(
                        embeddings, p=2, dim=1
                    )
                batches.append(embeddings.cpu().numpy().astype(np.float32))
        return np.concatenate(batches, axis=0)
