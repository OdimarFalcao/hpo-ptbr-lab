import json
from pathlib import Path

from hpo_ptbr.annotation import (
    build_annotation_span,
    build_workbench_export,
    find_occurrences,
    replace_overlapping_span,
    search_candidates,
)
from hpo_ptbr.assertion import PortugueseContextCueClassifier
from hpo_ptbr.data import HpoRecord
from hpo_ptbr.ontology import HpoConcept, HpoSynonym, OntologyIndex
from hpo_ptbr.ontology import load_ontology_index
from hpo_ptbr.rankers import Bm25Mapper, ExactMapper, FuzzyMapper

ROOT = Path(__file__).resolve().parents[1]


def _resources():
    records = [
        HpoRecord("HP:0000118", "Phenotypic abnormality", "Anormalidade fenotípica"),
        HpoRecord("HP:0000508", "Ptosis", "Ptose"),
        HpoRecord("HP:0000639", "Nystagmus", "Nistagmo"),
    ]
    mappers = {
        "Exact": ExactMapper(records, "test"),
        "Fuzzy": FuzzyMapper(records, "test"),
        "BM25": Bm25Mapper(records, "test"),
    }
    concepts = {
        record.hpo_id: HpoConcept(
            hpo_id=record.hpo_id,
            label_en=record.label_en,
            label_pt=record.label_pt,
            definition_en="",
            definition_pt="",
            definition_sources=(),
            synonyms=(),
            parent_ids=() if record.hpo_id == "HP:0000118" else ("HP:0000118",),
            child_ids=(),
        )
        for record in records
    }
    concepts["HP:1234567"] = HpoConcept(
        hpo_id="HP:1234567",
        label_en="Drooping upper eyelid",
        label_pt="",
        definition_en="",
        definition_pt="",
        definition_sources=(),
        synonyms=(HpoSynonym("Blepharoptosis", "exact", "clinical"),),
        parent_ids=("HP:0000118",),
        child_ids=(),
    )
    return mappers, OntologyIndex(concepts, "test")


def test_finds_repeated_occurrences_case_insensitively():
    text = "Ptose à esquerda; ptose à direita."
    assert find_occurrences(text, "ptose") == [(0, 5), (18, 23)]


def test_manual_span_replaces_overlapping_detection():
    mappers, _ = _resources()
    text = "Há pálpebra caída."
    classifier = PortugueseContextCueClassifier()
    detected = build_annotation_span(
        text,
        3,
        11,
        source="lexical",
        mappers=mappers,
        classifier=classifier,
    )
    replacement = build_annotation_span(
        text,
        3,
        17,
        source="manual",
        mappers=mappers,
        classifier=classifier,
    )

    spans = replace_overlapping_span([detected], replacement)

    assert len(spans) == 1
    assert spans[0]["text"] == "pálpebra caída"
    assert spans[0]["source"] == "manual"


def test_export_records_context_retrieval_and_human_changes():
    mappers, ontology = _resources()
    text = "Não há ptose."
    span = build_annotation_span(
        text,
        7,
        12,
        source="lexical",
        mappers=mappers,
        classifier=PortugueseContextCueClassifier(),
    )
    review = span | {
        "decision": "include",
        "assertion": "absent",
        "selected_hpo_id": "HP:0000508",
        "human_modified": False,
    }

    exported = build_workbench_export(
        text=text,
        data_version="test",
        reviews=[review],
        ontology=ontology,
        generated_at="2026-08-27T00:00:00+00:00",
    )

    annotation = exported["annotations"][0]
    assert exported["schema_version"] == "hpo-ptbr-review-v1"
    assert annotation["assertion"] == "absent"
    assert annotation["selected_hpo"]["hpo_id"] == "HP:0000508"
    assert annotation["origin"] == "automatic"
    assert annotation["human_decision"]["status"] == "include"
    assert annotation["pending_characterization"] == [
        {"field": "onset_age", "label": "idade ou início"},
        {"field": "severity", "label": "gravidade"},
        {"field": "evolution", "label": "evolução"},
        {"field": "frequency", "label": "frequência"},
        {"field": "laterality", "label": "lateralidade, quando aplicável"},
        {"field": "family_history", "label": "histórico familiar"},
    ]
    assert {item["method"] for item in annotation["retrieval"]} == {
        "exact",
        "fuzzy",
        "bm25",
    }
    assert exported["summary"]["included"] == 1
    serialized = str(exported).casefold()
    assert "confidence" not in serialized
    assert "probability" not in serialized


def test_manual_search_accepts_valid_id_and_rejects_unknown_id():
    mappers, ontology = _resources()

    direct = search_candidates("hp:0000508", mappers["Fuzzy"], ontology)
    missing = search_candidates("HP:9999999", mappers["Fuzzy"], ontology)
    root = search_candidates("HP:0000118", mappers["Fuzzy"], ontology)

    assert direct[0]["hpo_id"] == "HP:0000508"
    assert direct[0]["method"] == "hpo_id_lookup"
    assert direct[0]["score"] is None
    assert missing == []
    assert root == []


def test_export_rejects_concept_outside_phenotypic_abnormality_tree():
    mappers, ontology = _resources()
    text = "Anormalidade fenotípica"
    span = build_annotation_span(
        text,
        0,
        len(text),
        source="manual",
        mappers=mappers,
        classifier=PortugueseContextCueClassifier(),
    )
    review = span | {
        "decision": "include",
        "assertion": "present",
        "selected_hpo_id": "HP:0000118",
        "human_modified": False,
    }

    try:
        build_workbench_export(
            text=text,
            data_version="test",
            reviews=[review],
            ontology=ontology,
        )
    except ValueError as error:
        assert "fora da árvore" in str(error)
    else:
        raise AssertionError("A raiz não deve ser exportada como fenótipo")


def test_manual_search_adds_only_traceable_official_ontology_terms():
    mappers, ontology = _resources()

    results = search_candidates("Blepharoptosis", mappers["Fuzzy"], ontology)
    supplemental = next(item for item in results if item["hpo_id"] == "HP:1234567")

    assert supplemental["method"] == "ontology_term_search"
    assert supplemental["matched_term"] == "Blepharoptosis"
    assert supplemental["matched_language"] == "en"
    assert supplemental["term_source"] == "HPO ontology snapshot"
    assert supplemental["label_pt_status"] == "unavailable"


def test_all_synthetic_gold_mentions_fit_review_export():
    cases = json.loads(
        (ROOT / "data/demo/synthetic_review_cases.json").read_text(encoding="utf-8")
    )
    ontology = load_ontology_index(ROOT / "data/processed/hpo_ontology.json.gz")
    reviews = [
        {
            "text": mention["text"],
            "start": mention["start"],
            "end": mention["end"],
            "source": "manual",
            "decision": "include",
            "assertion": "present",
            "suggested_assertion": "present",
            "selected_hpo_id": mention["hpo_id"],
            "rankings": {},
            "human_modified": True,
        }
        for case in cases
        for mention in case["mentions"]
    ]

    exported = build_workbench_export(
        text="Conjunto sintético de validação funcional.",
        data_version=ontology.data_version,
        reviews=reviews,
        ontology=ontology,
        generated_at="2026-08-27T00:00:00+00:00",
    )

    assert len(exported["annotations"]) == 30
    assert exported["summary"] == {
        "automatic": 0,
        "manual": 30,
        "included": 30,
        "discarded": 0,
        "human_modified": 30,
        "included_with_pending_characterization": 30,
        "pending_characterization_fields": 180,
    }
import json
from pathlib import Path
