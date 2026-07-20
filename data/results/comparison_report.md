# Resultados consolidados — HPO-PTBR Lab

Gerado automaticamente por `python scripts/build_comparison_report.py`.

## Snapshot e cobertura

- Versão: `hpo-2026-06-23_pt-62f1d254`.
- Termos HPO ativos: 19.836.
- Rótulos portugueses: 7.158.
- Cobertura de rótulos: 36,09%.

## Desenvolvimento exploratório

Os 30 casos já influenciaram decisões e não medem generalização.

| Método | Acc@1 geral | Acc@5 geral | Acc@1 paráfrases | Acc@5 paráfrases |
|---|---:|---:|---:|---:|
| exact | 56,67% | 56,67% | 0,00% | 0,00% |
| fuzzy | 66,67% | 66,67% | 0,00% | 0,00% |
| bm25 | 60,00% | 63,33% | 0,00% | 10,00% |
| semantic | 40,00% | 60,00% | 10,00% | 20,00% |
| hybrid | 66,67% | 73,33% | 0,00% | 20,00% |

## Holdout congelado

Execução única. Estes resultados não devem ser reutilizados para ajuste.

| Método | Acc@1 geral | Acc@5 geral | Acc@1 paráfrases | Acc@5 paráfrases |
|---|---:|---:|---:|---:|
| exact | 46,67% | 46,67% | 0,00% | 0,00% |
| fuzzy | 66,67% | 66,67% | 0,00% | 0,00% |
| bm25 | 56,67% | 63,33% | 10,00% | 10,00% |
| semantic | 46,67% | 56,67% | 10,00% | 10,00% |
| hybrid | 60,00% | 73,33% | 0,00% | 20,00% |

## Critério de promoção do híbrido

- Paráfrases Acc@5: híbrido 20,00%; melhor individual 10,00%.
- Rótulos oficiais Acc@1 do híbrido: 100,00%.
- Variações ortográficas Acc@1: híbrido 80,00%; fuzzy 100,00%.
- Decisão: não promover. O híbrido perdeu dois casos ortográficos, acima do limite pré-registrado de um.

## Sanity check da descrição sintética

- Casos: 10; menções detectáveis: 25; falha conhecida: 5.
- Recall de trecho exato: 96,00%; HPO Acc@1: 96,00%; IDs inválidos: 0,00%.
- Escopo: verificação funcional construída no desenvolvimento; não é benchmark, holdout ou evidência clínica.

## Separação obrigatória

| Bloco | Pode ajustar? | Uso correto |
|---|---|---|
| Desenvolvimento exploratório | Sim | Construção e diagnóstico de métodos |
| Holdout congelado | Não | Avaliação única da sprint |
| Sanity check sintético | Sim | Verificação funcional da interface |
