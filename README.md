# HPO-PTBR Lab

Protótipo acadêmico para recuperar termos válidos da Human Phenotype Ontology a partir de expressões fenotípicas curtas em português brasileiro.

## O que entrega

- Snapshot versionado da HPO `2026-06-23` e da tradução portuguesa.
- Análise de cobertura dos rótulos em português.
- Três baselines reproduzíveis: exact match, fuzzy match e BM25.
- Baseline semântico offline experimental, isolado do dashboard.
- Piloto técnico com 30 expressões públicas/sintéticas.
- Dashboard Streamlit com cobertura, mapeador, descrição sintética, resultados e roadmap.

## Limites

Este projeto não realiza diagnóstico, não processa prontuários e não usa dados clínicos reais. SNOMED CT e OMOP fazem parte da arquitetura futura, mas não são simulados nesta versão. Nenhum conteúdo SNOMED é redistribuído.

## Instalação

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

## Prova de conceito com evidência textual

A página `Descrição sintética` recebe um texto inventado, destaca evidências lexicais e organiza candidatos HPO para revisão humana. O usuário pode selecionar um conceito, marcar a decisão como pendente, aceita, alternativa ou descartada e exportar a revisão em JSON. Os dez cenários multissistêmicos ficam em `data/demo/synthetic_review_cases.json`; nenhum de seus IDs pertence ao holdout.

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

`texto clínico PT-BR → SNOMED CT → OMOP CDM → HPO → Phenopacket → priorização genética`

SNOMED CT exigirá serviço terminológico e licenciamento adequados. OMOP usará vocabulários padronizados obtidos via Athena em ambiente controlado.
