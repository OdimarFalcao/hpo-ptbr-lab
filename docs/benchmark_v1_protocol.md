# Protocolo do benchmark PT-BR V1

## Pergunta de pesquisa

Quão bem um pipeline experimental consegue localizar expressões fenotípicas em descrições sintéticas em português, vincular essas expressões a IDs HPO válidos e distinguir o contexto em que foram mencionadas?

## Escopo

O benchmark é exploratório e serve ao fechamento do V1. Ele não mede validade clínica, não usa prontuários e não sustenta alegações diagnósticas ou de superioridade estatística.

Serão avaliadas três tarefas separadas:

1. detecção do trecho textual;
2. normalização para HPO;
3. classificação do contexto da menção.

Também será calculado um resultado ponta a ponta que exige acerto simultâneo das três tarefas.

## Dados

- Snapshot obrigatório: `hpo-2026-06-23_pt-62f1d254`.
- Origem: dados públicos e descrições totalmente sintéticas.
- Total planejado: 30 descrições, sendo 20 de desenvolvimento e 10 de holdout.
- Total planejado: 54 menções, sendo 36 de desenvolvimento e 18 de holdout, todas com HPO IDs distintos.
- Controles negativos: três descrições sem menção fenotípica anotável.
- Domínios mínimos: neurologia, oftalmologia, musculoesquelético, cardiovascular, respiratório, renal/urinário, dermatologia, gastrointestinal e audição/otorrinolaringologia.

Nenhum dos 54 IDs poderá aparecer em `pilot_cases.csv`, `holdout_cases.csv` ou `synthetic_review_cases.json`. Os IDs do desenvolvimento e do holdout também serão disjuntos.

## Estratificação

As 54 menções serão balanceadas por forma superficial:

- 18 rótulos oficiais;
- 18 variações ortográficas ou abreviações controladas;
- 18 paráfrases clínicas sintéticas.

No desenvolvimento serão quatro conceitos por domínio; no holdout futuro, dois por domínio. Essa distribuição reduz a concentração em poucos fenótipos ou especialidades.

Contextos planejados:

- 36 menções presentes;
- seis negadas;
- seis incertas;
- seis em histórico familiar.

Cada descrição fenotípica terá pelo menos uma menção. Casos marcados como controle negativo não terão menções.

## Esquema de anotação

Cada caso conterá:

- identificador estável;
- split;
- domínio;
- tipo de caso;
- texto sintético;
- lista de menções.

Cada menção conterá:

- texto exato;
- offsets `start` e `end` no padrão `[start, end)`;
- HPO ID;
- contexto: `present`, `absent`, `uncertain` ou `family_history`;
- forma superficial: `official_label`, `orthographic_variation` ou `clinical_paraphrase`.

O validador rejeitará offsets inconsistentes, IDs ausentes no snapshot, IDs já utilizados, conceitos repetidos, spans sobrepostos, splits inválidos e controles negativos com menções.

## Congelamento

1. Selecionar e gerar somente os 36 conceitos do desenvolvimento e uma folha cega para revisão.
2. Revisar texto, offsets e vínculo conceitual sem consultar saída dos métodos.
3. Corrigir apenas erros de anotação documentados.
4. Fixar o método e registrar o commit.
5. Somente depois do commit do método, selecionar e gerar os 18 conceitos do holdout com IDs inéditos.
6. Registrar SHA-256, snapshot, IDs, exclusões e distribuição.
7. Executar o holdout uma única vez.

O holdout antigo permanece consumido e não será usado para seleção, ajuste ou comparação do novo método.

## Métricas

Métrica primária:

- F1 exato ponta a ponta, exigindo span, HPO Top-1 e contexto corretos.

Métricas secundárias:

- precisão, recall e F1 de span exato;
- F1 relaxado com IoU ≥ 0,5;
- Accuracy@1, Accuracy@5 e MRR@20 do linking;
- macro-F1 do contexto;
- taxa de HPO ID inválido;
- taxa de falsos positivos nos controles negativos;
- latência média;
- métricas por domínio, forma superficial e contexto.

## Gate para integração

Um método candidato só poderá substituir ou complementar o detector atual no dashboard se:

- superar o baseline lexical no F1 ponta a ponta das paráfrases;
- não perder mais de um caso de rótulo oficial em relação ao baseline;
- reduzir ou manter falsos positivos nos controles negativos;
- retornar zero HPO IDs inválidos;
- manter execução determinística sob a mesma configuração.

O gate é relativo porque os valores absolutos ainda serão medidos no novo desenvolvimento. Falhar no gate produz um resultado negativo documentado e não autoriza ajuste sobre o holdout.

## Limitações

- O conjunto é pequeno e sintético.
- Não há validação por profissional de saúde nesta sprint.
- Contextos clínicos serão simplificados para anotação controlada.
- O benchmark não representa prontuários, prevalência ou distribuição clínica real.
- SNOMED CT, OMOP e priorização genética permanecem fora desta avaliação.

## Estado do desenvolvimento — 24/08/2026

O rascunho de desenvolvimento foi gerado sem executar nenhum método de recuperação:

- 20 descrições, incluindo dois controles negativos;
- 36 HPO IDs inéditos e disjuntos dos conjuntos anteriores;
- quatro conceitos em cada um dos nove domínios;
- 12 rótulos oficiais, 12 variações controladas e 12 paráfrases;
- 24 menções presentes e quatro em cada contexto não afirmativo;
- offsets e IDs validados automaticamente.

Arquivos:

- dataset: `data/eval/benchmark_v1_development.json`;
- revisão cega: `data/eval/benchmark_v1_development_review.csv`;
- manifesto e hashes: `data/eval/benchmark_v1_development_manifest.json`;
- plano de seleção: `data/protocol/benchmark_v1_development_plan.json`.

Uma revisão técnica cega foi concluída com base nos rótulos, definições e sinônimos do `hp.json` oficial, cujo SHA-256 foi conferido contra os metadados do snapshot. Nenhum ranking ou método foi executado.

- 36 decisões técnicas registradas;
- 12 paráfrases confrontadas com a fonte oficial;
- uma correção: “pele mais clara de forma difusa” foi substituída por “pigmentação cutânea reduzida de forma generalizada” para evitar confusão com palidez;
- templates de contexto foram diversificados para reduzir repetição textual;
- dataset, revisão, log e manifesto são reproduzíveis byte a byte.

Odimar confirmou o conjunto para avaliação de desenvolvimento em 24/08/2026. Essa confirmação autoriza o uso exploratório do desenvolvimento, mas não constitui validação clínica nem autoriza o holdout.

Log de auditoria: `data/eval/benchmark_v1_development_review_log.json`.

## Baseline de desenvolvimento — 24/08/2026

O protocolo do baseline foi registrado com o SHA-256 do dataset antes da execução. Foram comparados exact, fuzzy e BM25 com o mesmo detector de janelas lexicais e o contexto fixo `always_present`.

Principais resultados:

- fuzzy obteve o melhor F1 ponta a ponta geral: 50,79%;
- todos os métodos tiveram 0% de recall de detecção nas 12 paráfrases;
- com spans ouro, fuzzy atingiu 100% de Accuracy@1 em rótulos oficiais e variações ortográficas, mas 0% em paráfrases;
- com spans ouro, BM25 recuperou 16,67% das paráfrases no Top-1 e 33,33% no Top-5;
- a accuracy de contexto foi 66,67%, mas o macro-F1 foi apenas 20%, porque `always_present` errou todas as negações, incertezas e menções familiares;
- não houve HPO IDs inválidos nem falsos positivos nos controles negativos.

O resultado confirma que há dois problemas técnicos independentes para o próximo incremento: detecção semântica de paráfrases e classificação do contexto da menção. O holdout permanece não selecionado e não executado.

Relatório: `data/results/benchmark_v1_development_report.md`.
Análise estruturada: `data/results/benchmark_v1_development_error_analysis.json`.

## Candidatos pré-registrados — 24/08/2026

Antes de executar novos métodos no desenvolvimento, foi congelada uma matriz que separa o efeito de contexto do efeito de detecção:

1. fuzzy com `always_present`, reutilizando o baseline;
2. fuzzy com regras gerais de contexto em português;
3. SapBERT com aliases oficiais e fronteiras de sentença, mais regras de contexto;
4. união lexical-semântica, mais regras de contexto.

O candidato semântico reutiliza modelo, revisão, hash, aliases, limiar 0,8 e máximo de seis tokens já definidos em julho; nenhum parâmetro foi escolhido a partir dos resultados do novo benchmark. O classificador de contexto usa escopo limitado à sentença e prioridade fixa para histórico familiar, incerteza, ausência e presença.

Como os textos sintéticos já foram inspecionados, o resultado de contexto pode refletir os templates controlados e não demonstrará generalização. Os critérios de avanço exigem ganho nas paráfrases, preservação dos rótulos oficiais, zero falsos positivos nos controles e zero IDs inválidos. Mesmo se aprovado no desenvolvimento, o método não será promovido automaticamente nem autorizará o holdout.

Especificação congelada: `data/protocol/benchmark_v1_candidate_protocol.json`.

## Resultado dos candidatos — 24/08/2026

A matriz foi executada somente no desenvolvimento, sem selecionar ou consultar o novo holdout:

| Configuração | F1 ponta a ponta | Recall exato em paráfrases | Macro-F1 contexto | FP nos controles |
|---|---:|---:|---:|---:|
| fuzzy + `always_present` | 50,79% | 0,00% | 20,00% | 0,00% |
| fuzzy + contexto | 69,84% | 0,00% | 95,92% | 0,00% |
| SapBERT aliases + contexto | 74,29% | 33,33% | 95,92% | 50,00% |
| união lexical-semântica + contexto | 77,14% | 33,33% | 95,92% | 50,00% |

Decisões dos gates:

- classificador de contexto: aprovado no desenvolvimento, com 35/36 acertos;
- componente de detecção semântica: reprovado por falso positivo em um dos dois controles;
- candidato combinado: reprovado pelo mesmo motivo, apesar do ganho de F1 e da recuperação de 4/12 paráfrases;
- zero HPO IDs inválidos em todas as configurações.

A única falha de contexto ocorreu quando a pista “como possibilidade” apareceu depois da menção, fora do escopo à esquerda congelado. O falso positivo semântico foi o trecho “achados fenotípicos” do controle `DEV-CTRL-01`, vinculado a `HP:0000118`. Nenhuma regra, limiar ou escopo foi alterado após observar esses resultados.

O contexto pode avançar para avaliação inédita depois do congelamento. O detector semântico e a união permanecem offline e fora do dashboard. Relatório completo: `data/results/benchmark_v1_candidate_report.md`.

A repetibilidade foi verificada com duas execuções completas. Detalhes, previsões, gates, análise de erros, metadados, relatório e resumo normalizado foram idênticos; somente latência foi ignorada na comparação.
