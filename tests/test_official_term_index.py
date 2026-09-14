from hpo_ptbr.official_term_index import (
    OfficialBm25Ranker,
    OfficialExactRanker,
    OfficialFuzzyRanker,
    build_official_term_index,
)
from hpo_ptbr.ontology import HpoConcept, HpoSynonym, OntologyIndex


def ontology() -> OntologyIndex:
    root = HpoConcept(
        "HP:0000118",
        "Phenotypic abnormality",
        "Anormalidade fenotípica",
        "",
        "",
        (),
        (),
        (),
        ("HP:0000001", "HP:0000002"),
    )
    translated = HpoConcept(
        "HP:0000001",
        "Drooping eyelid",
        "Ptose",
        "",
        "",
        (),
        (HpoSynonym("Falling upper eyelid", "exact", "layperson"),),
        (root.hpo_id,),
        (),
    )
    untranslated = HpoConcept(
        "HP:0000002",
        "Loss of speech",
        "",
        "",
        "",
        (),
        (HpoSynonym("Speech regression", "exact", "clinical"),),
        (root.hpo_id,),
        (),
    )
    modifier = HpoConcept(
        "HP:0003674",
        "Onset",
        "Começo",
        "",
        "",
        (),
        (),
        (),
        (),
    )
    return OntologyIndex(
        {concept.hpo_id: concept for concept in (root, translated, untranslated, modifier)},
        "test-version",
    )


def metadata() -> dict[str, object]:
    return {
        "data_version": "test-version",
        "hpo_release": "2026-06-23",
        "translation_commit": "translation-sha",
        "sources": {
            "hpo": {"url": "https://example.test/hp.json", "sha256": "hpo-sha"},
            "hpo_pt": {"url": "https://example.test/hp-pt.tsv", "sha256": "pt-sha"},
        },
    }


def test_index_includes_untranslated_phenotype_with_explicit_provenance():
    index = build_official_term_index(ontology(), metadata())

    term = next(
        term
        for term in index.terms
        if term.hpo_id == "HP:0000002" and term.field == "official_label_en"
    )

    assert term.text == "Loss of speech"
    assert term.language == "en"
    assert term.source == "hpo"
    assert term.source_version == "2026-06-23"
    assert not any(term.hpo_id == "HP:0003674" for term in index.terms)
    assert not any(term.hpo_id == "HP:0000118" for term in index.terms)


def test_exact_candidate_marks_missing_portuguese_label_and_requires_review():
    local_ontology = ontology()
    ranker = OfficialExactRanker(
        build_official_term_index(local_ontology, metadata()),
        local_ontology,
    )

    result = ranker.map("Speech regression")

    assert result.candidates[0].hpo_id == "HP:0000002"
    assert result.candidates[0].label_pt == ""
    assert result.candidates[0].label_pt_status == "unavailable"
    assert result.candidates[0].matched_term_language == "en"
    assert result.candidates[0].human_review_required is True


def test_rankers_collapse_multiple_terms_to_one_candidate_per_concept():
    local_ontology = ontology()
    index = build_official_term_index(local_ontology, metadata())

    fuzzy = OfficialFuzzyRanker(index, local_ontology).map("falling upper eyelid")
    bm25 = OfficialBm25Ranker(index, local_ontology).map("speech regression")

    assert fuzzy.candidates[0].hpo_id == "HP:0000001"
    assert len({candidate.hpo_id for candidate in fuzzy.candidates}) == len(fuzzy.candidates)
    assert bm25.candidates[0].hpo_id == "HP:0000002"
