from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from hpo_ptbr.data import load_metadata, load_snapshot
from hpo_ptbr.evidence import EvidenceExtractor
from hpo_ptbr.rankers import Bm25Mapper, ExactMapper, FuzzyMapper
from hpo_ptbr.review import build_review_export, highlight_evidence, unmatched_mentions

st.set_page_config(page_title="HPO-PTBR Lab", page_icon="🧬", layout="wide")

st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 3rem;}
    .hero {padding: 1.4rem 1.6rem; border-radius: 16px; background: linear-gradient(120deg,#0f766e,#164e63); color:white; margin-bottom:1.2rem;}
    .hero h1 {margin:0; font-size:2.1rem;}
    .hero p {margin:.45rem 0 0; opacity:.9;}
    .notice {padding:.9rem 1rem; border-left:4px solid #f59e0b; background:#fffbeb; border-radius:8px;}
    .evidence-text {padding:1rem 1.1rem; border:1px solid #cbd5e1; border-radius:10px; background:#f8fafc; font-size:1.05rem; line-height:1.8;}
    .evidence-text mark {background:#fef08a; padding:.1rem .2rem; border-radius:4px;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def resources():
    records = load_snapshot(ROOT / "data/processed/hpo_ptbr.csv")
    metadata = load_metadata(ROOT / "data/processed/metadata.json")
    version = str(metadata["data_version"])
    return metadata, {
        "Exact": ExactMapper(records, version),
        "Fuzzy": FuzzyMapper(records, version),
        "BM25": Bm25Mapper(records, version),
    }


metadata, mappers = resources()

st.markdown(
    """
    <div class="hero">
      <h1>HPO-PTBR Lab</h1>
      <p>Recuperação reproduzível de conceitos da Human Phenotype Ontology a partir de expressões curtas em português.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.subheader("Navegação")
    page = st.radio(
        "Página",
        ["Cobertura", "Mapeador", "Descrição sintética", "Experimento", "Arquitetura"],
    )
    st.divider()
    st.caption(f"Dados: `{metadata['data_version']}`")
    st.caption(f"Gerado em: {str(metadata['generated_at'])[:10]}")
    st.caption("Dados públicos e sintéticos. Nenhum prontuário é processado.")

if page == "Cobertura":
    st.header("Cobertura da tradução portuguesa")
    col1, col2, col3 = st.columns(3)
    col1.metric("Termos HPO ativos", f"{metadata['active_terms']:,}".replace(",", "."))
    col2.metric("Rótulos em português", f"{metadata['translated_labels_pt']:,}".replace(",", "."))
    col3.metric("Cobertura", f"{metadata['label_coverage_percent']}%")

    chart = pd.DataFrame(
        {
            "Categoria": ["Com rótulo PT", "Sem rótulo PT"],
            "Termos": [
                metadata["translated_labels_pt"],
                metadata["active_terms"] - metadata["translated_labels_pt"],
            ],
        }
    ).set_index("Categoria")
    st.bar_chart(chart, horizontal=True)
    st.subheader("Amostra de lacunas")
    missing = pd.read_csv(ROOT / "data/processed/untranslated_terms.csv").head(100)
    st.dataframe(missing, width="stretch", hide_index=True)

elif page == "Mapeador":
    st.header("Mapeador PT-BR → HPO")
    st.markdown(
        '<div class="notice"><strong>Protótipo de pesquisa:</strong> não realiza diagnóstico e não deve receber dados clínicos reais.</div>',
        unsafe_allow_html=True,
    )
    method_name = st.selectbox("Método", list(mappers))
    top_k = st.slider("Candidatos por expressão", 1, 10, 5)
    raw_queries = st.text_area(
        "Expressões fenotípicas — uma por linha",
        value="microcefalia\npressão arterial elevada\nbaixa-estatura",
        height=130,
        max_chars=2000,
    )
    if st.button("Mapear", type="primary"):
        queries = [line.strip() for line in raw_queries.splitlines() if line.strip()]
        if not queries:
            st.error("Informe ao menos uma expressão.")
        elif len(queries) > 10:
            st.error("O limite é de dez expressões por execução.")
        else:
            payload = []
            for query in queries:
                try:
                    result = mappers[method_name].map(query, top_k=top_k)
                except ValueError as error:
                    st.error(f"{query}: {error}")
                    continue
                payload.append(result.to_dict())
                st.subheader(query)
                if not result.candidates:
                    st.info("Nenhuma correspondência encontrada por este método.")
                    continue
                st.dataframe(
                    pd.DataFrame([candidate.to_dict() for candidate in result.candidates]),
                    width="stretch",
                    hide_index=True,
                )
                st.caption(f"Latência: {result.latency_ms} ms")
            if payload:
                serialized = json.dumps(payload, ensure_ascii=False, indent=2)
                st.download_button(
                    "Baixar resultados JSON",
                    data=serialized,
                    file_name="hpo_ptbr_resultados.json",
                    mime="application/json",
                )

elif page == "Descrição sintética":
    st.header("Revisão de fenótipos em texto sintético")
    st.markdown(
        '<div class="notice"><strong>Prova de conceito experimental:</strong> revise sugestões HPO extraídas de texto totalmente inventado. A ferramenta pode omitir fenótipos, não mede confiança clínica e não realiza diagnóstico.</div>',
        unsafe_allow_html=True,
    )
    examples = json.loads(
        (ROOT / "data/demo/synthetic_review_cases.json").read_text(encoding="utf-8")
    )
    example = st.selectbox(
        "Cenário sintético",
        examples,
        format_func=lambda item: f"{item['domain']} — {item['title']}",
    )
    description = st.text_area(
        "Descrição para revisão",
        value=example["text"],
        height=140,
        max_chars=1000,
    )
    with st.expander("Configurações técnicas"):
        method_name = st.selectbox(
            "Método para ordenar candidatos", list(mappers), index=1
        )
        top_k = st.slider("Alternativas por trecho", 1, 10, 5)
        st.caption(
            "Scores são usados apenas para ordenação e não representam probabilidade clínica."
        )
    context = {
        "case_id": example["id"],
        "description": description,
        "method": method_name,
        "top_k": top_k,
    }
    if st.button("Analisar descrição sintética", type="primary"):
        try:
            extractor = EvidenceExtractor(mappers[method_name])
            result = extractor.map_text(description, top_k=top_k)
        except ValueError as error:
            st.error(str(error))
        else:
            st.session_state["evidence_analysis"] = result.to_dict()
            st.session_state["evidence_context"] = context

    analysis = st.session_state.get("evidence_analysis")
    if analysis and st.session_state.get("evidence_context") == context:
        spans = analysis["spans"]
        missed_mentions = unmatched_mentions(example, spans)
        col1, col2, col3 = st.columns(3)
        col1.metric("Evidências encontradas", len(spans))
        col2.metric("Sugestões para revisar", len(spans))
        col3.metric("Menções do cenário não encontradas", len(missed_mentions))

        st.subheader("Texto com evidências destacadas")
        st.markdown(
            highlight_evidence(description, spans),
            unsafe_allow_html=True,
        )
        if missed_mentions:
            missed_text = ", ".join(f'“{mention["text"]}”' for mention in missed_mentions)
            st.warning(
                f"Neste cenário de teste, ficaram sem correspondência automática: {missed_text}."
            )
        st.caption(
            "Ausência de destaque não significa ausência de fenótipo. Todo resultado exige revisão humana."
        )

        reviews = []
        for index, span in enumerate(spans, start=1):
            candidates = span["candidates"]
            with st.container(border=True):
                st.markdown(f"### Evidência {index}: “{span['text']}”")
                if not candidates:
                    st.warning("O trecho não possui candidato HPO para revisão.")
                    reviews.append(
                        {
                            "evidence_text": span["text"],
                            "start": span["start"],
                            "end": span["end"],
                            "selected_hpo_id": None,
                            "review_status": "Sem candidato",
                        }
                    )
                    continue
                candidate_by_id = {
                    candidate["hpo_id"]: candidate for candidate in candidates
                }
                selected_hpo_id = st.selectbox(
                    "Conceito HPO selecionado",
                    list(candidate_by_id),
                    format_func=lambda hpo_id, options=candidate_by_id: (
                        f"{options[hpo_id]['label_pt']} — {hpo_id}"
                    ),
                    key=f"selected_{example['id']}_{index}",
                )
                review_status = st.selectbox(
                    "Decisão da revisão",
                    ["Pendente", "Aceitar sugestão", "Revisar alternativas", "Descartar trecho"],
                    key=f"status_{example['id']}_{index}",
                )
                with st.expander("Alternativas e detalhes técnicos"):
                    alternatives = pd.DataFrame(candidates).rename(
                        columns={
                            "hpo_id": "HPO ID",
                            "label_pt": "Termo em português",
                            "label_en": "Termo em inglês",
                            "score": "Score de ranking",
                            "rank": "Posição",
                        }
                    )
                    st.dataframe(alternatives, width="stretch", hide_index=True)
                    st.caption(
                        f"Trecho nos caracteres {span['start']}–{span['end']}; score do detector {span['detector_score']:.3f}."
                    )
                reviews.append(
                    {
                        "evidence_text": span["text"],
                        "start": span["start"],
                        "end": span["end"],
                        "selected_hpo_id": selected_hpo_id,
                        "review_status": review_status,
                    }
                )

        review_payload = build_review_export(analysis, reviews)
        serialized = json.dumps(review_payload, ensure_ascii=False, indent=2)
        st.download_button(
            "Baixar revisão estruturada",
            data=serialized,
            file_name="hpo_ptbr_revisao_sintetica.json",
            mime="application/json",
        )
        st.caption(f"Tempo de processamento: {analysis['latency_ms']} ms")

elif page == "Experimento":
    st.header("Piloto com 30 expressões")
    summary = pd.read_csv(ROOT / "data/results/evaluation_summary.csv")
    overall = summary[summary["stratum"] == "ALL"].copy()
    st.dataframe(overall, width="stretch", hide_index=True)
    st.subheader("Accuracy@5 por estrato")
    stratified = summary[summary["stratum"] != "ALL"].pivot(
        index="stratum", columns="method", values="accuracy_at_5"
    )
    st.bar_chart(stratified)
    st.caption(
        "O piloto é técnico e sintético; não constitui benchmark clínico nem evidência de validade externa."
    )
    st.subheader("Verificação funcional da descrição sintética")
    evidence_summary = json.loads(
        (ROOT / "data/results/evidence_evaluation_summary.json").read_text(
            encoding="utf-8"
        )
    )
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Menções detectáveis", evidence_summary["n_detectable_mentions"])
    col2.metric(
        "Recall de trecho",
        f"{evidence_summary['exact_span_recall'] * 100:.0f}%",
    )
    col3.metric(
        "HPO Accuracy@1",
        f"{evidence_summary['hpo_accuracy_at_1'] * 100:.0f}%",
    )
    col4.metric(
        "Falha conhecida reproduzida",
        f"{evidence_summary['known_miss_reproduction_rate'] * 100:.0f}%",
    )
    st.warning(
        f"Sanity check construído com {evidence_summary['n_cases']} textos de desenvolvimento: não mede generalização e não utiliza o holdout."
    )

else:
    st.header("Arquitetura por fases")
    st.markdown(
        """
        ### Sprint atual
        **Expressão fenotípica curta PT-BR → candidatos HPO válidos**

        ### Roadmap validado com o contexto da orientação
        `Texto clínico PT-BR` → `SNOMED CT` → `OMOP CDM` → `HPO` → `Phenopacket` → `priorização genética`

        | Componente | Papel | Estado |
        |---|---|---|
        | HPO | Fenótipos relevantes para genética | Implementado no protótipo |
        | SNOMED CT | Normalização clínica ampla | Próxima fase; requer serviço/licença |
        | OMOP CDM | Eventos observacionais padronizados | Próxima fase; Athena/vocabulários |
        | Phenopackets | Perfil fenotípico/genômico interoperável | Planejado |
        | Priorização | Validação downstream com ferramenta especializada | Planejado |

        SNOMED e OMOP estão no escopo global, mas não são simulados nesta demonstração. Isso evita mostrar integração fictícia.
        """
    )

st.divider()
st.caption("HPO-PTBR Lab · protótipo acadêmico · fontes e versões registradas no repositório")
