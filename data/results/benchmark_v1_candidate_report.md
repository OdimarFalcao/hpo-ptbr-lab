# Benchmark V1 — candidatos no desenvolvimento

## Matriz controlada

| Configuração | F1 ponta a ponta | Recall paráfrases | F1 span | Macro-F1 contexto | FP controles | IDs inválidos |
|---|---:|---:|---:|---:|---:|---:|
| fuzzy_always_present | 50.79% | 0.00% | 73.02% | 20.00% | 0.00% | 0.00% |
| fuzzy_context_cues | 69.84% | 0.00% | 73.02% | 95.92% | 0.00% | 0.00% |
| semantic_context_cues | 74.29% | 33.33% | 77.14% | 95.92% | 50.00% | 0.00% |
| hybrid_context_cues | 77.14% | 33.33% | 80.00% | 95.92% | 50.00% | 0.00% |

## Gates

- `assertion_candidate`: APROVADO.
  - assertion_macro_f1: 0.9592 gt 0.2 — ok.
  - present_assertion_accuracy: 1.0 gte 1.0 — ok.
- `semantic_detection_component`: REPROVADO.
  - paraphrase_exact_span_recall: 0.3333 gt 0.0 — ok.
  - official_exact_span_recall: 1.0 gte 0.9167 — ok.
  - orthographic_exact_span_recall: 0.9167 gte 0.8333 — ok.
  - negative_control_false_positive_rate: 0.5 lte 0.0 — falhou.
  - invalid_hpo_id_rate: 0.0 lte 0.0 — ok.
- `combined_candidate`: REPROVADO.
  - overall_end_to_end_exact_f1: 0.7714 gt 0.5079 — ok.
  - paraphrase_end_to_end_recall: 0.3333 gt 0.0 — ok.
  - official_end_to_end_recall: 1.0 gte 0.75 — ok.
  - negative_control_false_positive_rate: 0.5 lte 0.0 — falhou.
  - invalid_hpo_id_rate: 0.0 lte 0.0 — ok.

## Análise de erros

- O contexto acertou 35/36 menções. A única falha foi `hipoventilacao`: esperado `uncertain`, previsto `present`. A pista ‘como possibilidade’ aparece depois da menção e ficou fora do escopo pré-registrado à esquerda.
- O detector semântico localizou exatamente 4/12 paráfrases: `retina deslocada` (HP:0000541), `ruídos respiratórios fora do padrão` (HP:0030829), `inflamação persistente do pâncreas` (HP:0006280), `perda completa do olfato` (HP:0000458).
- O mesmo detector perdeu 8/12 paráfrases.
- O gate semântico falhou porque DEV-CTRL-01 produziu o trecho espúrio `achados fenotípicos` → `HP:0000118`. A taxa foi 1/2 controles, ou 50%.
- Previsões sem span ouro: fuzzy+contexto 4, semântico+contexto 7 e híbrido+contexto 6.
- Nenhuma configuração retornou HPO ID inválido.

## Limites de interpretação

O classificador de contexto foi especificado depois da inspeção dos textos sintéticos e pode refletir seus templates. O SapBERT e seus parâmetros vieram de experimento anterior e foram congelados antes desta execução. O resultado pertence somente ao desenvolvimento, não utiliza holdout e não demonstra validade clínica ou generalização.

Aprovação em desenvolvimento não promove automaticamente qualquer método ao dashboard.
