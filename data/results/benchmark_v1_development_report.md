# Benchmark V1 — baseline de desenvolvimento

## Configuração

- Dataset: `data/eval/benchmark_v1_development.json`.
- Snapshot: `hpo-2026-06-23_pt-62f1d254`.
- Detector: janelas fuzzy, limiar 0,92 e máximo de cinco tokens.
- Rankers: exact, fuzzy e BM25.
- Contexto: baseline fixo `always_present`.
- Holdout: não utilizado.
- Scores dos rankers não são confiança calibrada.

## Resultados gerais

| Método | F1 ponta a ponta | F1 span exato | Linking A@1 | Linking A@5 | Macro-F1 contexto | FP controles | IDs inválidos | Latência média |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| exact | 31.75% | 73.02% | 47.22% | 47.22% | 20.00% | 0.00% | 0.00% | 402.639 ms |
| fuzzy | 50.79% | 73.02% | 66.67% | 66.67% | 20.00% | 0.00% | 0.00% | 618.549 ms |
| bm25 | 44.44% | 73.02% | 63.89% | 69.44% | 20.00% | 0.00% | 0.00% | 511.68 ms |

## Estratos de forma superficial

| Método | Estrato | N | Recall span | Linking A@1 | Linking A@5 | Recall ponta a ponta |
|---|---|---:|---:|---:|---:|---:|
| exact | clinical_paraphrase | 12 | 0.00% | 0.00% | 0.00% | 0.00% |
| exact | official_label | 12 | 100.00% | 100.00% | 100.00% | 75.00% |
| exact | orthographic_variation | 12 | 91.67% | 41.67% | 41.67% | 8.33% |
| fuzzy | clinical_paraphrase | 12 | 0.00% | 0.00% | 0.00% | 0.00% |
| fuzzy | official_label | 12 | 100.00% | 100.00% | 100.00% | 75.00% |
| fuzzy | orthographic_variation | 12 | 91.67% | 100.00% | 100.00% | 58.33% |
| bm25 | clinical_paraphrase | 12 | 0.00% | 16.67% | 33.33% | 0.00% |
| bm25 | official_label | 12 | 100.00% | 100.00% | 100.00% | 75.00% |
| bm25 | orthographic_variation | 12 | 91.67% | 75.00% | 75.00% | 41.67% |

## Estratos de contexto

| Método | Contexto | N | Accuracy contexto | Linking A@1 | Recall ponta a ponta |
|---|---|---:|---:|---:|---:|
| exact | absent | 4 | 0.00% | 75.00% | 0.00% |
| exact | family_history | 4 | 0.00% | 0.00% | 0.00% |
| exact | present | 24 | 100.00% | 41.67% | 41.67% |
| exact | uncertain | 4 | 0.00% | 100.00% | 0.00% |
| fuzzy | absent | 4 | 0.00% | 75.00% | 0.00% |
| fuzzy | family_history | 4 | 0.00% | 25.00% | 0.00% |
| fuzzy | present | 24 | 100.00% | 66.67% | 66.67% |
| fuzzy | uncertain | 4 | 0.00% | 100.00% | 0.00% |
| bm25 | absent | 4 | 0.00% | 75.00% | 0.00% |
| bm25 | family_history | 4 | 0.00% | 25.00% | 0.00% |
| bm25 | present | 24 | 100.00% | 62.50% | 58.33% |
| bm25 | uncertain | 4 | 0.00% | 100.00% | 0.00% |

## Análise de erros

- O detector lexical perdeu as 12 paráfrases clínicas e uma variação ortográfica: `nefro calcinose` (HP:0000121).
- Quando recebeu os spans ouro, fuzzy vinculou corretamente 12/12 rótulos oficiais e 12/12 variações ortográficas, mas 0/12 paráfrases.
- Com spans ouro, BM25 recuperou paráfrases em 16.67% no Top-1 e 33.33% no Top-5; a detecção automática dessas paráfrases permaneceu em 0%.
- O classificador `always_present` errou as quatro negações, quatro incertezas e quatro menções de histórico familiar.
- Nenhum método retornou HPO ID inválido ou produziu falso positivo nos dois controles negativos.

A separação entre detecção, linking e contexto mostra onde cada erro nasce. Melhorar somente o ranker não resolve as paráfrases enquanto o detector não localizar seus trechos; melhorar somente a detecção não resolve negação, incerteza e histórico familiar.

## Interpretação

A detecção e o linking são medidos separadamente para evitar atribuir ao ranker uma falha de span. O resultado ponta a ponta exige span exato, HPO Top-1 e contexto corretos. Como a aplicação atual não classifica negação, incerteza ou histórico familiar, o baseline prevê `present` para todas as menções; essa limitação foi registrada antes da execução e não será corrigida retroativamente neste resultado.

Os números pertencem ao desenvolvimento sintético e podem orientar engenharia e análise de erros. Eles não demonstram generalização, utilidade clínica ou superioridade estatística.
