from copy import deepcopy

from hpo_ptbr.experiment import promotion_gate, result_fingerprint


def _summary_rows():
    rows = []
    for method in ("exact", "fuzzy", "bm25", "semantic", "hybrid"):
        for stratum in ("ALL", "official_label", "orthographic_variation", "clinical_paraphrase"):
            rows.append(
                {
                    "method": method,
                    "stratum": stratum,
                    "accuracy_at_1": 1.0 if stratum == "official_label" else 0.5,
                    "accuracy_at_5": 0.2 if stratum == "clinical_paraphrase" else 0.5,
                    "mrr_at_20": 0.5,
                    "latency_mean_ms": 1.0,
                    "invalid_id_rate": 0.0,
                }
            )
    return rows


def test_promotion_gate_accepts_strict_paraphrase_gain_with_guardrails():
    rows = _summary_rows()
    for row in rows:
        if row["method"] == "hybrid" and row["stratum"] == "clinical_paraphrase":
            row["accuracy_at_5"] = 0.3
        if row["method"] == "fuzzy" and row["stratum"] == "orthographic_variation":
            row["accuracy_at_1"] = 1.0
        if row["method"] == "hybrid" and row["stratum"] == "orthographic_variation":
            row["accuracy_at_1"] = 0.9
    assert promotion_gate(rows)["passed"] is True


def test_result_fingerprint_ignores_only_timing():
    details = [{"case_id": "A", "target_rank": 1, "latency_ms": 2.0}]
    summary = [{"method": "exact", "latency_mean_ms": 2.0, "accuracy_at_1": 1.0}]
    changed_timing_details = deepcopy(details)
    changed_timing_summary = deepcopy(summary)
    changed_timing_details[0]["latency_ms"] = 99.0
    changed_timing_summary[0]["latency_mean_ms"] = 99.0
    assert result_fingerprint(details, summary) == result_fingerprint(
        changed_timing_details,
        changed_timing_summary,
    )
    changed_rank = deepcopy(details)
    changed_rank[0]["target_rank"] = 2
    assert result_fingerprint(details, summary) != result_fingerprint(changed_rank, summary)
