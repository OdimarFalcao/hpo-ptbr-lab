from __future__ import annotations

import hashlib
import json
from pathlib import Path


def result_fingerprint(
    details: list[dict[str, object]],
    summary: list[dict[str, object]],
) -> str:
    stable_details = [
        {key: value for key, value in row.items() if key != "latency_ms"}
        for row in details
    ]
    stable_summary = [
        {key: value for key, value in row.items() if key != "latency_mean_ms"}
        for row in summary
    ]
    payload = json.dumps(
        {"details": stable_details, "summary": stable_summary},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def promotion_gate(summary: list[dict[str, object]]) -> dict[str, object]:
    indexed = {
        (str(row["method"]), str(row["stratum"])): row
        for row in summary
    }

    def metric(method: str, stratum: str, name: str) -> float:
        return float(indexed[(method, stratum)][name])

    individual_methods = ("exact", "fuzzy", "bm25", "semantic")
    best_individual_paraphrase_at_5 = max(
        metric(method, "clinical_paraphrase", "accuracy_at_5")
        for method in individual_methods
    )
    hybrid_paraphrase_at_5 = metric("hybrid", "clinical_paraphrase", "accuracy_at_5")
    hybrid_official_at_1 = metric("hybrid", "official_label", "accuracy_at_1")
    hybrid_orthographic_at_1 = metric("hybrid", "orthographic_variation", "accuracy_at_1")
    fuzzy_orthographic_at_1 = metric("fuzzy", "orthographic_variation", "accuracy_at_1")
    hybrid_invalid_id_rate = metric("hybrid", "ALL", "invalid_id_rate")
    criteria = {
        "paraphrase_at_5_strictly_better": (
            hybrid_paraphrase_at_5 > best_individual_paraphrase_at_5
        ),
        "official_at_1_is_100_percent": hybrid_official_at_1 == 1.0,
        "orthographic_drop_at_most_one_case": (
            hybrid_orthographic_at_1 >= fuzzy_orthographic_at_1 - 0.1
        ),
        "invalid_id_rate_is_zero": hybrid_invalid_id_rate == 0.0,
    }
    return {
        "passed": all(criteria.values()),
        "criteria": criteria,
        "observed": {
            "best_individual_paraphrase_accuracy_at_5": best_individual_paraphrase_at_5,
            "hybrid_paraphrase_accuracy_at_5": hybrid_paraphrase_at_5,
            "hybrid_official_accuracy_at_1": hybrid_official_at_1,
            "hybrid_orthographic_accuracy_at_1": hybrid_orthographic_at_1,
            "fuzzy_orthographic_accuracy_at_1": fuzzy_orthographic_at_1,
            "hybrid_invalid_id_rate": hybrid_invalid_id_rate,
        },
    }


def verify_frozen_holdout(cases_path: str | Path, manifest_path: str | Path) -> dict[str, object]:
    cases = Path(cases_path)
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if manifest.get("status") != "frozen":
        raise ValueError("O manifesto do holdout não está congelado.")
    checksum = hashlib.sha256(cases.read_bytes()).hexdigest()
    if checksum != manifest.get("sha256"):
        raise ValueError("O checksum do holdout difere do manifesto.")
    return manifest
