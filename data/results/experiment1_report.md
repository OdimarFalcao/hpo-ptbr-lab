# Experimento 1 — recuperação híbrida

## Status

Experimento exploratório concluído em 16/07/2026. O holdout contém 30 casos sintéticos aprovados cegamente por Odimar, com 10 HPO IDs inéditos em relação ao desenvolvimento. O método foi congelado no commit `61566d503c652efc43a86e4ed384c97e61f39b37` antes da execução única.

## Resultados no holdout

| Método | Accuracy@1 geral | Accuracy@5 geral | Accuracy@1 paráfrases | Accuracy@5 paráfrases | Accuracy@1 ortográfica | IDs inválidos |
|---|---:|---:|---:|---:|---:|---:|
| exact | 46,67% | 46,67% | 0,00% | 0,00% | 40,00% | 0,00% |
| fuzzy | 66,67% | 66,67% | 0,00% | 0,00% | 100,00% | 0,00% |
| BM25 | 56,67% | 63,33% | 10,00% | 10,00% | 60,00% | 0,00% |
| semantic | 46,67% | 56,67% | 10,00% | 10,00% | 30,00% | 0,00% |
| hybrid | 60,00% | 73,33% | 0,00% | 20,00% | 80,00% | 0,00% |

## Casos determinantes

- `formação de granulomas nos pulmões` recuperou `HP:0030250` na posição 3.
- `quantidade de macrófagos fora do intervalo esperado` recuperou `HP:0030326` na posição 5.
- `leuco coria` recuperou `HP:0000555` na posição 2, abaixo de `HP:0020075`.
- `glomerul osclerose` recuperou `HP:0000096` na posição 2, abaixo de `HP:0000362`.

## Decisão

O critério de promoção falhou. O híbrido superou os métodos individuais em Accuracy@5 nas paráfrases, manteve 100% nos rótulos oficiais e não gerou IDs inválidos, mas perdeu dois casos de Accuracy@1 ortográfica em relação ao fuzzy; o limite pré-registrado permitia perda de apenas um.

O método permanece fora do dashboard. Este holdout não será usado para alterar pesos, regras ou roteamento. Qualquer nova versão híbrida deverá ser definida no desenvolvimento e avaliada em um novo conjunto congelado.
