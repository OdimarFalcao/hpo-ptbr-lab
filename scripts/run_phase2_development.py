from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hpo_ptbr.data import load_metadata, load_snapshot
from hpo_ptbr.evidence import EvidenceExtractor
from hpo_ptbr.ontology import load_ontology_index
from hpo_ptbr.phase2_evaluation import (
    audit_split_leakage,
    evaluate_phase2,
    load_phase2_dataset,
)
from hpo_ptbr.rankers import FuzzyMapper

BASELINE_PATH = ROOT / "data/protocol/phase2_baseline_freeze.json"
PROTOCOL_PATH = ROOT / "data/protocol/phase2_evaluation_protocol.json"
DATASET_PATH = ROOT / "data/eval/phase2_development.json"
SPLIT_REGISTRY_PATH = ROOT / "data/eval/phase2_split_registry.json"
RESULTS_DIR = ROOT / "data/results"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_baseline() -> dict[str, object]:
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    for relative_path, expected_hash in baseline["sha256"].items():
        observed = _sha256(ROOT / relative_path)
        if observed != expected_hash:
            raise ValueError(f"Baseline divergiu em {relative_path}.")
    return baseline


def _load_review_observations(path: Path | None) -> list[dict[str, object]]:
    if path is None:
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Observações de revisão devem formar uma lista JSON.")
    return payload


def _percent(value: object) -> str:
    return f"{float(value) * 100:.1f}%"


def _report(summary: dict[str, object], metadata: dict[str, object]) -> str:
    extraction = summary["extraction"]
    ranking = summary["normalization_and_ranking"]
    context = summary["context"]
    pending = summary["pending_fields"]
    review = summary["review"]
    errors = summary["errors_by_category"]
    observed_recommendations = []
    if errors["mention_not_detected"] or errors["wrong_span"]:
        observed_recommendations.append("Avaliar um detector de menções orientado a paráfrases, mantendo o baseline congelado para comparação.")
    if errors["paraphrase_failure"]:
        observed_recommendations.append("Ampliar cobertura lexical somente com sinônimos e paráfrases rastreáveis e submetidos a revisão.")
    if errors["context_error"]:
        observed_recommendations.append("Expandir e testar separadamente as regras de incerteza e histórico familiar observadas nos erros.")
    if errors["portuguese_coverage_failure"]:
        observed_recommendations.append("Encaminhar conceitos sem rótulo PT oficial para curadoria; não promovê-los a tradução validada automaticamente.")
    recommendations = "\n".join(f"- {item}" for item in observed_recommendations) or "- Nenhuma mudança proposta sem erro observado."
    return f"""# Fase 2 — baseline em linguagem clínica natural

## Escopo

- Split executado: `development`.
- Dataset: `{metadata['dataset']}` (`{metadata['dataset_sha256']}`).
- Baseline: `{metadata['baseline_id']}`; hashes verificados antes da execução.
- Validação e holdout: não criados nem executados.
- Padrão-ouro: técnico e sintético, ainda sem validação clínica.

## Resultados medidos

| Dimensão | Métrica | Resultado |
|---|---|---:|
| Extração | F1 span exato | {_percent(extraction['exact_span_f1'])} |
| Extração | Recall relaxado | {_percent(extraction['relaxed_span_recall'])} |
| Normalização | Accuracy@1 em span ouro | {_percent(ranking['gold_span_accuracy_at_1'])} |
| Ranking | Accuracy@5 em span ouro | {_percent(ranking['gold_span_accuracy_at_5'])} |
| Contexto | Accuracy | {_percent(context['accuracy'])} |
| Contexto | Macro-F1 | {_percent(context['macro_f1'])} |
| Pendências | Precisão dos campos marcados pendentes | {_percent(pending['precision'])} |
| Pendências | Recall dos campos realmente ausentes | {_percent(pending['recall'])} |
| Controles | Casos com falso positivo | {_percent(summary['negative_control_false_positive_rate'])} |
| Execução | Latência média por caso | {summary['latency_mean_ms']} ms |

O baseline deixou de estruturar {pending['characterization_omissions']} valores de caracterização que estavam explícitos nos textos. O proxy computacional soma {review['proxy_total']} componentes de correção. Tempo humano real: {review['human_elapsed_seconds'] if review['human_elapsed_seconds'] is not None else 'não medido'}.

## Erros observados

{json.dumps(errors, ensure_ascii=False, indent=2)}

As categorias podem se sobrepor: por exemplo, uma paráfrase não detectada também pode expor falta de cobertura portuguesa. Isso serve para localizar causas, não para somar uma taxa única.

## Recomendações derivadas dos erros

{recommendations}

## Limites

Os resultados são exploratórios, pequenos e produzidos em desenvolvimento sintético. Não demonstram generalização, segurança clínica nem atingimento de limiar de aprovação. O proxy de revisão não substitui estudo com profissionais, e nenhuma tradução sintética foi tratada como oficial.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa somente o desenvolvimento da avaliação da Fase 2.")
    parser.add_argument("--review-observations", type=Path, help="JSON local e opt-in com tempo e ações de revisão; não é coletado automaticamente.")
    args = parser.parse_args()

    baseline = _verify_baseline()
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol["execution"]["allowed_split"] != "development":
        raise ValueError("Protocolo não autoriza desenvolvimento.")
    ontology = load_ontology_index(ROOT / "data/processed/hpo_ontology.json.gz")
    dataset = load_phase2_dataset(DATASET_PATH, ontology, expected_split="development")
    registry = json.loads(SPLIT_REGISTRY_PATH.read_text(encoding="utf-8"))
    if registry["validation"]["texts"] or registry["holdout"]["texts"]:
        raise ValueError("Validação ou holdout foram expostos no registro de desenvolvimento.")
    leakage_issues = audit_split_leakage(
        [dataset],
        ontology,
        related_distance=int(protocol["leakage_audit"]["block_ancestor_or_descendant_distance"]),
    )
    if leakage_issues:
        raise ValueError(f"Auditoria de vazamento falhou: {leakage_issues[:3]}")
    metadata_source = load_metadata(ROOT / "data/processed/metadata.json")
    if dataset["source"]["terminology_snapshot"] != metadata_source["data_version"]:
        raise ValueError("Dataset e snapshot terminológico divergem.")
    records = load_snapshot(ROOT / "data/processed/hpo_ptbr.csv")
    mapper = FuzzyMapper(records, str(metadata_source["data_version"]))
    pipeline = baseline["pipeline"]
    extractor = EvidenceExtractor(
        mapper,
        detection_threshold=float(pipeline["detector_threshold"]),
        max_span_tokens=int(pipeline["detector_max_span_tokens"]),
    )
    details, errors, summary = evaluate_phase2(
        extractor,
        dataset,
        ontology,
        relaxed_iou=float(protocol["execution"]["relaxed_span_iou"]),
        top_k=int(protocol["execution"]["gold_span_top_k"]),
        review_observations=_load_review_observations(args.review_observations),
    )
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    metadata = {
        "status": "development_exploratory_executed",
        "evaluated_at_utc": datetime.now(UTC).isoformat(),
        "dataset": DATASET_PATH.relative_to(ROOT).as_posix(),
        "dataset_sha256": _sha256(DATASET_PATH),
        "protocol": PROTOCOL_PATH.relative_to(ROOT).as_posix(),
        "protocol_sha256": _sha256(PROTOCOL_PATH),
        "baseline": BASELINE_PATH.relative_to(ROOT).as_posix(),
        "baseline_sha256": _sha256(BASELINE_PATH),
        "baseline_id": baseline["baseline_id"],
        "split": "development",
        "validation_used": False,
        "holdout_used": False,
        "clinical_validation": False,
        "leakage_audit": {
            "cross_split_issues": 0,
            "validation_status": registry["validation"]["status"],
            "holdout_status": registry["holdout"]["status"],
            "note": "Não há textos fora do desenvolvimento nesta versão; a auditoria cruzada deverá ser repetida quando conjuntos independentes forem fornecidos."
        },
    }
    outputs = {
        "phase2_development_summary.json": summary,
        "phase2_development_details.json": details,
        "phase2_development_error_analysis.json": errors,
        "phase2_development_metadata.json": metadata,
    }
    for filename, payload in outputs.items():
        (RESULTS_DIR / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (RESULTS_DIR / "phase2_development_report.md").write_text(_report(summary, metadata), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
