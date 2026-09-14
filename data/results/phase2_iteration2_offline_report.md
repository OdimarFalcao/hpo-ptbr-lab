# Fase 2 — Iteração 2 offline

## Escopo

Avaliação de linking em nove trechos-ouro sintéticos de desenvolvimento. A aplicação, validação e holdout não foram alterados nem executados.

## Resultados

| Método | Acc@1 | Acc@5 | MRR@5 | Sem PT recuperados@5 |
|---|---:|---:|---:|---:|
| `baseline_pt_fuzzy` | 0.0% | 0.0% | 0.0% | 0/4 |
| `official_terms_exact` | 0.0% | 0.0% | 0.0% | 0/4 |
| `official_terms_fuzzy` | 0.0% | 0.0% | 0.0% | 0/4 |
| `official_terms_bm25` | 0.0% | 0.0% | 0.0% | 0/4 |
| `official_terms_sapbert` | 0.0% | 11.1% | 3.7% | 0/4 |

## Controle de falsos positivos

O detector congelado produziu 0 spans nos onze casos e 0/2 controles negativos com falso positivo. O linking em span-ouro não é um detector e não possui taxa própria de falso positivo.

## Decisão

Status: `do_not_integrate`.

Nenhum candidato satisfez simultaneamente os critérios exploratórios; não há justificativa para integração.

Mesmo um ganho neste desenvolvimento pequeno não demonstra generalização ou segurança clínica. Nenhuma alteração foi integrada à API ou ao frontend.
