# HPO-PTBR Lab

Protótipo acadêmico para recuperar termos válidos da Human Phenotype Ontology a partir de expressões fenotípicas curtas em português brasileiro.

## O que entrega

- Snapshot versionado da HPO `2026-06-23` e da tradução portuguesa.
- Análise de cobertura dos rótulos em português.
- Três baselines reproduzíveis: exact match, fuzzy match e BM25.
- Piloto técnico com 30 expressões públicas/sintéticas.
- Dashboard Streamlit com cobertura, mapeador, resultados e roadmap.

## Limites

Este projeto não realiza diagnóstico, não processa prontuários e não usa dados clínicos reais. SNOMED CT e OMOP fazem parte da arquitetura futura, mas não são simulados nesta versão. Nenhum conteúdo SNOMED é redistribuído.

## Instalação

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

## Reproduzir os dados

Baixe os dois arquivos oficiais para `data/raw/`:

- `hp.json`: `https://github.com/obophenotype/human-phenotype-ontology/releases/latest/download/hp.json`
- `hp-pt.babelon.tsv`: `https://raw.githubusercontent.com/obophenotype/hpo-translations/main/babelon/hp-pt.babelon.tsv`

Depois execute:

```powershell
python scripts/build_snapshot.py
python scripts/run_evaluation.py
python scripts/create_notebook.py
```

O snapshot processado e os resultados usados pelo dashboard já estão versionados. Os arquivos brutos ficam fora do Git.

## Executar

```powershell
streamlit run streamlit_app.py
```

## Testar

```powershell
pytest
```

## Dados e proveniência

As versões, URLs e somas SHA-256 ficam em `data/processed/metadata.json`. O piloto em `data/eval/pilot_cases.csv` é estratificado em rótulos oficiais, variações ortográficas e paráfrases clínicas sintéticas.

## Roadmap

`texto clínico PT-BR → SNOMED CT → OMOP CDM → HPO → Phenopacket → priorização genética`

SNOMED CT exigirá serviço terminológico e licenciamento adequados. OMOP usará vocabulários padronizados obtidos via Athena em ambiente controlado.
