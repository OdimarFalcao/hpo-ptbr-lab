from __future__ import annotations

import json
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, model_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .annotation import build_annotation_span, build_workbench_export, rank_candidates, search_candidates
from .assertion import PortugueseContextCueClassifier
from .data import load_metadata, load_snapshot
from .evidence import EvidenceExtractor
from .ontology import load_ontology_index
from .rankers import Bm25Mapper, ExactMapper, FuzzyMapper

ROOT = Path(__file__).resolve().parents[2]
Assertion = Literal["present", "absent", "uncertain", "family_history"]
ORIGINS = [f"http://{host}:{port}" for host in ("127.0.0.1", "localhost") for port in (8000, 5173)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class TextRequest(Contract):
    text: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=10)

    @model_validator(mode="after")
    def nonblank(self):
        if not self.text.strip():
            raise ValueError("Texto vazio.")
        return self


class SpanRequest(TextRequest):
    start: int = Field(ge=0)
    end: int = Field(gt=0)

    @model_validator(mode="after")
    def valid_offsets(self):
        if self.end <= self.start or self.end > len(self.text):
            raise ValueError("Offsets inválidos.")
        return self


class SearchRequest(Contract):
    query: str = Field(min_length=1, max_length=100)
    top_k: int = Field(default=5, ge=1, le=10)


class Candidate(Contract):
    hpo_id: str
    label_pt: str
    label_en: str
    score: float | None = None
    rank: int = Field(ge=1, le=10)
    method: Literal["exact", "fuzzy", "bm25", "semantic", "manual_search", "hpo_id_lookup", "ontology_term_search"]
    reason: str
    matched_term: str | None = None
    matched_language: Literal["pt", "en"] | None = None
    matched_field: str | None = None
    matched_audience: str | None = None
    term_source: str | None = None
    label_pt_status: Literal["official", "unavailable"]


class Span(Contract):
    text: str
    start: int
    end: int
    source: Literal["lexical", "manual"]
    detector_score: float | None = None
    suggested_assertion: Assertion
    rankings: dict[str, list[Candidate]]


class Analysis(Contract):
    data_version: str
    spans: list[Span]
    latency_ms: float


class Characterization(Contract):
    onset_age: str | None = Field(default=None, max_length=100)
    severity: Literal["mild", "moderate", "severe", "profound", "other", "unknown"] | None = None
    evolution: Literal["stable", "progressive", "improving", "fluctuating", "resolved", "other", "unknown"] | None = None
    frequency: Literal["episodic", "intermittent", "continuous", "other", "unknown"] | None = None
    laterality: Literal["left", "right", "bilateral", "midline", "not_applicable", "other", "unknown"] | None = None
    family_history: Literal["present", "absent", "unknown"] | None = None


class Review(Span):
    selected_hpo_id: str | None
    assertion: Assertion
    decision: Literal["include", "discard"]
    human_modified: bool
    characterization: Characterization = Field(default_factory=Characterization)


class ExportRequest(Contract):
    text: str = Field(min_length=1, max_length=1000)
    data_version: str
    reviews: list[Review] = Field(max_length=100)


@lru_cache(maxsize=1)
def resources():
    metadata = load_metadata(ROOT / "data/processed/metadata.json")
    ontology = load_ontology_index(ROOT / "data/processed/hpo_ontology.json.gz")
    version = str(metadata["data_version"])
    if ontology.data_version != version:
        raise ValueError("Snapshot e índice incompatíveis.")
    records = [
        record
        for record in load_snapshot(ROOT / "data/processed/hpo_ptbr.csv")
        if ontology.is_phenotypic_abnormality(record.hpo_id)
    ]
    if not records:
        raise ValueError("Snapshot sem anormalidades fenotípicas traduzidas.")
    mappers = {"Exact": ExactMapper(records, version), "Fuzzy": FuzzyMapper(records, version), "BM25": Bm25Mapper(records, version)}
    return metadata, ontology, mappers


@lru_cache(maxsize=1)
def semantic_mapper():
    from .sapbert import SapBertEncoder
    from .semantic import SemanticMapper

    _, _, mappers = resources()
    return SemanticMapper(mappers["Fuzzy"].records, mappers["Fuzzy"].data_version, SapBertEncoder(local_files_only=True))


app = FastAPI(title="HPO-PTBR local", version="1.0.0", docs_url=None, redoc_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


@app.middleware("http")
async def local_privacy_boundary(request: Request, call_next):
    if request.headers.get("origin") and request.headers["origin"] not in ORIGINS:
        return JSONResponse({"detail": "Origem não permitida."}, status_code=403)
    if request.url.path.startswith("/api/") and request.method == "POST":
        if request.headers.get("content-type", "").split(";")[0] != "application/json":
            return JSONResponse({"detail": "Envie JSON."}, status_code=415)
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 262144:
                return JSONResponse({"detail": "Requisição excede o limite."}, status_code=413)
        request._body = bytes(body)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request, error):
    return JSONResponse({"detail": "Dados inválidos: confira texto, limites, contexto e decisões de revisão."}, status_code=422)


@app.exception_handler(ValueError)
async def value_error(request, error):
    return JSONResponse({"detail": "Anotação inválida para o snapshot ou texto informado."}, status_code=422)


@app.get("/api/health")
def health():
    metadata, ontology, _ = resources()
    return {
        "status": "ok",
        "data_version": ontology.data_version,
        "active_terms": len(ontology.concepts),
        "translated_labels_pt": metadata["translated_labels_pt"],
        "automatic_phenotype_terms": len(ontology.phenotypic_abnormality_ids),
        "ranked_phenotype_terms_pt": len(resources()[2]["Fuzzy"].records),
        "automatic_scope_root": ontology.root_hpo_id,
    }


@app.get("/api/examples")
def examples():
    cases = json.loads((ROOT / "data/demo/synthetic_review_cases.json").read_text(encoding="utf-8"))
    return [{key: case[key] for key in ("id", "title", "domain", "text")} for case in cases]


@app.post("/api/analyze", response_model=Analysis, response_model_exclude_none=True)
def analyze(payload: TextRequest):
    _, ontology, mappers = resources()
    result = EvidenceExtractor(mappers["Fuzzy"]).map_text(payload.text, top_k=payload.top_k)
    leading = len(payload.text) - len(payload.text.lstrip())
    spans = [build_annotation_span(payload.text, span.start + leading, span.end + leading, source="lexical", mappers=mappers, classifier=PortugueseContextCueClassifier(), detector_score=span.detector_score, top_k=payload.top_k) for span in result.spans]
    return {"data_version": ontology.data_version, "spans": spans, "latency_ms": result.latency_ms}


@app.post("/api/mentions", response_model=Span, response_model_exclude_none=True)
def manual_mention(payload: SpanRequest):
    _, _, mappers = resources()
    return build_annotation_span(payload.text, payload.start, payload.end, source="manual", mappers=mappers, classifier=PortugueseContextCueClassifier(), top_k=payload.top_k)


@app.post("/api/search", response_model=list[Candidate], response_model_exclude_none=True)
def search(payload: SearchRequest):
    _, ontology, mappers = resources()
    return search_candidates(payload.query, mappers["Fuzzy"], ontology, top_k=payload.top_k)


@app.post("/api/semantic", response_model=list[Candidate], response_model_exclude_none=True)
def semantic(payload: SpanRequest):
    try:
        return rank_candidates(payload.text[payload.start:payload.end], {"SapBERT": semantic_mapper()}, top_k=payload.top_k)["SapBERT"]
    except Exception:
        raise HTTPException(503, "SapBERT indisponível no cache local. Continue com os métodos lexicais.") from None


@app.get("/api/concepts/{hpo_id}")
def concept_details(hpo_id: str):
    _, ontology, _ = resources()
    concept = ontology.get(hpo_id)
    if concept is None:
        raise HTTPException(404, "Conceito inexistente no snapshot.")
    def related(ids):
        return [{"hpo_id": identifier, "label": ontology.require(identifier).label_pt or ontology.require(identifier).label_en} for identifier in ids]
    return asdict(concept) | {"parents": related(concept.parent_ids), "children": related(concept.child_ids), "path": related(ontology.path_to_root(hpo_id))}


@app.post("/api/export")
def export(payload: ExportRequest):
    metadata, ontology, _ = resources()
    if payload.data_version != ontology.data_version or not payload.text.strip():
        raise ValueError("Versão ou texto inválido.")
    previous_end = 0
    for review in sorted(payload.reviews, key=lambda item: (item.start, item.end)):
        if review.start < previous_end or review.end <= review.start or review.end > len(payload.text) or payload.text[review.start:review.end] != review.text:
            raise ValueError("Offsets inválidos ou sobrepostos.")
        previous_end = review.end
        ranked_ids = {
            candidate.hpo_id
            for candidates in review.rankings.values()
            for candidate in candidates
        }
        if review.selected_hpo_id:
            ontology.require_phenotypic_abnormality(review.selected_hpo_id)
        if review.decision == "include" and review.selected_hpo_id not in ranked_ids:
            raise ValueError("Conceito incluído sem método de recuperação registrado.")
        for candidates in review.rankings.values():
            for candidate in candidates:
                ontology.require_phenotypic_abnormality(candidate.hpo_id)
    terminology_provenance = {
        "data_version": payload.data_version,
        "hpo_release": metadata["hpo_release"],
        "hpo": metadata["sources"]["hpo"],
        "portuguese_translation": {
            "status": "official labels only",
            "commit": metadata["translation_commit"],
            **metadata["sources"]["hpo_pt"],
        },
    }
    return build_workbench_export(text=payload.text, data_version=payload.data_version, reviews=[review.model_dump() for review in payload.reviews], ontology=ontology, terminology_provenance=terminology_provenance)


DIST = ROOT / "web/dist"
if DIST.is_dir():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="workbench")
