# Fase 2 — baseline em linguagem clínica natural

## Escopo

- Split executado: `development`.
- Dataset: `data/eval/phase2_development.json` (`8e9e11c130ce11fad924702c4448ee33058a53bad14d545186ac153b9aed17bd`).
- Baseline: `phase2-pre-improvement-2026-09-12`; hashes verificados antes da execução.
- Validação e holdout: não criados nem executados.
- Padrão-ouro: técnico e sintético, ainda sem validação clínica.

## Resultados medidos

| Dimensão | Métrica | Resultado |
|---|---|---:|
| Extração | F1 span exato | 0.0% |
| Extração | Recall relaxado | 0.0% |
| Normalização | Accuracy@1 em span ouro | 0.0% |
| Ranking | Accuracy@5 em span ouro | 0.0% |
| Contexto | Accuracy | 66.7% |
| Contexto | Macro-F1 | 44.2% |
| Pendências | Precisão dos campos marcados pendentes | 77.8% |
| Pendências | Recall dos campos realmente ausentes | 100.0% |
| Controles | Casos com falso positivo | 0.0% |
| Execução | Latência média por caso | 296.078 ms |

O baseline deixou de estruturar 12 valores de caracterização que estavam explícitos nos textos. O proxy computacional soma 33 componentes de correção. Tempo humano real: não medido.

## Erros observados

{
  "mention_not_detected": 8,
  "wrong_span": 1,
  "concept_too_generic": 0,
  "concept_too_specific": 0,
  "wrong_concept": 9,
  "context_error": 3,
  "paraphrase_failure": 9,
  "portuguese_coverage_failure": 4
}

As categorias podem se sobrepor: por exemplo, uma paráfrase não detectada também pode expor falta de cobertura portuguesa. Isso serve para localizar causas, não para somar uma taxa única.

## Recomendações derivadas dos erros

- Avaliar um detector de menções orientado a paráfrases, mantendo o baseline congelado para comparação.
- Ampliar cobertura lexical somente com sinônimos e paráfrases rastreáveis e submetidos a revisão.
- Expandir e testar separadamente as regras de incerteza e histórico familiar observadas nos erros.
- Encaminhar conceitos sem rótulo PT oficial para curadoria; não promovê-los a tradução validada automaticamente.

## Limites

Os resultados são exploratórios, pequenos e produzidos em desenvolvimento sintético. Não demonstram generalização, segurança clínica nem atingimento de limiar de aprovação. O proxy de revisão não substitui estudo com profissionais, e nenhuma tradução sintética foi tratada como oficial.
