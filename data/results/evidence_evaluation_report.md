# Avaliação funcional da extração de evidências

Data da execução: 2026-07-17.

## Escopo

Esta é uma verificação funcional no conjunto de desenvolvimento demonstrativo. Os cinco textos foram construídos para exercitar a interface e já são conhecidos pelo desenvolvimento. Portanto, os resultados não medem generalização, não são holdout e não sustentam alegações clínicas ou comparação estatística.

O ouro sintético contém nove menções: oito marcadas como detectáveis pelo baseline lexical e uma paráfrase marcada previamente como falha conhecida.

## Resultado

| Métrica | Resultado |
|---|---:|
| Recall de trecho exato nas menções detectáveis | 100,00% (8/8) |
| Precisão dos trechos previstos | 100,00% (8/8) |
| HPO Accuracy@1 nas menções detectáveis | 100,00% (8/8) |
| HPO Accuracy@5 nas menções detectáveis | 100,00% (8/8) |
| Reprodução da falha conhecida | 100,00% (1/1 não detectada) |
| Taxa de HPO ID inválido | 0,00% |

Os oito acertos confirmam que o pipeline preserva offsets e associa candidatos válidos quando a expressão é lexicalmente próxima do rótulo português. A falha em “cabeça parece menor do que o esperado” confirma que a extração lexical ainda não resolve paráfrases clínicas.

## Artefatos

- Ouro sintético: `data/demo/synthetic_descriptions.json`.
- Detalhes por menção: `data/results/evidence_evaluation_details.csv`.
- Resumo legível por máquina: `data/results/evidence_evaluation_summary.json`.
- Execução: `python scripts/evaluate_evidence.py`.

O script usa somente os cinco textos sintéticos e não lê `data/eval/holdout_cases.csv`.
