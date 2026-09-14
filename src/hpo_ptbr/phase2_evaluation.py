from __future__ import annotations

import json
import re
import statistics
from collections import Counter, deque
from pathlib import Path

from .annotation import CHARACTERIZATION_FIELDS
from .assertion import PortugueseContextCueClassifier
from .benchmark_evaluation import evaluate_benchmark_method
from .evidence import EvidenceExtractor
from .normalize import normalize_text
from .ontology import OntologyIndex

CONTEXTS = {"present", "absent", "uncertain", "family_history"}
SURFACE_SOURCES = {"synthetic_paraphrase_pending_clinical_review"}
ERROR_CATEGORIES = (
    "mention_not_detected",
    "wrong_span",
    "concept_too_generic",
    "concept_too_specific",
    "wrong_concept",
    "context_error",
    "paraphrase_failure",
    "portuguese_coverage_failure",
)


def _field_names() -> tuple[str, ...]:
    return tuple(field for field, _ in CHARACTERIZATION_FIELDS)


def load_phase2_dataset(
    path: str | Path,
    ontology: OntologyIndex,
    *,
    expected_split: str | None = None,
) -> dict[str, object]:
    dataset_path = Path(path)
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "phase2-synthetic-cases-v1":
        raise ValueError("Schema de casos da Fase 2 inválido.")
    split = str(payload.get("split", ""))
    if split not in {"development", "validation", "holdout"}:
        raise ValueError("Split da Fase 2 inválido.")
    if expected_split is not None and split != expected_split:
        raise ValueError(f"Executor de {expected_split} não aceita split {split}.")
    source = payload.get("source", {})
    if not isinstance(source, dict) or source.get("kind") != "synthetic":
        raise ValueError("A Fase 2 aceita somente dados sintéticos.")
    if source.get("contains_real_patient_data") is not False:
        raise ValueError("O dataset deve declarar ausência de dados reais.")

    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Dataset da Fase 2 sem casos.")
    case_ids: set[str] = set()
    template_families: set[str] = set()
    for case in cases:
        _validate_case(case, ontology, case_ids, template_families)
    return payload


def _validate_case(
    case: object,
    ontology: OntologyIndex,
    case_ids: set[str],
    template_families: set[str],
) -> None:
    if not isinstance(case, dict):
        raise ValueError("Caso da Fase 2 inválido.")
    case_id = str(case.get("case_id", ""))
    if not case_id or case_id in case_ids:
        raise ValueError(f"case_id ausente ou duplicado: {case_id!r}")
    case_ids.add(case_id)
    text = str(case.get("text", ""))
    if not text.strip():
        raise ValueError(f"Texto vazio em {case_id}.")
    template_family = str(case.get("template_family", ""))
    if not template_family or template_family in template_families:
        raise ValueError(f"Família de template ausente ou repetida em {case_id}.")
    template_families.add(template_family)
    annotations = case.get("annotations")
    if not isinstance(annotations, list):
        raise ValueError(f"Anotações inválidas em {case_id}.")
    for annotation in annotations:
        _validate_annotation(case_id, text, annotation, ontology)


def _validate_annotation(
    case_id: str,
    text: str,
    annotation: object,
    ontology: OntologyIndex,
) -> None:
    if not isinstance(annotation, dict):
        raise ValueError(f"Anotação inválida em {case_id}.")
    start = int(annotation.get("start", -1))
    end = int(annotation.get("end", -1))
    mention = str(annotation.get("mention_text", ""))
    if start < 0 or end <= start or text[start:end] != mention:
        raise ValueError(f"Offsets não reproduzem a menção em {case_id}.")
    concept = ontology.require(str(annotation.get("hpo_id", "")))
    snapshot_label = annotation.get("label_pt_snapshot")
    expected_label = concept.label_pt or None
    if snapshot_label != expected_label:
        raise ValueError(f"Rótulo português diverge do snapshot em {case_id}.")
    if concept.label_pt:
        normalized_label = normalize_text(concept.label_pt)
        normalized_mention = normalize_text(mention)
        if normalized_label == normalized_mention or normalized_label in normalized_mention:
            raise ValueError(f"Rótulo HPO literal usado como pista principal em {case_id}.")
    if annotation.get("context") not in CONTEXTS:
        raise ValueError(f"Contexto inválido em {case_id}.")
    if annotation.get("surface_source") not in SURFACE_SOURCES:
        raise ValueError(f"Origem superficial não rastreável em {case_id}.")
    if not str(annotation.get("evidence_limit", "")).strip():
        raise ValueError(f"Limite da evidência ausente em {case_id}.")
    specificity = annotation.get("specificity")
    if not isinstance(specificity, dict) or not specificity.get("grade") or not specificity.get("note"):
        raise ValueError(f"Especificidade não documentada em {case_id}.")
    characterization = annotation.get("characterization")
    if not isinstance(characterization, dict) or set(characterization) != set(_field_names()):
        raise ValueError(f"Caracterização incompleta em {case_id}.")
    absent = set(annotation.get("information_absent", []))
    expected_absent = {field for field in _field_names() if characterization[field] is None}
    if absent != expected_absent:
        raise ValueError(f"Informações ausentes inconsistentes em {case_id}.")


def morphological_fingerprint(text: str) -> str:
    """Heurística conservadora para auditoria; não é um lematizador clínico."""
    suffixes = ("mente", "ções", "ção", "ando", "endo", "indo", "ados", "idas", "oso", "osa", "os", "as", "s")
    tokens = re.findall(r"\b[a-z0-9]+\b", normalize_text(text))
    stems = []
    for token in tokens:
        stem = token
        for suffix in suffixes:
            if len(stem) - len(suffix) >= 4 and stem.endswith(suffix):
                stem = stem[: -len(suffix)]
                break
        stems.append(stem)
    return " ".join(stems)


def _related_within(ontology: OntologyIndex, first: str, second: str, distance: int) -> bool:
    if first == second:
        return True
    queue: deque[tuple[str, int]] = deque([(first, 0)])
    visited = {first}
    while queue:
        current_id, current_distance = queue.popleft()
        if current_distance >= distance:
            continue
        concept = ontology.require(current_id)
        for related in (*concept.parent_ids, *concept.child_ids):
            if related == second:
                return True
            if related not in visited:
                visited.add(related)
                queue.append((related, current_distance + 1))
    return False


def _official_terms(ontology: OntologyIndex, hpo_id: str) -> set[str]:
    concept = ontology.require(hpo_id)
    raw_terms = [concept.label_pt, concept.label_en]
    raw_terms.extend(synonym.text for synonym in concept.synonyms)
    return {normalize_text(term) for term in raw_terms if term.strip()}


def audit_split_leakage(
    datasets: list[dict[str, object]],
    ontology: OntologyIndex,
    *,
    related_distance: int = 2,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    entries = []
    for dataset in datasets:
        split = str(dataset["split"])
        for case in dataset["cases"]:
            for annotation in case["annotations"] or [None]:
                entries.append((split, case, annotation))
    for index, (split_a, case_a, annotation_a) in enumerate(entries):
        for split_b, case_b, annotation_b in entries[index + 1 :]:
            if split_a == split_b:
                continue
            comparisons = {
                "case_text": normalize_text(str(case_a["text"])) == normalize_text(str(case_b["text"])),
                "template_family": case_a["template_family"] == case_b["template_family"],
            }
            if annotation_a and annotation_b:
                comparisons |= {
                    "mention_text": normalize_text(annotation_a["mention_text"]) == normalize_text(annotation_b["mention_text"]),
                    "morphological_fingerprint": morphological_fingerprint(annotation_a["mention_text"]) == morphological_fingerprint(annotation_b["mention_text"]),
                    "official_term_overlap": bool(_official_terms(ontology, annotation_a["hpo_id"]) & _official_terms(ontology, annotation_b["hpo_id"])),
                    "related_concept": _related_within(ontology, annotation_a["hpo_id"], annotation_b["hpo_id"], related_distance),
                }
            for issue_type, found in comparisons.items():
                if found:
                    issues.append({"type": issue_type, "left": str(case_a["case_id"]), "right": str(case_b["case_id"])})
    return issues


def _is_ancestor(ontology: OntologyIndex, ancestor: str, descendant: str) -> bool:
    return ancestor in ontology.path_to_root(descendant)[1:]


def _overlap(start_a: int, end_a: int, start_b: int, end_b: int) -> int:
    return max(0, min(end_a, end_b) - max(start_a, start_b))


def evaluate_phase2(
    extractor: EvidenceExtractor,
    dataset: dict[str, object],
    ontology: OntologyIndex,
    *,
    relaxed_iou: float = 0.5,
    top_k: int = 5,
    review_observations: list[dict[str, object]] | None = None,
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    cases = dataset["cases"]
    legacy_cases = []
    annotations_by_key = {}
    for case in cases:
        mentions = []
        for annotation in case["annotations"]:
            key = (case["case_id"], annotation["start"], annotation["end"])
            annotations_by_key[key] = annotation
            mentions.append({
                "text": annotation["mention_text"],
                "start": annotation["start"],
                "end": annotation["end"],
                "hpo_id": annotation["hpo_id"],
                "surface_form": annotation["surface_category"],
                "assertion": annotation["context"],
            })
        legacy_cases.append({
            "case_id": case["case_id"],
            "domain": "natural_clinical_language",
            "case_type": "phenotype" if mentions else "negative_control",
            "text": case["text"],
            "mentions": mentions,
        })

    classifier = PortugueseContextCueClassifier()
    gold, predictions, base = evaluate_benchmark_method(
        extractor,
        legacy_cases,
        assertion_classifier=classifier,
        detected_span_top_k=top_k,
        gold_span_top_k=top_k,
        relaxed_iou_threshold=relaxed_iou,
    )
    predictions_by_case: dict[str, list[dict[str, object]]] = {}
    for prediction in predictions:
        predictions_by_case.setdefault(str(prediction["case_id"]), []).append(prediction)

    errors = []
    pending_true_positive = 0
    pending_predicted = 0
    pending_gold = 0
    characterization_omissions = 0
    correction_components = Counter()
    for row in gold:
        key = (row["case_id"], row["start"], row["end"])
        annotation = annotations_by_key[key]
        case_predictions = predictions_by_case.get(str(row["case_id"]), [])
        overlapping = [
            prediction
            for prediction in case_predictions
            if _overlap(int(row["start"]), int(row["end"]), int(prediction["start"]), int(prediction["end"]))
        ]
        categories = []
        if not overlapping:
            categories.append("mention_not_detected")
            correction_components["manual_inclusions"] += 1
        elif not row["exact_span_detected"]:
            categories.append("wrong_span")
            correction_components["span_adjustments"] += 1

        top_hpo_ids = row["gold_span_top_hpo_ids"]
        top_hpo_id = top_hpo_ids[0] if top_hpo_ids else None
        if row["gold_span_target_rank"] != 1:
            correction_components["concept_changes"] += 1
            if top_hpo_id and _is_ancestor(ontology, str(top_hpo_id), str(row["target_hpo_id"])):
                categories.append("concept_too_generic")
            elif top_hpo_id and _is_ancestor(ontology, str(row["target_hpo_id"]), str(top_hpo_id)):
                categories.append("concept_too_specific")
            else:
                categories.append("wrong_concept")
        if not row["assertion_correct"]:
            categories.append("context_error")
            correction_components["context_changes"] += 1
        if (not row["exact_span_detected"] or row["gold_span_target_rank"] != 1) and "paraphrase" in str(row["surface_form"]):
            categories.append("paraphrase_failure")
        if annotation["label_pt_snapshot"] is None and row["gold_span_target_rank"] != 1:
            categories.append("portuguese_coverage_failure")

        characterization = annotation["characterization"]
        gold_pending = {field for field in _field_names() if characterization[field] is None}
        predicted_pending = set(_field_names())
        pending_gold += len(gold_pending)
        pending_predicted += len(predicted_pending)
        pending_true_positive += len(gold_pending & predicted_pending)
        omissions = len(predicted_pending - gold_pending)
        characterization_omissions += omissions
        correction_components["characterization_entries"] += omissions
        row.update({
            "label_pt_snapshot": annotation["label_pt_snapshot"],
            "evidence_limit": annotation["evidence_limit"],
            "specificity": annotation["specificity"],
            "information_absent": annotation["information_absent"],
            "error_categories": categories,
        })
        for category in categories:
            errors.append({
                "case_id": row["case_id"],
                "mention_text": row["mention_text"],
                "hpo_id": row["target_hpo_id"],
                "category": category,
                "top_hpo_id": top_hpo_id,
            })

    pending_precision = pending_true_positive / pending_predicted if pending_predicted else 0.0
    pending_recall = pending_true_positive / pending_gold if pending_gold else 0.0
    ranks = [row["gold_span_target_rank"] for row in gold]
    observations = review_observations or []
    elapsed_seconds = []
    explicit_corrections = []
    valid_case_ids = {str(case["case_id"]) for case in cases}
    for observation in observations:
        if str(observation.get("case_id")) not in valid_case_ids:
            raise ValueError("Observação humana aponta para case_id desconhecido.")
        elapsed = float(observation.get("elapsed_seconds", 0))
        corrections = int(observation.get("correction_actions", -1))
        if elapsed <= 0 or corrections < 0:
            raise ValueError("Observação humana deve informar tempo positivo e correções não negativas.")
        elapsed_seconds.append(elapsed)
        explicit_corrections.append(corrections)

    context_confusion = {
        expected: {
            observed: sum(
                row["assertion"] == expected and row["predicted_assertion"] == observed
                for row in gold
            )
            for observed in sorted(CONTEXTS)
        }
        for expected in sorted(CONTEXTS)
    }
    summary = {
        "status": "development_exploratory_not_clinically_validated",
        "dataset_id": dataset["dataset_id"],
        "n_cases": base["n_cases"],
        "n_gold_mentions": base["n_gold_mentions"],
        "n_negative_controls": sum(not case["annotations"] for case in cases),
        "extraction": {key: base[key] for key in ("exact_span_precision", "exact_span_recall", "exact_span_f1", "relaxed_span_recall")},
        "normalization_and_ranking": {
            "gold_span_accuracy_at_1": base["linking_accuracy_at_1"],
            "gold_span_accuracy_at_5": base["linking_accuracy_at_5"],
            "gold_span_mrr_at_5": round(statistics.fmean(1 / int(rank) if rank and int(rank) <= 5 else 0.0 for rank in ranks), 4),
        },
        "context": {
            "accuracy": base["assertion_accuracy"],
            "macro_f1": base["assertion_macro_f1"],
            "confusion_matrix": context_confusion,
        },
        "pending_fields": {
            "precision": round(pending_precision, 4),
            "recall": round(pending_recall, 4),
            "characterization_omissions": characterization_omissions,
            "note": "O baseline marca todos os campos como pendentes; omissão indica informação presente no texto mas não estruturada automaticamente."
        },
        "review": {
            "correction_components_proxy": dict(sorted(correction_components.items())),
            "proxy_total": sum(correction_components.values()),
            "human_elapsed_seconds": {
                "mean": round(statistics.fmean(elapsed_seconds), 3),
                "median": round(statistics.median(elapsed_seconds), 3),
            } if elapsed_seconds else None,
            "human_correction_actions_mean": round(statistics.fmean(explicit_corrections), 3) if explicit_corrections else None,
            "human_observations": len(observations),
            "note": "Observações só entram por arquivo fornecido explicitamente; não há telemetria automática. Sem observações, o proxy computacional não representa tempo humano."
        },
        "negative_control_false_positive_rate": base["negative_control_false_positive_rate"],
        "latency_mean_ms": base["latency_mean_ms"],
        "latency_median_ms": base["latency_median_ms"],
        "errors_by_category": {category: sum(error["category"] == category for error in errors) for category in ERROR_CATEGORIES},
        "interpretation": "Resultado exploratório no desenvolvimento sintético; não demonstra generalização nem desempenho clínico."
    }
    return gold, errors, summary
