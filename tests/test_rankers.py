import pytest

from hpo_ptbr.data import HpoRecord
from hpo_ptbr.rankers import Bm25Mapper, ExactMapper, FuzzyMapper


@pytest.fixture
def records():
    return [
        HpoRecord("HP:0000252", "Microcephaly", "Microcefalia"),
        HpoRecord("HP:0000822", "Hypertension", "Hipertensão"),
        HpoRecord("HP:0003419", "Low back pain", "Dor lombar"),
    ]


def test_exact_normalizes_accents_and_case(records):
    result = ExactMapper(records, "test").map("HIPERTENSAO")
    assert result.candidates[0].hpo_id == "HP:0000822"


def test_fuzzy_recovers_typo(records):
    result = FuzzyMapper(records, "test").map("micro cefalia")
    assert result.candidates[0].hpo_id == "HP:0000252"


def test_bm25_is_deterministic_and_valid(records):
    mapper = Bm25Mapper(records, "test")
    first = mapper.map("dor lombar").to_dict()
    second = mapper.map("dor lombar").to_dict()
    assert first["candidates"] == second["candidates"]
    assert first["candidates"][0]["hpo_id"] == "HP:0003419"


def test_invalid_queries_are_rejected(records):
    mapper = ExactMapper(records, "test")
    with pytest.raises(ValueError):
        mapper.map(" ")
    with pytest.raises(ValueError):
        mapper.map("x" * 201)
