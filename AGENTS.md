# Contexto Operacional do Projeto (para Codex)

Atualizado em 2026-09-14.

## Objetivo do repositorio

Infraestrutura terminologica versionada sobre a Human Phenotype Ontology (HPO)
em portugues brasileiro, com revisao humana rastreavel.

O projeto esta em transicao de escopo. Duas frentes coexistem:

1. **Bancada de anotacao (implementada).** Texto clinico PT-BR -> mencoes ->
   conceito HPO -> contexto -> revisao humana -> exportacao determinista com
   proveniencia. Funciona na parte manual; a extracao automatica nao.
2. **Painel de alvos fenotipicos (direcao nova).** Doenca monogenica ->
   genes -> variantes causativas -> perfil HPO esperado -> cobertura frente
   ao painel genotipado disponivel. Serve a pesquisa de aDNA do PO.

A frente 2 e a prioridade. A frente 1 permanece no repositorio, documentada,
com seus resultados negativos preservados. Nao remover nem reescrever a
frente 1 sem autorizacao explicita.

A ferramenta organiza terminologia versionada e apoia revisao humana. Ela nao
constitui diagnostico, nao substitui julgamento profissional e nao autentica
evidencia clinica por conta propria.

## Stack

- Python 3.11+
- `fastapi`, `uvicorn`, `pydantic` (API)
- `rapidfuzz`, `rank-bm25`, `pandas` (recuperacao)
- `sentence-transformers` + SapBERT local (opcional, extra `semantic`)
- React + Vite + TypeScript (`web/`)
- `streamlit` (area historica de pesquisa)

## Entradas e saidas relevantes

- Snapshot terminologico: `data/processed/hpo_ptbr.csv`,
  `data/processed/hpo_ontology.json.gz`, `data/processed/metadata.json`
- Versao vigente: `hpo-2026-06-23_pt-62f1d254` (HPO 2026-06-23,
  traducao commit 62f1d254)
- Protocolos congelados: `data/protocol/`
- Conjuntos de avaliacao: `data/eval/`
- Resultados de execucao: `data/results/`
- Fontes brutas: `data/raw/` (fora do git)

## Pontos de entrada

- Bancada web: `python scripts/run_web.py`
  (FastAPI em 127.0.0.1:8000, Streamlit em 127.0.0.1:8504)
- Somente API: `python -m uvicorn hpo_ptbr.web_api:app --host 127.0.0.1 --port 8000`
- Avaliacao Fase 2: `python scripts/run_phase2_development.py`
- Iteracao 2 offline: `python scripts/run_phase2_iteration2_offline.py`
- Testes: `python -m pytest -q`

## Modulos centrais

- `src/hpo_ptbr/ontology.py` — indice ontologico, hierarquia, escopo fenotipico
- `src/hpo_ptbr/official_term_index.py` — indice de termos oficiais com proveniencia
- `src/hpo_ptbr/annotation.py` — perfil revisavel, caracterizacao, exportacao
- `src/hpo_ptbr/web_api.py` — API da bancada
- `src/hpo_ptbr/evidence.py` — detector lexical por janelas (nao funcional em linguagem natural)
- `src/hpo_ptbr/rankers.py` — Exact, Fuzzy, BM25
- `src/hpo_ptbr/assertion.py` — classificador de contexto por pistas em portugues
- `src/hpo_ptbr/phase2_evaluation.py` — metricas, auditoria de vazamento, taxonomia de erros

Codigo historico de pesquisa, nao integrado ao fluxo padrao:
`benchmark*.py`, `mention_*.py`, `semantic_evidence.py`, `hybrid*.py`,
`aliases.py`, `evaluation.py`, `experiment.py`, `protocol.py`, `reporting.py`.

## Riscos tecnicos ja observados

Confirmados por auditoria externa em 2026-09-14. Nao reintroduzir.

1. **`fuzz.WRatio` satura em consultas longas.** Contra rotulos curtos o score
   maximo trava em 0.8550 e 50 a 520 conceitos empatam nesse valor. Com
   desempate por `hpo_id` ascendente, o Top-5 vira uma fatia arbitraria do
   empate. Afeta `rankers.py:82` e `official_term_index.py:261`. Qualquer
   metrica de ranking lexical medida com WRatio em paráfrase longa e invalida.
2. **BM25 ranqueia sobre stopwords portuguesas.** `normalize.tokenize` nao
   remove `a`, `de`, `para`, `ao`, `os`, `com`. Consulta com `para` repetido
   recupera rotulos com `para o`. Afeta `rankers.py:93` e
   `official_term_index.py:271`.
3. **`path_to_root` nao e teste de ancestralidade.** Devolve um unico caminho
   num grafo multi-parental; perde ~42% dos ancestrais reais. Usado
   incorretamente em `scripts/run_phase2_iteration2_offline.py:192-194`,
   inflando a categoria `wrong_concept_different_branch`.
4. **O congelamento por hash nao cobre os artefatos que definem o detector.**
   `data/protocol/phase2_baseline_freeze.json` nao inclui `ontology.py`,
   `annotation.py`, `web_api.py` nem `data.py`. Apos a Iteracao 1 o universo
   do detector mudou sem que o freeze acusasse.
5. **`data.py::load_snapshot` descarta silenciosamente conceitos sem
   `label_pt`** (12.678 de 19.836). E a decisao mais cara do repositorio e
   esta numa linha sem comentario.
6. **O congelamento por hash esta preso ao Windows.** Os sha256 em
   `data/protocol/phase2_baseline_freeze.json` foram calculados sobre arquivos
   com quebra de linha CRLF. Em checkout Linux (incluindo o CI, que roda
   `pytest` em `ubuntu-latest`) os hashes divergem e 4 testes de integridade
   falham: `test_phase2_results.py`, `test_benchmark_results.py`,
   `test_benchmark_development.py`, `test_benchmark_candidate_results.py`.
   Verificado em 2026-09-14: `hpo_ptbr.csv` com LF da `8c708aea957f...`,
   com CRLF da `05a82409f712...`, que e o valor gravado no freeze.
   Corrigir exige normalizar antes de hashear ou fixar `eol=lf` no
   `.gitattributes`; em ambos os casos os hashes gravados mudam, entao a
   correcao e uma decisao de protocolo e deve ser registrada.
7. **Scripts que nao pertencem ao projeto estao rastreados no git**:
   `scripts/add_aula04_escrituracao.py`, `audit_aula04_review.py`,
   `audit_contas_review.py`, `docx_to_qa_html.py`, `make_contact_sheet.py`,
   `merge_contas_review.py`, `render_qa_html.cjs`, `render_qa_html.mjs`.
   Nao modificar, nao executar, nao usar como referencia.

## Estado do controle de versao

- Ultimo commit: `06fccfa` — "Implement phenotypic profile and Phase 2 evaluation"
- Iteracao 1 (filtro de escopo fenotipico) e Iteracao 2 (indice de termos
  oficiais) estao **na arvore de trabalho, nao commitadas**.
- Antes de qualquer reorganizacao de arquivos, commitar o que existe.

## Modo de atuacao do agente neste projeto

### Regra 1: recuperar contexto antes de editar

1. `git status --short`
2. confirmar branch atual
3. ler o arquivo alvo e os testes associados
4. ler os "Riscos tecnicos ja observados" acima

### Regra 2: mudancas pequenas e validaveis

- Um incremento por vez, com criterio de aceite declarado antes.
- Nao alterar comportamento sem teste cobrindo.
- Primeiro extrair com comportamento equivalente; depois corrigir logica.

### Regra 3: nao sujar o repositorio

- Nao commitar artefatos de execucao, saidas locais ou pastas temporarias.
- Respeitar `.gitignore`.
- Nao executar commit, push ou publicacao sem pedido explicito do PO.
- Preservar alteracoes locais nao commitadas.

### Regra 4: disciplina de dados e proveniencia

- Nenhuma fonte entra sem versao, URL e sha256 registrados.
- Nao alterar dataset oficial existente.
- Nao inventar traducao portuguesa. Conceito sem rotulo PT oficial recebe
  `label_pt_status: "unavailable"` e exibe o rotulo ingles com a fonte.
- Ausencia de informacao nunca vira negacao.

### Regra 5: disciplina experimental

- Protocolo pre-registrado antes de executar; hash do protocolo registrado.
- Nao consumir conjunto de validacao ou holdout.
- Nao definir metrica ou limiar depois de ver o resultado.
- Preservar resultado negativo. Gate reprovado permanece registrado.
- Teste unitario nao e evidencia de generalizacao.

### Regra 6: abstencao e preferivel a sugestao incorreta

Quando a fonte nao sustenta um valor, o campo fica ausente e explicito. Nao
preencher com palpite. Silencio nao e resposta aceitavel: a ausencia precisa
ser visivel para o revisor.

### Regra 7: documentar decisao tecnica

Toda correcao relevante entra no historico com: problema observado,
alteracao feita, funcionalidade afetada, **comando exato de validacao** e
resultado esperado.

### Regra 8: testes minimos por alteracao

- `python -m pytest -q`
- `python -m pytest tests/test_web_api.py -q` quando a API mudar
- `python -m pytest tests/test_ontology.py tests/test_official_term_index.py -q`
  quando o escopo ontologico ou o indice mudarem
- Se nao for possivel rodar, registrar o motivo.

## Prioridade atual de desenvolvimento

Construir o painel de alvos fenotipicos, em incrementos pequenos:

1. Snapshot versionado de `phenotype.hpoa` (doenca -> fenotipo, com
   frequencia, idade de inicio, evidencia e referencia).
2. Consulta de perfil fenotipico por doenca, com proveniencia por linha.
3. Ligacao doenca -> gene -> variantes causativas.
4. Cobertura das variantes frente ao painel genotipado disponivel.
5. Revisao humana do painel na bancada existente.

Fora de escopo ate nova decisao do PO: novo modelo, LLM em runtime, RAG,
SNOMED CT, OMOP, Phenopacket, dados de paciente reais.

## Protocolo de retomada rapida

1. ler este `AGENTS.md`;
2. `git status --short`;
3. identificar em qual incremento da prioridade atual estamos;
4. executar apenas o proximo bloco pendente, com validacao;
5. registrar no historico.
