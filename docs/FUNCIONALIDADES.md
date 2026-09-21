# Funcionalidades do repositório

Inventário do que existe hoje, levantado lendo o código. O repositório tem
**duas frentes** com propósitos, entradas e dependências diferentes.

| | Frente A — bancada de anotação | Frente B — painel de alvos |
|---|---|---|
| Pergunta | dado um texto clínico em português, que conceitos HPO ele menciona | dadas as doenças-alvo, que fenótipos, genes e posições genotipadas existem |
| Entrada | texto livre (casos sintéticos) | `phenotype.hpoa`, `genes_to_disease.txt`, `.snp` |
| Entrada principal | `scripts/run_web.py`, `streamlit_app.py` | `scripts/hpo_panel_cli.py` |
| Dependências | rapidfuzz, rank_bm25, numpy, torch, transformers, streamlit, fastapi | só biblioteca padrão |
| Estado | implementada, com resultado negativo documentado | em construção, prioridade atual |

O `__init__.py` usa importação preguiçosa (PEP 562) justamente para que a
frente B não falhe por falta das bibliotecas da frente A.

---

# Frente A — bancada de anotação fenotípica

## A1. Interfaces

**API local FastAPI** (`src/hpo_ptbr/web_api.py`), restrita a
`127.0.0.1`. Bloqueia origem não listada (403), exige JSON em POST (415),
corta corpo acima de 256 KB (413), força `Cache-Control: no-store`.

| rota | o que faz |
|---|---|
| `GET /api/health` | versão dos dados, termos ativos, rótulos PT, termos ranqueáveis |
| `GET /api/examples` | casos sintéticos de demonstração |
| `POST /api/analyze` | extrai trechos do texto e ranqueia por 3 métodos, com latência |
| `POST /api/mentions` | mesmo pacote, para um trecho marcado à mão |
| `POST /api/search` | busca manual por rótulo ou por `HP:\d{7}` |
| `POST /api/semantic` | reranqueia com SapBERT; falha vira 503 com instrução de seguir no léxico |
| `GET /api/concepts/{id}` | conceito, pais, filhos e caminho até a raiz |
| `POST /api/export` | valida e exporta o perfil revisado com proveniência |

**Interface de pesquisa Streamlit** (`streamlit_app.py`), cinco páginas:
cobertura de tradução; mapeador por método; **anotação assistida** (a
bancada de fato: destaque de evidência, correção de trecho, escolha do
conceito, asserção, exportação); experimento piloto; arquitetura.

**Lançador** (`scripts/run_web.py`) sobe as duas, checando portas livres
sem matar processos alheios.

## A2. Métodos de mapeamento texto → HPO

| método | como funciona |
|---|---|
| `exact` | igualdade do texto normalizado com o rótulo PT |
| `fuzzy` | `rapidfuzz.WRatio` contra todos os rótulos PT |
| `bm25` | BM25Okapi sobre tokens dos rótulos PT |
| `semantic` | cosseno entre embeddings dos rótulos PT |
| `semantic_bilingual` | máximo entre similaridade PT e EN |
| `semantic_alias` | inclui sinônimos exatos em inglês no índice |
| `hybrid` | atalho por correspondência exata; senão Reciprocal Rank Fusion (k=60) |

Encoder semântico: SapBERT (`cambridgeltl/SapBERT-UMLS-2020AB-all-lang-from-XLMR`),
revisão fixa, sha256 declarado, `local_files_only`.

Variante paralela em `official_term_index.py`: os mesmos quatro rankers
sobre um índice de **termos oficiais** (rótulo PT + rótulo EN + sinônimos
exatos EN), com proveniência por termo e `human_review_required=True`.

## A3. Detecção de evidência (onde no texto)

- **`evidence.py`** — janelas de 1 a 5 tokens, corte por `WRatio ≥ 0.92`,
  resolução gulosa de sobreposição.
- **`semantic_evidence.py`** — mesmas janelas, pontuadas por embedding;
  opção de não atravessar pontuação.
- **`hybrid_evidence.py`** — união dos dois, com prioridade lexical.
- **`mention_ner.py` / `mention_detection.py`** — NER médico em português
  (`HUMADEX/portugese_medical_ner`), decodificação BIOES ou agregação por
  palavra.

## A4. Contexto e anotação

- **`assertion.py`** — classificador de pistas de contexto em português:
  `present`, `absent`, `uncertain`, `family_history`, olhando à esquerda
  até a fronteira de sentença.
- **`annotation.py`** — núcleo compartilhado pela API e pelo Streamlit:
  localizar ocorrências, ranquear candidatos com motivo em português,
  buscar por rótulo ou ID, normalizar 6 campos de caracterização (início,
  gravidade, evolução, frequência, lateralidade, histórico familiar) e
  montar o export `hpo-ptbr-review-v1`.
- **`review.py`** — destaque HTML com `<mark>`, menções de ouro não
  previstas, export exigindo uma decisão por evidência.

## A5. Ontologia e dados

- **`ontology.py`** — conceitos, sinônimos, pais/filhos, `path_to_root`,
  subárvore de `HP:0000118`.
  **Atenção:** `path_to_root` percorre um caminho único num grafo de
  múltiplos pais e **não serve como teste de ancestralidade** — perde cerca
  de 42% dos ancestrais reais.
- **`aliases.py`** — extração de sinônimos exatos em inglês do `hp.json`.
- **`data.py`** — carga do snapshot. **Descarta silenciosamente linhas sem
  `label_pt`** (12.678 de 19.836 conceitos).
- **`normalize.py`** — normalização e tokenização.
  **Atenção:** mantém stopwords portuguesas, e o BM25 ranqueia sobre elas.
- **`hashing.py`** — `content_sha256` (CRLF→LF, congelamentos internos) vs
  `raw_sha256` (bytes crus, fontes externas).

## A6. Avaliação, congelamento e relatório

- **`evaluation.py`** — Acc@1, Acc@5, MRR@20, latência e taxa de ID
  inválido, por estrato.
- **`benchmark.py`** — validação estrutural do benchmark v1: unicidade,
  splits, controles negativos sem menção, offsets que reproduzem o texto,
  paráfrase que não repete o rótulo, ausência de sobreposição.
- **`benchmark_evaluation.py`** — pipeline ponta a ponta: P/R/F1 de span,
  recall relaxado por IoU, linking Acc@1/Acc@5, macro-F1 de asserção,
  falso positivo em controles negativos.
- **`protocol.py`** — ciclo completo do holdout: seleção com seed fixa
  (20260717), 5 regras de variação ortográfica, formulário cego de revisão,
  substituição de rejeitados com motivo registrado, e congelamento com
  sha256.
- **`experiment.py`** — `result_fingerprint` (hash que exclui latências),
  `promotion_gate` (4 critérios pré-registrados) e verificação do holdout
  congelado.
- **`phase2_evaluation.py`** — validação do dataset sintético (proíbe o
  rótulo HPO literal como pista, exige contexto e caracterização),
  **auditoria de vazamento entre splits** (texto, família de template,
  menção, impressão morfológica, termos oficiais, parentesco ontológico até
  distância 2) e 8 categorias de erro.
- **`reporting.py`** — relatório comparativo marcando `dataset_role`,
  `tuning_allowed` e `claim_scope` por bloco.
- **`deployment.py`** — prontidão do dashboard; garante que `torch` não
  vaze para o `requirements.txt` principal.

## A7. Scripts da frente A

**Dados:** `build_snapshot.py`, `build_ontology_index.py`,
`build_aliases.py`, `create_notebook.py`, `download_mention_model.py`.

**Holdout:** `prepare_holdout_review.py`, `replace_rejected_holdout.py`,
`freeze_holdout.py`.

**Benchmark v1:** `prepare_benchmark_v1_development.py`,
`review_benchmark_v1_development.py`, `confirm_benchmark_v1_development.py`.

**Avaliações lexicais:** `run_evaluation.py`, `evaluate_evidence.py`,
`benchmark_evidence.py`, `run_benchmark_v1_development.py`.

**Avaliações semânticas e híbridas:** `run_semantic_evaluation.py`,
`run_semantic_evidence_experiment.py`, `run_experiment1.py`,
`run_benchmark_v1_candidates.py`, `build_benchmark_v1_candidate_analysis.py`.

**NER:** `run_mention_detection_experiment.py`,
`run_mention_detection_word_aggregation.py`.

**Fase 2:** `run_phase2_development.py`, `run_phase2_iteration2_offline.py`.

**Relatório:** `build_comparison_report.py`, `check_dashboard_readiness.py`.

---

# Frente B — painel de alvos fenotípicos

Uma CLI, `scripts/hpo_panel_cli.py`, com cinco subcomandos. Guia de uso
completo em `docs/USO_PAINEL_DE_ALVOS.md`.

| subcomando | o que faz |
|---|---|
| `snapshot` | normaliza `phenotype.hpoa` + `genes_to_disease.txt` com manifesto de proveniência; **recusa se a release divergir** |
| `search` | acha o identificador de uma doença por substring do nome |
| `profile` | doença → fenótipos e genes (`--aspects`, `--somente-mendelianas`, `--json`) |
| `term` | termo HPO → doenças → genes (`--somente-mendelianas`, `--somente-com-gene`, `--json`) |
| `panel` | caracteriza um `.snp` EIGENSTRAT e **verifica o build declarado** contra o próprio arquivo |

Módulos: `hpoa.py`, `gene_disease.py`, `term_targets.py`,
`genotype_panel.py` — todos só com biblioteca padrão.

Proteções que esta frente implementa, e que são o seu valor:

- release declarada no cabeçalho conferida contra o snapshot terminológico;
- sobreposição medida quando a fonte não declara release;
- qualificador `NOT` separado das ocorrências, nunca somado;
- `association_type` ausente contabilizado por fonte (o Orphanet inteiro
  chega como `UNKNOWN`);
- build do genoma obrigatório, verificado por evidência interna, com saída
  diferente de zero quando a declaração é contradita;
- recusa de cruzamento entre builds divergentes.

---

# O que não existe

- Expansão por ancestrais no grafo da HPO (o `term` só vê anotação direta).
- Busca de termo HPO por rótulo (só por identificador).
- Ingestão do ClinVar.
- O cruzamento final: de quantas doenças-alvo o painel 1240K fala.
- Tradução automática de termos sem rótulo PT — por decisão, não por falta.

# Limitações conhecidas que valem repetir

1. `fuzzy` satura em 0,8550 com 50 a 520 conceitos empatados; o desempate
   por `hpo_id` é que decide o Top-5.
2. BM25 ranqueia sobre stopwords portuguesas.
3. `path_to_root` não é teste de ancestralidade.
4. O congelamento por hash não cobre `ontology.py`, `annotation.py`,
   `web_api.py`, `data.py`.
5. `data.py::load_snapshot` descarta 12.678 de 19.836 conceitos sem
   `label_pt`.
6. Cobertura PT das anotações: 40,62% — e 5 dos 7 conceitos mais anotados
   não têm rótulo em português.
