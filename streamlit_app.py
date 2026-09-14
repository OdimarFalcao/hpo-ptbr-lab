from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from hpo_ptbr.annotation import (
    ASSERTION_LABELS,
    build_annotation_span,
    build_workbench_export,
    candidate_union,
    find_occurrences,
    occurrence_label,
    replace_overlapping_span,
    search_candidates,
)
from hpo_ptbr.assertion import PortugueseContextCueClassifier
from hpo_ptbr.data import load_metadata, load_snapshot
from hpo_ptbr.evidence import EvidenceExtractor
from hpo_ptbr.ontology import load_ontology_index
from hpo_ptbr.rankers import Bm25Mapper, ExactMapper, FuzzyMapper
from hpo_ptbr.review import highlight_evidence, unmatched_mentions

st.set_page_config(page_title="HPO-PTBR Lab", page_icon="🧬", layout="wide")

st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 3rem;}
    .hero {padding: 1.4rem 1.6rem; border-radius: 16px; background:#102529; color:#e8f3f1; margin-bottom:1.2rem;}
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
    ontology = load_ontology_index(ROOT / "data/processed/hpo_ontology.json.gz")
    version = str(metadata["data_version"])
    if ontology.data_version != version:
        raise ValueError("Índice ontológico e snapshot HPO possuem versões diferentes.")
    return metadata, ontology, {
        "Exact": ExactMapper(records, version),
        "Fuzzy": FuzzyMapper(records, version),
        "BM25": Bm25Mapper(records, version),
    }


@st.cache_resource(show_spinner=False)
def optional_sapbert_mapper():
    from hpo_ptbr.sapbert import SapBertEncoder
    from hpo_ptbr.semantic import SemanticMapper

    records = load_snapshot(ROOT / "data/processed/hpo_ptbr.csv")
    version = str(load_metadata(ROOT / "data/processed/metadata.json")["data_version"])
    return SemanticMapper(
        records,
        version,
        SapBertEncoder(local_files_only=True),
    )


def display_label(hpo_id: str) -> str:
    concept = ontology.require(hpo_id)
    label = concept.label_pt or concept.label_en
    return f"{label} — {hpo_id}"


def span_widget_key(prefix: str, case_id: str, span: dict[str, object]) -> str:
    fingerprint = hashlib.sha1(
        f"{case_id}|{span['start']}|{span['end']}|{span['text']}".encode("utf-8")
    ).hexdigest()[:12]
    return f"{prefix}_{fingerprint}"


def related_labels(hpo_ids: tuple[str, ...], limit: int = 8) -> str:
    labels = []
    for hpo_id in hpo_ids[:limit]:
        concept = ontology.require(hpo_id)
        labels.append(f"{concept.label_pt or concept.label_en} (`{hpo_id}`)")
    if len(hpo_ids) > limit:
        labels.append(f"mais {len(hpo_ids) - limit}")
    return ", ".join(labels) if labels else "Nenhum no snapshot."


metadata, ontology, mappers = resources()

st.markdown(
    """
    <div class="hero">
      <h1>HPO-PTBR Lab</h1>
      <p>Anotação assistida e reproduzível de fenótipos em português para conceitos válidos da Human Phenotype Ontology.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.link_button("Abrir nova bancada web", "http://127.0.0.1:8000")
    st.caption("Área de pesquisa · Streamlit de referência")
    st.subheader("Navegação")
    page = st.radio(
        "Página",
        ["Cobertura", "Mapeador", "Anotação assistida", "Experimento", "Arquitetura"],
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

elif page == "Anotação assistida":
    st.header("Bancada de anotação fenotípica")
    st.markdown(
        '<div class="notice"><strong>Laboratório experimental:</strong> use somente conteúdo público ou sintético. O sistema pode omitir ou sugerir trechos incorretos; toda anotação exige revisão humana e não constitui diagnóstico.</div>',
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
        "Descrição sintética para revisão",
        value=example["text"],
        height=140,
        max_chars=1000,
    )
    with st.expander("Configurações técnicas"):
        top_k = st.slider("Alternativas por trecho", 1, 10, 5)
        st.caption(
            "A detecção automática permanece lexical. Exact, Fuzzy e BM25 são comparados por trecho; scores servem somente para ordenação."
        )
    context = {
        "case_id": example["id"],
        "description": description,
        "top_k": top_k,
    }
    if st.button("Localizar fenótipos", type="primary"):
        try:
            extractor = EvidenceExtractor(mappers["Fuzzy"])
            result = extractor.map_text(description, top_k=top_k)
            classifier = PortugueseContextCueClassifier()
            spans = [
                build_annotation_span(
                    description,
                    span.start,
                    span.end,
                    source="lexical",
                    mappers=mappers,
                    classifier=classifier,
                    detector_score=span.detector_score,
                    top_k=top_k,
                )
                for span in result.spans
            ]
        except ValueError as error:
            st.error(str(error))
        else:
            st.session_state["evidence_analysis"] = result.to_dict()
            st.session_state["workbench_spans"] = spans
            st.session_state["workbench_context"] = context

    analysis = st.session_state.get("evidence_analysis")
    if analysis and st.session_state.get("workbench_context") == context:
        spans = st.session_state.get("workbench_spans", [])
        missed_mentions = (
            unmatched_mentions(example, spans)
            if description == example["text"]
            else []
        )
        col1, col2, col3 = st.columns(3)
        col1.metric(
            "Detectadas automaticamente",
            sum(span["source"] == "lexical" for span in spans),
        )
        col2.metric(
            "Adicionadas manualmente",
            sum(span["source"] == "manual" for span in spans),
        )
        col3.metric("Menções conhecidas não encontradas", len(missed_mentions))

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

        st.subheader("Adicionar ou corrigir um trecho")
        manual_phrase = st.text_input(
            "Copie do texto uma expressão que deveria ser anotada",
            key=f"manual_phrase_{example['id']}",
            placeholder="Ex.: pálpebra caída",
        )
        occurrences = find_occurrences(description, manual_phrase)
        selected_occurrence = 0
        if len(occurrences) > 1:
            selected_occurrence = st.selectbox(
                "A expressão aparece mais de uma vez. Escolha a ocorrência:",
                range(len(occurrences)),
                format_func=lambda index: occurrence_label(
                    description, *occurrences[index]
                ),
                key=f"manual_occurrence_{example['id']}",
            )
        if manual_phrase and not occurrences:
            st.warning("A expressão precisa existir exatamente no texto informado.")
        if st.button("Adicionar trecho à revisão"):
            if not occurrences:
                st.error("Informe uma expressão existente no texto.")
            else:
                start, end = occurrences[selected_occurrence]
                replacement = build_annotation_span(
                    description,
                    start,
                    end,
                    source="manual",
                    mappers=mappers,
                    classifier=PortugueseContextCueClassifier(),
                    top_k=top_k,
                )
                st.session_state["workbench_spans"] = replace_overlapping_span(
                    spans, replacement
                )
                st.rerun()

        st.subheader("Revisar conceitos e contexto")
        reviews = []
        for index, span in enumerate(spans, start=1):
            span_key = span_widget_key("span", example["id"], span)
            with st.container(border=True):
                source_label = (
                    "detecção lexical" if span["source"] == "lexical" else "inclusão manual"
                )
                st.markdown(f"### Trecho {index}: “{span['text']}”")
                st.caption(
                    f"Origem: {source_label} · caracteres {span['start']}–{span['end']}"
                )

                with st.expander("IA experimental e busca de outro conceito"):
                    st.caption(
                        "O SapBERT é carregado somente neste botão, usa cache local e não altera a detecção do texto."
                    )
                    if st.button(
                        "Comparar candidatos SapBERT",
                        key=span_widget_key("sapbert", example["id"], span),
                    ):
                        try:
                            with st.spinner("Carregando modelo local e comparando o trecho..."):
                                semantic_result = optional_sapbert_mapper().map(
                                    str(span["text"]), top_k=top_k
                                )
                        except (ImportError, ModuleNotFoundError, OSError, ValueError) as error:
                            st.warning(
                                "SapBERT indisponível neste ambiente. A bancada lexical continua funcional. "
                                f"Detalhe técnico: {error}"
                            )
                        else:
                            span["rankings"]["SapBERT experimental"] = [
                                candidate.to_dict()
                                | {
                                    "method": "semantic",
                                    "reason": "similaridade semântica experimental",
                                }
                                for candidate in semantic_result.candidates
                            ]
                            st.session_state["workbench_spans"] = spans
                            st.rerun()

                    manual_search = st.text_input(
                        "Buscar por rótulo ou HPO ID",
                        key=span_widget_key("concept_search", example["id"], span),
                        placeholder="Ex.: ptose ou HP:0000508",
                    )
                    if st.button(
                        "Buscar conceito HPO",
                        key=span_widget_key("concept_search_button", example["id"], span),
                    ):
                        results = search_candidates(
                            manual_search,
                            mappers["Fuzzy"],
                            ontology,
                            top_k=top_k,
                        )
                        if not results:
                            st.warning("Nenhum conceito válido foi localizado.")
                        else:
                            span["rankings"]["Pesquisa manual"] = results
                            st.session_state["workbench_spans"] = spans
                            st.rerun()

                candidates = candidate_union(span["rankings"])
                if not candidates:
                    st.warning("O trecho não possui candidato HPO para revisão.")
                    reviews.append(
                        {
                            "evidence_text": span["text"],
                            "start": span["start"],
                            "end": span["end"],
                            "source": span["source"],
                            "selected_hpo_id": None,
                            "decision": "discard",
                            "assertion": span["suggested_assertion"],
                            "suggested_assertion": span["suggested_assertion"],
                            "rankings": span["rankings"],
                            "human_modified": True,
                        }
                    )
                    continue
                candidate_by_id = {
                    candidate["hpo_id"]: candidate for candidate in candidates
                }
                fuzzy_candidates = span["rankings"].get("Fuzzy", [])
                default_hpo_id = (
                    fuzzy_candidates[0]["hpo_id"]
                    if fuzzy_candidates
                    else candidates[0]["hpo_id"]
                )
                selected_hpo_id = st.selectbox(
                    "Conceito HPO selecionado",
                    list(candidate_by_id),
                    index=list(candidate_by_id).index(default_hpo_id),
                    format_func=display_label,
                    key=span_widget_key("selected", example["id"], span),
                )
                assertion_options = list(ASSERTION_LABELS)
                assertion = st.selectbox(
                    "Contexto da menção",
                    assertion_options,
                    index=assertion_options.index(span["suggested_assertion"]),
                    format_func=lambda value: ASSERTION_LABELS[value],
                    key=span_widget_key("assertion", example["id"], span),
                )
                decision_label = st.radio(
                    "Decisão",
                    ["Incluir no perfil", "Descartar trecho"],
                    horizontal=True,
                    key=span_widget_key("decision", example["id"], span),
                )
                decision = "include" if decision_label == "Incluir no perfil" else "discard"

                selected_concept = ontology.require(selected_hpo_id)
                st.markdown("**Informação ontológica oficial**")
                if selected_concept.definition_pt:
                    st.write(selected_concept.definition_pt)
                    st.caption("Definição oficial em português.")
                elif selected_concept.definition_en:
                    st.write(selected_concept.definition_en)
                    st.caption("Definição oficial disponível somente em inglês neste snapshot.")
                else:
                    st.caption("Este conceito não possui definição textual no snapshot utilizado.")
                if selected_concept.synonyms:
                    synonym_text = ", ".join(
                        synonym.text for synonym in selected_concept.synonyms[:8]
                    )
                    st.caption(f"Sinônimos oficiais: {synonym_text}")
                st.caption(f"Pais imediatos: {related_labels(selected_concept.parent_ids)}")
                st.caption(f"Filhos imediatos: {related_labels(selected_concept.child_ids)}")
                root_path = ontology.path_to_root(selected_hpo_id)
                if root_path:
                    st.caption(
                        "Caminho na ontologia: "
                        + " → ".join(
                            ontology.require(hpo_id).label_pt
                            or ontology.require(hpo_id).label_en
                            for hpo_id in reversed(root_path)
                        )
                    )

                with st.expander("Comparar rankings técnicos"):
                    ranking_names = list(span["rankings"])
                    ranking_tabs = st.tabs(ranking_names)
                    for tab, ranking_name in zip(
                        ranking_tabs, ranking_names, strict=True
                    ):
                        with tab:
                            ranking = span["rankings"][ranking_name]
                            if not ranking:
                                st.info("Este método não retornou candidatos.")
                                continue
                            alternatives = pd.DataFrame(ranking).rename(
                                columns={
                                    "hpo_id": "HPO ID",
                                    "label_pt": "Termo em português",
                                    "label_en": "Termo em inglês",
                                    "score": "Score de ranking",
                                    "rank": "Posição",
                                    "reason": "Motivo",
                                }
                            )
                            columns = [
                                column
                                for column in (
                                    "Posição",
                                    "HPO ID",
                                    "Termo em português",
                                    "Termo em inglês",
                                    "Score de ranking",
                                    "Motivo",
                                )
                                if column in alternatives
                            ]
                            st.dataframe(
                                alternatives[columns],
                                width="stretch",
                                hide_index=True,
                            )
                    if span["detector_score"] is not None:
                        st.caption(
                            f"Score de ranking do detector lexical: {span['detector_score']:.3f}."
                        )

                human_modified = (
                    span["source"] == "manual"
                    or selected_hpo_id != default_hpo_id
                    or assertion != span["suggested_assertion"]
                    or decision == "discard"
                )
                reviews.append(
                    {
                        "evidence_text": span["text"],
                        "text": span["text"],
                        "start": span["start"],
                        "end": span["end"],
                        "source": span["source"],
                        "selected_hpo_id": selected_hpo_id,
                        "decision": decision,
                        "assertion": assertion,
                        "suggested_assertion": span["suggested_assertion"],
                        "rankings": span["rankings"],
                        "human_modified": human_modified,
                    }
                )

        st.subheader("Perfil fenotípico revisado")
        profile_rows = []
        for review in reviews:
            if review["decision"] != "include" or not review["selected_hpo_id"]:
                continue
            concept = ontology.require(str(review["selected_hpo_id"]))
            profile_rows.append(
                {
                    "Trecho": review["text"],
                    "HPO ID": concept.hpo_id,
                    "Conceito": concept.label_pt or concept.label_en,
                    "Contexto": ASSERTION_LABELS[str(review["assertion"])],
                    "Origem": "Automática" if review["source"] == "lexical" else "Manual",
                }
            )
        if profile_rows:
            st.dataframe(pd.DataFrame(profile_rows), width="stretch", hide_index=True)
        else:
            st.info("Nenhuma anotação foi incluída no perfil.")

        review_payload = build_workbench_export(
            text=description,
            data_version=str(metadata["data_version"]),
            reviews=reviews,
            ontology=ontology,
        )
        serialized = json.dumps(review_payload, ensure_ascii=False, indent=2)
        st.download_button(
            "Baixar perfil revisado em JSON",
            data=serialized,
            file_name="hpo_ptbr_review_v1.json",
            mime="application/json",
        )
        st.caption(
            f"Detecção inicial: {analysis['latency_ms']} ms. Nenhum texto ou ajuste é persistido pelo sistema."
        )

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
