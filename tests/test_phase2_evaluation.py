import json

import pytest

from hpo_ptbr.data import HpoRecord
from hpo_ptbr.evidence import EvidenceExtractor
from hpo_ptbr.ontology import HpoConcept, OntologyIndex
from hpo_ptbr.phase2_evaluation import (
    audit_split_leakage,
    evaluate_phase2,
    load_phase2_dataset,
    morphological_fingerprint,
)
from hpo_ptbr.rankers import FuzzyMapper


def _ontology() -> OntologyIndex:
    root = HpoConcept("HP:0000118", "Phenotypic abnormality", "Anormalidade fenotípica", "", "", (), (), (), ("HP:0000508",))
    ptosis = HpoConcept("HP:0000508", "Ptosis", "Ptose", "", "", (), (), ("HP:0000118",), ())
    return OntologyIndex({root.hpo_id: root, ptosis.hpo_id: ptosis}, "test")


def _dataset(split: str = "development") -> dict[str, object]:
    text = "A pálpebra permanece caída ao anoitecer."
    mention = "pálpebra permanece caída"
    start = text.index(mention)
    characterization = {field: None for field in ("onset_age", "severity", "evolution", "frequency", "laterality", "family_history")}
    return {
        "schema_version": "phase2-synthetic-cases-v1",
        "dataset_id": f"test-{split}",
        "split": split,
        "source": {"kind": "synthetic", "contains_real_patient_data": False},
        "cases": [{
            "case_id": f"{split}-001",
            "text": text,
            "scenario_tags": ["linguagem_leiga"],
            "template_family": "queda_palpebral",
            "annotations": [{
                "mention_text": mention,
                "start": start,
                "end": start + len(mention),
                "hpo_id": "HP:0000508",
                "label_pt_snapshot": "Ptose",
                "context": "present",
                "surface_category": "clinical_paraphrase",
                "surface_source": "synthetic_paraphrase_pending_clinical_review",
                "evidence_limit": "Não informa causa.",
                "specificity": {"grade": "supported_general", "note": "Sem subtipo."},
                "characterization": characterization,
                "information_absent": list(characterization),
            }],
        }],
    }


def test_loads_real_development_dataset_and_validates_offsets(tmp_path):
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps(_dataset(), ensure_ascii=False), encoding="utf-8")

    loaded = load_phase2_dataset(path, _ontology(), expected_split="development")

    assert loaded["dataset_id"] == "test-development"


def test_rejects_literal_hpo_label_as_main_clue(tmp_path):
    dataset = _dataset()
    annotation = dataset["cases"][0]["annotations"][0]
    dataset["cases"][0]["text"] = "Há Ptose."
    annotation["mention_text"] = "Ptose"
    annotation["start"] = 3
    annotation["end"] = 8
    path = tmp_path / "literal.json"
    path.write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="literal"):
        load_phase2_dataset(path, _ontology())


def test_leakage_audit_blocks_templates_morphology_and_related_concepts():
    development = _dataset("development")
    validation = _dataset("validation")

    issues = audit_split_leakage([development, validation], _ontology())

    issue_types = {issue["type"] for issue in issues}
    assert {"case_text", "mention_text", "morphological_fingerprint", "template_family", "official_term_overlap", "related_concept"} <= issue_types


def test_morphological_fingerprint_normalizes_accents_and_inflection():
    assert morphological_fingerprint("mãos caídas") == morphological_fingerprint("maos caidos")


def test_evaluation_records_paraphrase_and_review_burden_without_human_time():
    dataset = _dataset()
    extractor = EvidenceExtractor(FuzzyMapper([HpoRecord("HP:0000508", "Ptosis", "Ptose")], "test"))

    details, errors, summary = evaluate_phase2(extractor, dataset, _ontology())

    assert details[0]["error_categories"]
    assert {error["category"] for error in errors} >= {"mention_not_detected", "paraphrase_failure"}
    assert summary["review"]["human_elapsed_seconds"] is None
    assert summary["review"]["human_observations"] == 0
    assert summary["pending_fields"]["recall"] == 1.0
