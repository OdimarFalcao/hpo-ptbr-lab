from hpo_ptbr.normalize import normalize_text, tokenize


def test_normalize_accents_case_and_punctuation():
    assert normalize_text("  Pressão-ARTERIAL, elevada! ") == "pressao arterial elevada"


def test_tokenize_empty_and_regular_text():
    assert tokenize("---") == []
    assert tokenize("Dor lombar") == ["dor", "lombar"]
