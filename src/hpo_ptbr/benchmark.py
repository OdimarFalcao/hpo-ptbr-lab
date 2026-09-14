from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Collection, Mapping

from .normalize import normalize_text

ALLOWED_SPLITS = {"development", "holdout"}
ALLOWED_CASE_TYPES = {"phenotype", "negative_control"}
ALLOWED_ASSERTIONS = {"present", "absent", "uncertain", "family_history"}
ALLOWED_SURFACE_FORMS = {
    "official_label",
    "orthographic_variation",
    "clinical_paraphrase",
}


@dataclass(frozen=True)
class BenchmarkSummary:
    case_count: int
    mention_count: int
    negative_control_count: int
    cases_by_split: Counter[str]
    mentions_by_split: Counter[str]
    domains: frozenset[str]
    assertion_counts: Counter[str]
    surface_form_counts: Counter[str]
    domain_mention_counts: Counter[str]
    hpo_ids: frozenset[str]


def load_benchmark(path: str | Path) -> dict[str, object]:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("O benchmark deve ser um objeto JSON.")
    return document


def validate_benchmark(
    document: dict[str, object],
    valid_hpo_ids: Collection[str],
    excluded_hpo_ids: Collection[str] = (),
    official_labels: Mapping[str, str] | None = None,
) -> BenchmarkSummary:
    if not isinstance(document.get("benchmark_version"), str):
        raise ValueError("benchmark_version é obrigatório.")
    if not isinstance(document.get("snapshot"), str):
        raise ValueError("snapshot é obrigatório.")
    cases = document.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("O benchmark deve conter uma lista não vazia de casos.")

    valid_ids = set(valid_hpo_ids)
    excluded_ids = set(excluded_hpo_ids)
    case_ids: set[str] = set()
    benchmark_hpo_ids: set[str] = set()
    cases_by_split: Counter[str] = Counter()
    mentions_by_split: Counter[str] = Counter()
    domains: set[str] = set()
    assertion_counts: Counter[str] = Counter()
    surface_form_counts: Counter[str] = Counter()
    domain_mention_counts: Counter[str] = Counter()
    negative_control_count = 0

    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("Cada caso deve ser um objeto JSON.")
        case_id = case.get("case_id")
        split = case.get("split")
        domain = case.get("domain")
        case_type = case.get("case_type")
        text = case.get("text")
        mentions = case.get("mentions")

        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("Todo caso precisa de case_id.")
        if case_id in case_ids:
            raise ValueError(f"case_id duplicado: {case_id}")
        case_ids.add(case_id)
        if split not in ALLOWED_SPLITS:
            raise ValueError(f"Split inválido em {case_id}: {split}")
        if not isinstance(domain, str) or not domain.strip():
            raise ValueError(f"Domínio ausente em {case_id}.")
        if case_type not in ALLOWED_CASE_TYPES:
            raise ValueError(f"Tipo de caso inválido em {case_id}: {case_type}")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"Texto sintético ausente em {case_id}.")
        if not isinstance(mentions, list):
            raise ValueError(f"Lista de menções ausente em {case_id}.")
        if case_type == "negative_control" and mentions:
            raise ValueError(f"Controle negativo contém menções: {case_id}")
        if case_type == "phenotype" and not mentions:
            raise ValueError(f"Caso fenotípico sem menções: {case_id}")

        cases_by_split[split] += 1
        if case_type == "negative_control":
            negative_control_count += 1
        else:
            domains.add(domain)

        occupied_spans: list[tuple[int, int]] = []
        for mention in mentions:
            if not isinstance(mention, dict):
                raise ValueError(f"Menção inválida em {case_id}.")
            mention_text = mention.get("text")
            start = mention.get("start")
            end = mention.get("end")
            hpo_id = mention.get("hpo_id")
            assertion = mention.get("assertion")
            surface_form = mention.get("surface_form")

            if not isinstance(mention_text, str) or not mention_text:
                raise ValueError(f"Texto de menção ausente em {case_id}.")
            if not isinstance(start, int) or not isinstance(end, int):
                raise ValueError(f"Offsets não inteiros em {case_id}: {mention_text}")
            if start < 0 or end <= start or end > len(text):
                raise ValueError(f"Offsets inválidos em {case_id}: {mention_text}")
            if text[start:end] != mention_text:
                raise ValueError(f"Texto e offsets divergem em {case_id}: {mention_text}")
            if not isinstance(hpo_id, str) or hpo_id not in valid_ids:
                raise ValueError(f"HPO ID inválido em {case_id}: {hpo_id}")
            if hpo_id in excluded_ids:
                raise ValueError(f"HPO ID já usado em avaliação anterior: {hpo_id}")
            if hpo_id in benchmark_hpo_ids:
                raise ValueError(f"HPO ID repetido no benchmark: {hpo_id}")
            if assertion not in ALLOWED_ASSERTIONS:
                raise ValueError(f"Contexto inválido em {case_id}: {assertion}")
            if surface_form not in ALLOWED_SURFACE_FORMS:
                raise ValueError(f"Forma superficial inválida em {case_id}: {surface_form}")
            if official_labels is not None:
                official_label = official_labels[hpo_id]
                if mention.get("label_pt") != official_label:
                    raise ValueError(f"Rótulo oficial divergente em {case_id}: {hpo_id}")
                if surface_form == "official_label" and mention_text != official_label:
                    raise ValueError(f"Superfície oficial alterada em {case_id}: {hpo_id}")
                if (
                    surface_form == "clinical_paraphrase"
                    and normalize_text(official_label) in normalize_text(mention_text)
                ):
                    raise ValueError(f"Paráfrase repete o rótulo oficial em {case_id}: {hpo_id}")
            if any(start < occupied_end and end > occupied_start for occupied_start, occupied_end in occupied_spans):
                raise ValueError(f"Spans sobrepostos em {case_id}: {mention_text}")

            occupied_spans.append((start, end))
            benchmark_hpo_ids.add(hpo_id)
            mentions_by_split[split] += 1
            assertion_counts[assertion] += 1
            surface_form_counts[surface_form] += 1
            domain_mention_counts[domain] += 1

    return BenchmarkSummary(
        case_count=len(cases),
        mention_count=len(benchmark_hpo_ids),
        negative_control_count=negative_control_count,
        cases_by_split=cases_by_split,
        mentions_by_split=mentions_by_split,
        domains=frozenset(domains),
        assertion_counts=assertion_counts,
        surface_form_counts=surface_form_counts,
        domain_mention_counts=domain_mention_counts,
        hpo_ids=frozenset(benchmark_hpo_ids),
    )


def validate_benchmark_targets(
    summary: BenchmarkSummary,
    protocol: dict[str, object],
    target_name: str | None = None,
) -> None:
    target = protocol
    if target_name is not None:
        targets = protocol.get("targets")
        if not isinstance(targets, dict) or not isinstance(targets.get(target_name), dict):
            raise ValueError(f"Target ausente no protocolo: {target_name}")
        target = targets[target_name]
    scope = target.get("scope")
    annotation = target.get("annotation")
    if not isinstance(scope, dict) or not isinstance(annotation, dict):
        raise ValueError("Protocolo sem scope ou annotation.")

    expected_scalars = {
        "case_count": summary.case_count,
        "mention_count": summary.mention_count,
        "negative_control_count": summary.negative_control_count,
    }
    for field, observed in expected_scalars.items():
        expected = scope.get(field)
        if observed != expected:
            raise ValueError(f"{field}: esperado {expected}, observado {observed}.")

    expected_splits = scope.get("splits")
    if not isinstance(expected_splits, dict) or dict(summary.cases_by_split) != expected_splits:
        raise ValueError(
            f"Distribuição de splits inválida: {dict(summary.cases_by_split)}"
        )
    expected_mentions_by_split = scope.get("mentions_by_split")
    if (
        not isinstance(expected_mentions_by_split, dict)
        or dict(summary.mentions_by_split) != expected_mentions_by_split
    ):
        raise ValueError(
            "Distribuição de menções por split inválida: "
            f"{dict(summary.mentions_by_split)}"
        )
    minimum_domains = scope.get("minimum_domains")
    if not isinstance(minimum_domains, int) or len(summary.domains) < minimum_domains:
        raise ValueError(
            f"Domínios insuficientes: mínimo {minimum_domains}, observado {len(summary.domains)}."
        )

    expected_assertions = annotation.get("assertion_counts")
    if not isinstance(expected_assertions, dict) or dict(summary.assertion_counts) != expected_assertions:
        raise ValueError(
            f"Distribuição de contextos inválida: {dict(summary.assertion_counts)}"
        )
    expected_surfaces = annotation.get("surface_form_counts")
    if not isinstance(expected_surfaces, dict) or dict(summary.surface_form_counts) != expected_surfaces:
        raise ValueError(
            f"Distribuição de formas inválida: {dict(summary.surface_form_counts)}"
        )
    expected_domain_mentions = annotation.get("domain_mention_counts")
    if expected_domain_mentions is not None and (
        not isinstance(expected_domain_mentions, dict)
        or dict(summary.domain_mention_counts) != expected_domain_mentions
    ):
        raise ValueError(
            "Distribuição de menções por domínio inválida: "
            f"{dict(summary.domain_mention_counts)}"
        )
