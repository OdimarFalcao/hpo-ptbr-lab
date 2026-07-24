from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from huggingface_hub import snapshot_download

from hpo_ptbr.mention_ner import (
    DEFAULT_MENTION_MODEL_NAME,
    DEFAULT_MENTION_MODEL_REVISION,
    MODEL_ALLOW_PATTERNS,
    model_file_manifest,
)


def main() -> None:
    snapshot_path = snapshot_download(
        repo_id=DEFAULT_MENTION_MODEL_NAME,
        revision=DEFAULT_MENTION_MODEL_REVISION,
        allow_patterns=list(MODEL_ALLOW_PATTERNS),
    )
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "model_name": DEFAULT_MENTION_MODEL_NAME,
        "model_revision": DEFAULT_MENTION_MODEL_REVISION,
        "files": model_file_manifest(snapshot_path),
    }
    output_path = ROOT / "data/results/mention_detection_model_manifest.json"
    output_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
