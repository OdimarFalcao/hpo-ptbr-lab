from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from hpo_ptbr.data import load_metadata, load_snapshot
from hpo_ptbr.rankers import Bm25Mapper, ExactMapper, FuzzyMapper

st.set_page_config(page_title="HPO-PTBR Lab", page_icon="🧬", layout="wide")

st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 3rem;}
    .hero {padding: 1.4rem 1.6rem; border-radius: 16px; background: linear-gradient(120deg,#0f766e,#164e63); color:white; margin-bottom:1.2rem;}
    .hero h1 {margin:0; font-size:2.1rem;}
    .hero p {margin:.45rem 0 0; opacity:.9;}
    .notice {padding:.9rem 1rem; border-left:4px solid #f59e0b; background:#fffbeb; border-radius:8px;}
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
    page = st.radio("Página", ["Cobertura", "Mapeador", "Experimento", "Arquitetura"])
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
