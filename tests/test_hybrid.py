from hpo_ptbr.data import HpoRecord
from hpo_ptbr.hybrid import HybridMapper
from hpo_ptbr.rankers import BaseMapper


class StaticMapper(BaseMapper):
    method = "static"

    def __init__(self, records, rankings):
        super().__init__(records, "test")
        self.rankings = rankings

    def _score(self, query):
        records_by_id = {record.hpo_id: record for record in self.records}
        return [
            (records_by_id[hpo_id], score)
            for hpo_id, score in self.rankings.get(query, [])
        ]


def test_hybrid_short_circuits_exact_match():
    records = [
        HpoRecord("HP:0000001", "One", "Microcefalia"),
        HpoRecord("HP:0000002", "Two", "Outro termo"),
    ]
    source = StaticMapper(records, {"Microcefalia": [("HP:0000002", 1.0)]})
    result = HybridMapper(records, "test", (source,)).map("MICROCEFALIA")
    assert [candidate.hpo_id for candidate in result.candidates] == ["HP:0000001"]


def test_hybrid_rrf_unifies_duplicates_and_is_repeatable():
    records = [
        HpoRecord("HP:0000001", "One", "Termo um"),
        HpoRecord("HP:0000002", "Two", "Termo dois"),
        HpoRecord("HP:0000003", "Three", "Termo três"),
    ]
    first_source = StaticMapper(
        records,
        {"consulta": [("HP:0000001", 0.9), ("HP:0000002", 0.8)]},
    )
    second_source = StaticMapper(
        records,
        {"consulta": [("HP:0000002", 0.7), ("HP:0000003", 0.6)]},
    )
    mapper = HybridMapper(records, "test", (first_source, second_source))
    first = mapper.map("consulta").to_dict()
    second = mapper.map("consulta").to_dict()
    assert first["candidates"] == second["candidates"]
    assert [candidate["hpo_id"] for candidate in first["candidates"]] == [
        "HP:0000002",
        "HP:0000001",
        "HP:0000003",
    ]


def test_hybrid_breaks_rrf_ties_by_hpo_id():
    records = [
        HpoRecord("HP:0000001", "One", "Termo um"),
        HpoRecord("HP:0000002", "Two", "Termo dois"),
    ]
    first_source = StaticMapper(records, {"consulta": [("HP:0000002", 1.0)]})
    second_source = StaticMapper(records, {"consulta": [("HP:0000001", 1.0)]})
    result = HybridMapper(records, "test", (first_source, second_source)).map("consulta")
    assert [candidate.hpo_id for candidate in result.candidates] == [
        "HP:0000001",
        "HP:0000002",
    ]
