# HPO-PTBR Lab

Projeto acadêmico de agente especializado em ontologia clínica no Brasil. A bancada atual implementa o módulo inicial de construção e revisão de perfil fenotípico em português; não é o agente completo nem o produto final.

## Visão da pesquisa

O objetivo global é desenvolver um agente de conhecimento especializado em problemas de ontologia clínica no contexto brasileiro. O agente deverá receber descrições clínicas em português, identificar conceitos, reduzir ambiguidades terminológicas, consultar ontologias e apresentar resultados rastreáveis com evidências para revisão profissional.

Fluxo conceitual:

```text
descrição clínica em português
→ extração de conceitos e contexto
→ normalização semântica
→ mapeamento HPO e consulta a ontologias
→ evidências e alternativas
→ apoio à priorização de hipóteses genéticas
→ revisão humana
```

O HPO-PTBR Lab implementa e avalia o primeiro núcleo desse agente: `texto PT-BR → menções fenotípicas → HPO válido`. SNOMED CT, OMOP CDM, RAG com literatura, Phenopackets e priorização genética pertencem às fases posteriores e não devem ser apresentados como funcionalidades atuais. O agente será de apoio ao conhecimento e à decisão; não emitirá diagnóstico autônomo.

## O que entrega

### Visão e planejamento do agente

HPO é infraestrutura semântica, não produto final. A direção global inclui investigação genética assistida com hipóteses priorizadas, evidências e referências, sem diagnóstico autônomo. O planejamento atual está separado dos protocolos experimentais e não altera seus resultados:

- [Visão canônica e origem na reunião de 28/05/2026](docs/AGENTE.md).
- [Arquitetura alvo e módulos realmente existentes](docs/ARQUITETURA_AGENTE.md).
- [Roadmap incremental](docs/ROADMAP_AGENTE.md).
- [Plano de avaliação do agente](docs/AVALIACAO_AGENTE.md).
- [Fase 2: linguagem clínica natural e avaliação](docs/FASE_2_LINGUAGEM_E_AVALIACAO.md).
- [Decisões e pendências](docs/DECISOES_AGENTE.md).

### Módulo atual

- Snapshot versionado da HPO `2026-06-23` e da tradução portuguesa.
- Análise de cobertura dos rótulos em português.
- Três baselines reproduzíveis: exact match, fuzzy match e BM25.
- Baseline semântico offline experimental, isolado do dashboard.
- Piloto técnico com 30 expressões públicas/sintéticas.
- Dashboard Streamlit com cobertura, mapeador, bancada de anotação assistida, resultados e roadmap.

### Fase 1 — núcleo do perfil fenotípico

A bancada web implementa a construção e revisão local de um perfil por fenótipo: trecho original, HPO selecionado, contexto, origem automática/manual, método de recuperação, decisão humana, caracterização e pendências. Idade/início, gravidade, evolução, frequência, lateralidade e histórico familiar podem ser registrados; campos vazios continuam explicitamente pendentes. Toda alteração exige nova confirmação antes da exportação.

O detector lexical e os rankers Exact, Fuzzy e BM25 foram preservados. A busca manual amplia a consulta com rótulos e sinônimos oficiais do snapshot HPO e mostra idioma e fonte. O snapshot português atual possui rótulos oficiais, mas não fornece sinônimos portugueses; portanto, resultados ingleses são marcados como tais e termos sem rótulo PT não são apresentados como traduções validadas. Nenhum dataset oficial foi alterado.

### Fase 2 — desenvolvimento técnico implementado

A Fase 2 corrige uma limitação metodológica dos testes antigos: descrições que repetem o rótulo HPO esperado verificam o pipeline, mas favorecem correspondência lexical e não demonstram fluidez clínica. Foram adicionados baseline congelado, [rubrica](docs/FASE_2_RUBRICA_ANOTACAO.md), protocolo, onze casos sintéticos de desenvolvimento sem rótulo literal como pista principal, executor e análise de erros. O resultado foi negativo para extração e ranking de paráfrases e está registrado sem exagero em `data/results/phase2_development_report.md`.

Validação e holdout continuam sem casos no repositório e dependem de autoria independente e revisão clínica. Não foi adicionado modelo, tradução não oficial, prontuário real, telemetria ou gate aprovado.

Na primeira iteração corretiva, sugestões e exportações foram limitadas a descendentes de `HP:0000118`, sem a raiz. Isso eliminou falsos fenótipos como `Começo`, mas não melhorou o recall em linguagem natural. O resultado negativo permanece registrado em `data/results/phase2_iteration1_scope_filter.json`.

Na segunda iteração, um índice exclusivamente offline passou a representar os 19.119 fenótipos com rótulos oficiais PT, rótulos oficiais EN e sinônimos exatos EN, sempre com idioma, fonte e versão. Os 12.139 conceitos sem rótulo PT são marcados como `unavailable`; nenhuma tradução foi criada. Em nove trechos-ouro, Exact, Fuzzy e BM25 recuperaram 0/9 alvos no Top-5 e o SapBERT local recuperou 1/9, mas 0/4 entre os conceitos sem PT. O candidato reprovou a regra pré-registrada e não foi integrado à aplicação. Protocolo e relatório: `data/protocol/phase2_iteration2_offline_protocol.json` e `data/results/phase2_iteration2_offline_report.md`.

Para reproduzir a Iteração 2 com o modelo já presente no cache local:

```powershell
python scripts/run_phase2_iteration2_offline.py
```

Para reproduzir somente o desenvolvimento:

```powershell
python scripts/run_phase2_development.py
```

## Limites

Este projeto não realiza diagnóstico, não processa prontuários e não usa dados clínicos reais. SNOMED CT e OMOP fazem parte da arquitetura futura, mas não são simulados nesta versão. Nenhum conteúdo SNOMED é redistribuído.

## Fechamento do V1

Em agosto de 2026 iniciou-se uma sprint de sete dias para fechar o V1 acadêmico. O primeiro incremento é um novo benchmark sintético que separa detecção de menções, linking HPO e contexto da menção. Seus conceitos serão inéditos em relação a todos os conjuntos já avaliados, e o novo holdout só poderá ser executado depois do congelamento do método.

- Sprint: `docs/sprint_v1_7_days.md`
- Protocolo científico: `docs/benchmark_v1_protocol.md`
- Especificação executável: `data/protocol/benchmark_v1_protocol.json`
- Aprendizado aplicado de TI: `docs/learning_by_doing.md`

O desenvolvimento do benchmark possui 20 descrições sintéticas e 36 HPO IDs inéditos, distribuídos igualmente entre nove domínios. Após revisão técnica cega contra o `hp.json` oficial e confirmação humana para uso exploratório, o baseline de desenvolvimento foi executado sem selecionar ou consultar o novo holdout.

O fuzzy obteve F1 ponta a ponta geral de 50,79%. Os três métodos lexicais tiveram 0% de recall de detecção nas 12 paráfrases. A avaliação também mostrou por que accuracy isolada pode enganar: o contexto atingiu 66,67% de accuracy, mas apenas 20,00% de macro-F1, pois o baseline `always_present` errou todas as negações, incertezas e menções familiares.

Para regenerar o desenvolvimento, revisar, confirmar e executar novamente o baseline:

```powershell
python scripts/prepare_benchmark_v1_development.py
python scripts/review_benchmark_v1_development.py
python scripts/confirm_benchmark_v1_development.py
python scripts/run_benchmark_v1_development.py
python scripts/run_benchmark_v1_candidates.py
```

Relatório: `data/results/benchmark_v1_development_report.md`.

### Candidatos V1 no desenvolvimento

Uma matriz pré-registrada separou o efeito do contexto e da detecção semântica. As regras de contexto em português elevaram o macro-F1 de 20,00% para 95,92% e passaram o gate exploratório, com uma falha em 36 menções. Esse valor pode refletir os templates sintéticos já inspecionados e ainda precisa de avaliação em casos inéditos.

O SapBERT com aliases oficiais recuperou exatamente 4/12 paráfrases. A união lexical-semântica elevou o F1 ponta a ponta para 77,14%, contra 50,79% do fuzzy original. Porém, ambos produziram um falso positivo em um dos dois controles negativos (`achados fenotípicos` → `HP:0000118`), taxa de 50%. O componente semântico e o híbrido reprovaram seus gates e permanecem fora do dashboard. Nenhum HPO ID inválido foi retornado e o holdout não foi utilizado.

Duas execuções produziram os mesmos detalhes, previsões, gates, erros, metadados, relatório e métricas depois de remover somente os campos de latência.

- Pré-registro: `data/protocol/benchmark_v1_candidate_protocol.json`
- Relatório: `data/results/benchmark_v1_candidate_report.md`
- Análise de erros: `data/results/benchmark_v1_candidate_error_analysis.json`

## Instalação

### Nova bancada web (React + FastAPI)

Interface principal em português, com revisão explícita, correções manuais, conceitos oficiais e exportação. Streamlit continua disponível como área de pesquisa. As duas interfaces usam o mesmo núcleo científico; a nova interface não melhora por si só as métricas de detecção.

```powershell
cd C:\dev\hpo-ptbr-lab
.\.venv\Scripts\python.exe -m pip install -r requirements-web.txt
cd web
npm ci
npm run build
cd ..
.\.venv\Scripts\python.exe scripts/run_web.py
```

Abra `http://127.0.0.1:8000` para a bancada e `http://127.0.0.1:8504` para pesquisa. Mantenha o terminal aberto; **Ctrl+C** encerra apenas os servidores iniciados pelo comando. Se o Streamlit já estiver aberto separadamente, use `--without-research`. Nenhum processo existente é encerrado automaticamente.

Node 22 LTS é recomendado; o build também foi exercitado com Node 18.20.8 neste ambiente. O `package-lock.json` fixa as dependências do frontend. Não é necessário instalar modelos semânticos para usar a bancada. Revisões ficam apenas em memória e no JSON baixado explicitamente. Não inserir prontuários nem dados pessoais.

Detalhes da arquitetura, contratos, privacidade e validação: `docs/web_workbench.md`.

### Streamlit de referência

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

`requirements.txt` contém apenas o necessário para o dashboard. `requirements-semantic.txt` isola o modelo offline e é incluído por `requirements-dev.txt`.

## Reproduzir os dados

Baixe os dois arquivos oficiais para `data/raw/`:

- `hp.json`: `https://github.com/obophenotype/human-phenotype-ontology/releases/latest/download/hp.json`
- `hp-pt.babelon.tsv`: `https://raw.githubusercontent.com/obophenotype/hpo-translations/main/babelon/hp-pt.babelon.tsv`

Depois execute:

```powershell
python scripts/build_snapshot.py
python scripts/build_ontology_index.py
python scripts/run_evaluation.py
python scripts/run_semantic_evaluation.py
python scripts/create_notebook.py
```

O snapshot processado e os resultados usados pelo dashboard já estão versionados. Os arquivos brutos ficam fora do Git.

## Experimento semântico offline

O primeiro baseline semântico usa o modelo multilíngue `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, fixado por revisão, para comparar cada consulta com os 7.158 rótulos HPO em português. Ele permanece fora do mapeador Streamlit enquanto sua utilidade não estiver demonstrada.

No piloto atual, obteve Accuracy@1 de 40,00% no geral e 10,00% nas paráfrases clínicas. Em Accuracy@5, obteve 60,00% no geral e 20,00% nas paráfrases. O ganho semântico nas paráfrases foi pequeno e veio acompanhado de queda acentuada nas variações ortográficas; portanto, este modelo isolado não substitui os baselines lexicais.

Os resultados e a proveniência ficam em `data/results/semantic_*`.

## Protocolo do Experimento 1

Os 30 casos de `data/eval/pilot_cases.csv` são o conjunto de desenvolvimento exploratório. O holdout usa dez HPO IDs inéditos, foi aprovado cegamente por Odimar e está congelado em `data/eval/holdout_cases.csv`, com checksum e proveniência em `data/eval/holdout_manifest.json`.

Fluxo operacional:

```powershell
# Desenvolvimento: pode ser repetido
python scripts/run_experiment1.py --dataset development

# Se Odimar rejeitar um conceito após registrar o motivo no CSV
python scripts/replace_rejected_holdout.py

# Somente depois de todos os status serem "approved"
python scripts/freeze_holdout.py

# Execução única, apenas com Git limpo e holdout congelado
python scripts/run_experiment1.py --dataset holdout --confirm-holdout
```

O híbrido usa short-circuit exato e Reciprocal Rank Fusion sem pesos (`k=60`) sobre os Top-20 de fuzzy, BM25 e semantic. O score de fusão não é confiança calibrada.

No desenvolvimento, o híbrido obteve Accuracy@1 geral de 66,67%, Accuracy@5 geral de 73,33% e Accuracy@5 de 20,00% nas paráfrases. Ele empatou com o melhor método individual nas paráfrases.

No holdout congelado, o híbrido obteve Accuracy@1 geral de 60,00%, Accuracy@5 geral de 73,33% e Accuracy@5 de 20,00% nas paráfrases. Superou os métodos individuais nas paráfrases, mas caiu para 80,00% de Accuracy@1 ortográfica contra 100,00% do fuzzy. Como o limite pré-registrado permitia queda de apenas um caso, o critério de promoção falhou. O híbrido permanece fora do dashboard e o holdout não deve ser reutilizado para ajuste.

A análise completa está em `data/results/experiment1_report.md`.

A consolidação automática que separa Experimento 0, desenvolvimento do Experimento 1, holdout congelado e sanity check sintético fica em `data/results/comparison_report.md`. Para regenerar:

```powershell
python scripts/build_comparison_report.py
```

## Bancada de anotação assistida

A página `Anotação assistida` recebe um texto inventado, destaca evidências lexicais e organiza candidatos HPO para revisão humana. O usuário pode incluir uma menção omitida, corrigir limites por sobreposição, descartar falsos positivos, escolher contexto e caracterização, pesquisar outro HPO por rótulo, sinônimo oficial ou ID e exportar o perfil no formato experimental `hpo-ptbr-review-v1`. As alterações ficam somente na sessão e no JSON baixado; não há banco nem persistência de texto.

Cada conceito selecionado apresenta os rótulos oficiais disponíveis, definição, sinônimos, pais, filhos e um caminho determinístico até `HP:0000118`. Esses dados são derivados do mesmo snapshot oficial em `data/processed/hpo_ontology.json.gz`. Referências cruzadas SNOMED CT não são incluídas no índice nem exibidas na aplicação.

Exact, fuzzy e BM25 são comparados separadamente em cada trecho. O SapBERT pode ser carregado explicitamente do cache local para comparar candidatos de um trecho já selecionado; ele não participa da detecção padrão e sua ausência não impede o funcionamento do dashboard. Scores continuam sendo scores de ranking, não confiança calibrada.

Os dez cenários multissistêmicos ficam em `data/demo/synthetic_review_cases.json`; nenhum de seus IDs pertence ao holdout. O fluxo e os conceitos para estudo estão descritos em `docs/workbench_v1.md`.

O detector usa fuzzy match com limiar fixo de `0.92`; o método escolhido pelo usuário apenas ordena os candidatos de cada trecho detectado. `detector_score` e `score` são scores de ranking, não confiança calibrada. Essa prova de conceito pode omitir paráfrases clínicas, não processa prontuários e não altera os resultados do holdout congelado.

A busca do melhor rótulo por janela usa `rapidfuzz.process.extractOne` com desempate determinístico por HPO ID. A medição local controlada dos cinco exemplos reduziu a mediana observada de 1.713,280 ms para 183,042 ms sem alterar os trechos ou IDs retornados. Valores brutos, metodologia e limitações estão em `data/results/evidence_performance.md`. Para medir a versão atual:

```powershell
python scripts/benchmark_evidence.py --runs 3
```

Os dez cenários possuem 30 menções com offsets e alvos HPO explícitos para uma verificação funcional reproduzível. O baseline recupera 24 das 25 menções lexicais esperadas, mantém cinco paráfrases como falhas conhecidas e retorna zero IDs inválidos. Esse resultado é um sanity check de desenvolvimento construído, não medida de generalização. Relatório em `data/results/evidence_evaluation_report.md` e execução por:

```powershell
python scripts/evaluate_evidence.py
```

### Experimento 2: detecção semântica de trechos

O próximo experimento troca a detecção exclusivamente lexical por janelas codificadas em lote e recuperação por similaridade semântica. O executor suporta o encoder genérico anterior e o `cambridgeltl/SapBERT-UMLS-2020AB-all-lang-from-XLMR`, especializado em *biomedical entity linking*. Modelo, revisão, limiar e uso exclusivo do desenvolvimento são registrados nos metadados; o holdout congelado não é lido.

```powershell
python scripts/run_semantic_evidence_experiment.py --encoder sapbert --threshold 0.8
```

O modelo é carregado apenas do cache local. O método permanece offline e fora do dashboard até demonstrar ganho mensurável em paráfrases sem aumento inaceitável de falsos positivos.

O baseline de detecção com o encoder genérico obteve recall exato de 66,67% (20/30), precisão de 43,48% (20/46), HPO Accuracy@1 de 63,33% e não recuperou nenhuma das cinco paráfrases críticas. O SapBERT elevou essas métricas para 83,33%, 96,15% e 83,33%, respectivamente. A fusão lexical + SapBERT chegou a 86,67% de recall, 92,86% de precisão e 86,67% de HPO Accuracy@1, mas ainda recuperou somente uma das cinco paráfrases críticas. Ambos permanecem fora do dashboard. Resultados e análise de erros em `data/results/semantic_evidence_experiment_report.md`.

Um índice SapBERT bilíngue com `label_pt` e `label_en` reproduziu exatamente as métricas e os erros do índice somente em português. A hipótese não trouxe ganho e também permanece offline.

O índice com aliases usa 8.921 sinônimos ingleses exatos do próprio snapshot HPO, cobrindo 4.085 dos 7.158 conceitos traduzidos. No desenvolvimento, obteve recall de trecho de 86,67%, precisão de 96,30%, HPO Accuracy@1 de 83,33% e Accuracy@5 de 86,67%. Ele recuperou “olhos desalinhados” no Top-5, mas não no Top-1, e não resolveu as demais paráfrases críticas. O resultado permanece offline e não altera o dashboard.

Uma ablação posterior impediu que janelas semânticas atravessassem vírgulas, ponto e vírgula, dois-pontos, pontos ou quebras de linha. O número de janelas caiu de 491 para 356 (−27,49%), mas acertos, erros e candidatos permaneceram iguais, enquanto a latência média observada subiu para 1.781,133 ms. A segmentação por pontuação também permanece offline.

O próximo experimento separa detecção de menções e linking HPO. O protocolo pré-registra um modelo NER português, decodificação BIOES, métricas exclusivas de offsets e critérios para avançar, sem baixar o modelo, ler o holdout ou alterar o dashboard nesta etapa. Consulte `docs/mention_detection_protocol.md`.

O candidato pré-registrado foi executado uma vez no desenvolvimento e reprovado: 112 fragmentos previstos, precisão/recall/F1 exatos de 0,00%, F1 relaxado de 11,27% e nenhuma das cinco paráfrases críticas recuperada exatamente. A fragmentação WordPiece foi preservada como resultado negativo; não houve regra posterior de junção, linking HPO, uso do holdout ou alteração do dashboard. Consulte `data/results/mention_detection_experiment_report.md`.

Um experimento posterior agregou probabilidades BIOES por grupo, reconstruiu palavras pelo `word_id` do tokenizer e impediu junções através de pontuação. A configuração foi especificada após um dry-run no próprio desenvolvimento e não estima generalização. Ela elevou o F1 exato para 65,57%, com precisão de 64,52%, recall de 66,67% e recuperação de 2/5 paráfrases críticas, mas reprovou os gates. O método permanece offline, sem linking HPO, sem holdout e fora do dashboard. Consulte `data/results/mention_detection_word_aggregation_report.md`.

```powershell
python scripts/build_aliases.py
python scripts/run_semantic_evidence_experiment.py --encoder alias-sapbert --threshold 0.8
python scripts/run_semantic_evidence_experiment.py --encoder boundary-alias-sapbert --threshold 0.8
```

## Executar

```powershell
streamlit run streamlit_app.py
```

Antes de publicar o dashboard:

```powershell
python scripts/check_dashboard_readiness.py
```

O workflow `.github/workflows/ci.yml` executa testes, verifica a prontidão do dashboard e confirma que a consolidação versionada foi regenerada antes de cada alteração na `main`.

## Testar

```powershell
pytest
```

## Dados e proveniência

As versões, URLs e somas SHA-256 ficam em `data/processed/metadata.json`. O piloto em `data/eval/pilot_cases.csv` é estratificado em rótulos oficiais, variações ortográficas e paráfrases clínicas sintéticas.

## Roadmap

A referência atual é o [roadmap do agente](docs/ROADMAP_AGENTE.md). O encadeamento abaixo é o esboço histórico de interoperabilidade, não uma dependência obrigatória entre cada etapa nem a arquitetura completa do agente:

`texto clínico PT-BR → SNOMED CT → OMOP CDM → HPO → Phenopacket → priorização genética`

SNOMED CT exigirá serviço terminológico e licenciamento adequados. OMOP usará vocabulários padronizados obtidos via Athena em ambiente controlado.
