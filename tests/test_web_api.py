import copy
import json

import pytest
from fastapi.testclient import TestClient

from hpo_ptbr.annotation import build_annotation_span, rank_candidates
from hpo_ptbr.assertion import PortugueseContextCueClassifier
from hpo_ptbr.web_api import ROOT, app, resources


@pytest.fixture(scope="module")
def client():
    with TestClient(app, base_url="http://127.0.0.1") as instance:
        yield instance


def reviewed_payload(client, text="ptose e nistagmo"):
    result = client.post("/api/analyze", json={"text": text}).json()
    reviews = []
    for span in result["spans"]:
        reviews.append(span | {
            "selected_hpo_id": span["rankings"]["Fuzzy"][0]["hpo_id"],
            "assertion": span["suggested_assertion"], "decision": "include", "human_modified": False,
        })
    return {"text": text, "data_version": result["data_version"], "reviews": reviews}


def test_health_examples_and_no_gold_labels(client):
    assert client.get("/api/health").json()["active_terms"] == 19836
    examples = client.get("/api/examples").json()
    assert len(examples) == 10
    assert set(examples[0]) == {"id", "title", "domain", "text"}


@pytest.mark.parametrize("text", ["ptose", "  ptose e nistagmo  ", "\n🧪 ptose\n e nistagmo.", "á 🧬 ptose"])
def test_offsets_and_rankings_match_core(client, text):
    result = client.post("/api/analyze", json={"text": text})
    assert result.status_code == 200, result.text
    _, _, mappers = resources()
    assert result.json()["spans"]
    for span in result.json()["spans"]:
        assert text[span["start"]:span["end"]] == span["text"]
        expected = build_annotation_span(text, span["start"], span["end"], source="lexical", mappers=mappers, classifier=PortugueseContextCueClassifier(), detector_score=span["detector_score"])
        assert span == expected
        assert span["rankings"] == rank_candidates(span["text"], mappers)


@pytest.mark.parametrize("text", ["", "   ", "a" * 1001])
def test_invalid_text_is_not_echoed(client, text):
    response = client.post("/api/analyze", json={"text": text})
    assert response.status_code == 422
    assert "input" not in response.json()


def test_negative_text_and_manual_repeated_mention(client):
    assert client.post("/api/analyze", json={"text": "Texto artificial sem achados."}).json()["spans"] == []
    text = "🧪 ptose; ptose"
    result = client.post("/api/mentions", json={"text": text, "start": 9, "end": 14})
    assert result.status_code == 200, result.text
    assert result.json()["text"] == "ptose"
    assert result.json()["source"] == "manual"
    assert client.post("/api/mentions", json={"text": text, "start": 9, "end": 90}).status_code == 422


def test_concept_hierarchy_and_search(client):
    _, ontology, _ = resources()
    response = client.get("/api/concepts/HP:0000508")
    assert response.status_code == 200
    concept = response.json()
    assert concept["path"][-1]["hpo_id"] == "HP:0000118"
    for related in concept["parents"] + concept["children"] + concept["path"]:
        assert ontology.get(related["hpo_id"])
    assert client.get("/api/concepts/HP:9999999").status_code == 404
    assert client.post("/api/search", json={"query": "HP:0000508"}).json()[0]["hpo_id"] == "HP:0000508"
    assert client.post("/api/search", json={"query": "HP:9999999"}).json() == []


def test_semantic_failure_preserves_lexical(client, monkeypatch):
    def unavailable():
        raise ImportError("Test-only unavailable model")
    monkeypatch.setattr("hpo_ptbr.web_api.semantic_mapper", unavailable)
    assert client.post("/api/semantic", json={"text": "ptose", "start": 0, "end": 5}).status_code == 503
    assert client.post("/api/analyze", json={"text": "ptose"}).status_code == 200


@pytest.mark.parametrize("assertion", ["present", "absent", "uncertain", "family_history"])
def test_context_and_deterministic_export(client, assertion):
    payload = reviewed_payload(client)
    payload["reviews"][0]["assertion"] = assertion
    payload["reviews"][0]["human_modified"] = True
    payload["reviews"][0]["characterization"] = {
        "onset_age": "ao nascimento", "severity": "mild", "evolution": "stable",
        "frequency": "continuous", "laterality": "not_applicable", "family_history": "unknown",
    }
    payload["reviews"][1]["decision"] = "discard"
    first = client.post("/api/export", json=payload)
    second = client.post("/api/export", json=payload)
    assert first.status_code == 200, first.text
    first_data, second_data = first.json(), second.json()
    first_data.pop("generated_at"); second_data.pop("generated_at")
    assert first_data == second_data
    assert first_data["schema_version"] == "hpo-ptbr-review-v1"
    assert first_data["annotations"][0]["assertion"] == assertion
    assert first_data["annotations"][0]["pending_characterization"] == []
    assert first_data["annotations"][0]["characterization"]["onset_age"] == "ao nascimento"
    assert first_data["annotations"][0]["human_decision"]["reviewed"] is True
    assert first_data["terminology_provenance"]["portuguese_translation"]["status"] == "official labels only"
    assert first_data["summary"]["discarded"] == 1
    assert first_data["annotations"][1]["selected_hpo"] is None
    assert "probabilidade" not in json.dumps(first_data)


@pytest.mark.parametrize("field,value", [("decision", "pending"), ("assertion", "diagnosis"), ("selected_hpo_id", "HP:9999999"), ("start", -1), ("text", "trecho incorreto"), ("end", 999)])
def test_invalid_export_rejected(client, field, value):
    payload = reviewed_payload(client)
    payload["reviews"][0][field] = value
    assert client.post("/api/export", json=payload).status_code == 422


def test_export_rejects_overlaps_snapshot_and_missing_selection(client):
    original = reviewed_payload(client)
    payload = copy.deepcopy(original)
    payload["reviews"].append(payload["reviews"][0])
    assert client.post("/api/export", json=payload).status_code == 422
    payload = copy.deepcopy(original)
    payload["data_version"] = "wrong"
    assert client.post("/api/export", json=payload).status_code == 422
    payload = copy.deepcopy(original)
    payload["reviews"][0]["selected_hpo_id"] = None
    assert client.post("/api/export", json=payload).status_code == 422


def test_privacy_origin_body_limits_and_cache(client):
    assert client.post("/api/analyze", json={"text": "ptose"}, headers={"Origin": "https://other.example"}).status_code == 403
    assert client.post("/api/analyze", content="text=ptose", headers={"Content-Type": "text/plain"}).status_code == 415
    assert client.post("/api/analyze", content='"' + 'a' * 262145 + '"', headers={"Content-Type": "application/json"}).status_code == 413
    assert client.get("/api/health").headers["cache-control"] == "no-store"
    assert client.get("/api/health", headers={"Host": "other.example"}).status_code == 400


def test_all_30_synthetic_mentions_can_be_reviewed_and_exported(client):
    cases = json.loads((ROOT / "data/demo/synthetic_review_cases.json").read_text(encoding="utf-8"))
    version = client.get("/api/health").json()["data_version"]
    count = 0
    for case in cases:
        reviews = []
        for mention in case["mentions"]:
            response = client.post("/api/mentions", json={"text": case["text"], "start": mention["start"], "end": mention["end"]})
            assert response.status_code == 200, response.text
            span = response.json()
            candidate = client.post("/api/search", json={"query": mention["hpo_id"]}).json()
            span["rankings"]["Busca manual"] = candidate
            reviews.append(span | {"selected_hpo_id": mention["hpo_id"], "assertion": "present", "decision": "include", "human_modified": True})
            count += 1
        exported = client.post("/api/export", json={"text": case["text"], "data_version": version, "reviews": reviews})
        assert exported.status_code == 200, exported.text
        assert {item["selected_hpo"]["hpo_id"] for item in exported.json()["annotations"]} == set(case["expected_hpo_ids"])
    assert count == 30
