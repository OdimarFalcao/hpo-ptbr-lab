# Avaliação funcional da extração de evidências

Data da execução: 2026-07-17.

## Escopo

Esta é uma verificação funcional no conjunto de desenvolvimento demonstrativo. Os dez textos foram construídos para exercitar a interface e já são conhecidos pelo desenvolvimento. Portanto, os resultados não medem generalização, não são holdout e não sustentam alegações clínicas ou comparação estatística.

O ouro sintético contém 30 menções em cenários neurológicos, renais, respiratórios, musculoesqueléticos, cardíacos, oculares, auditivos, dermatológicos e digestivos: 25 marcadas como detectáveis pelo baseline lexical e cinco paráfrases marcadas previamente como falhas conhecidas. Nenhum HPO ID pertence ao holdout congelado.

## Resultado

| Métrica | Resultado |
|---|---:|
| Recall de trecho exato nas menções detectáveis | 96,00% (24/25) |
| Precisão dos trechos previstos | 92,31% (24/26) |
| HPO Accuracy@1 nas menções detectáveis | 96,00% (24/25) |
| HPO Accuracy@5 nas menções detectáveis | 96,00% (24/25) |
| Reprodução das falhas conhecidas | 100,00% (5/5 não detectadas) |
| Taxa de HPO ID inválido | 0,00% |

Os 24 acertos confirmam que o pipeline preserva offsets e associa candidatos válidos quando a expressão é lexicalmente próxima do rótulo português. A variação “estrabizmo” não atingiu o trecho esperado, e as cinco paráfrases permaneceram sem correspondência. O resultado demonstra que ortografia não padronizada e linguagem clínica cotidiana ainda exigem revisão humana e recuperação semântica futura.

As duas previsões excedentes ocorreram no `caso-09`: “próxima” foi associada a `HP:0012840` (Proximal) dentro da paráfrase “fraqueza próxima ao tronco”, e “tosse” foi associada a `HP:0012735` (Tosse) dentro de “tosse persistente”. Elas contam como excedentes porque não coincidem com os offsets e alvos compostos definidos no ouro. Esse resultado evidencia uma limitação do conjunto anotado e do recorte lexical: uma sugestão pode ser plausível como conceito mais geral, mas ainda exigir decisão humana sobre especificidade e contexto.

## Artefatos

- Ouro sintético ampliado: `data/demo/synthetic_review_cases.json`.
- Detalhes por menção: `data/results/evidence_evaluation_details.csv`.
- Resumo legível por máquina: `data/results/evidence_evaluation_summary.json`.
- Execução: `python scripts/evaluate_evidence.py`.

O script usa somente os dez textos sintéticos e não lê `data/eval/holdout_cases.csv`.
