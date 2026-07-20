# Otimização do detector de evidência textual

Data da medição: 2026-07-17.

Este documento preserva o benchmark histórico dos cinco casos originais. A interface atual usa o conjunto ampliado `data/demo/synthetic_review_cases.json`; os resultados funcionais correspondentes estão em `data/results/evidence_evaluation_report.md`.

## Objetivo

Reduzir a latência da prova de conceito sem alterar o método científico: fuzzy WRatio, limiar `0.92`, desempate determinístico por HPO ID e candidatos provenientes do snapshot oficial.

## Alteração

A implementação inicial chamava o `FuzzyMapper` para cada janela do texto. Isso executava o scorer em Python sobre os 7.158 rótulos portugueses repetidamente. A versão otimizada usa `rapidfuzz.process.extractOne`, da mesma dependência e com o mesmo scorer, sobre rótulos previamente ordenados por HPO ID.

## Medição controlada

Foram executados os cinco textos de `data/demo/synthetic_descriptions.json` uma vez, no mesmo ambiente local, com `top_k=5`. Os tempos incluem detecção e ordenação dos candidatos.

| Caso | Antes (ms) | Depois (ms) |
|---|---:|---:|
| demo-01 | 1083.486 | 183.042 |
| demo-02 | 857.342 | 165.856 |
| demo-03 | 1713.280 | 203.502 |
| demo-04 | 2782.598 | 209.178 |
| demo-05 | 2261.536 | 73.342 |
| Mediana | 1713.280 | 183.042 |
| Média | 1739.648 | 166.984 |

A redução da mediana foi de aproximadamente 89,3%. Os trechos detectados e os HPO IDs de primeira posição permaneceram iguais nos cinco casos. Latência depende do hardware e da carga do sistema; os valores não constituem métrica de validade clínica.

A validação visual em uma instância Streamlit isolada retornou o `demo-01` em 196,113 ms, preservando os dois trechos, offsets, candidatos e exportação JSON. Duas instâncias antigas presas à mesma porta foram descartadas antes dessa verificação para evitar medir código obsoleto.

## Reprodução da versão atual

```powershell
python scripts/benchmark_evidence.py --runs 3
```

O benchmark usa somente os exemplos sintéticos versionados e não acessa o holdout.
