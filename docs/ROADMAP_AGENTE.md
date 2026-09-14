# Roadmap incremental do agente

Derivado da [visão canônica](AGENTE.md), fontes V1–V3. Fases sem datas ou promessas de resultado clínico. Planejamento não autoriza implementação, alteração de método ou consumo de holdout. O núcleo HPO continua sendo o primeiro módulo avaliável, não o produto final.

| Fase | Entrada | Entrega planejada e critério de saída | Risco principal |
|---|---|---|---|
| 0 — Consolidar direção | Documentação e inventário existentes | PO revisa os documentos; questões de escopo final são levadas ao orientador. Distinguir aprovação de desenvolvimento de validação científica | Recorte da bancada confundido com objetivo global |
| 1 — Perfil e cobertura PT-BR | Núcleo atual preservado; implementação autorizada em 11/09/2026 | **Implementado no núcleo operacional:** perfil revisável, contexto, caracterização, pendências, decisão humana, exportação determinística e proveniência; busca manual ampliada somente com termos oficiais rastreáveis. **Ainda pendente como pesquisa:** validação clínica e de cobertura/especificidade | IDs válidos, mas conceitos inadequados ou excessivamente específicos |
| 2 — Linguagem clínica e avaliação | Núcleo da Fase 1 e baseline congelado | **Implementado no desenvolvimento:** protocolo local, rubrica, casos sintéticos não literais, validador, auditor de vazamento, métricas modulares e análise de erros. **Pendente:** revisão clínica, autoria independente, validação, holdout e estudo humano | Linguagem artificial, vazamento de templates/sinônimos e falsa evidência de generalização |
| 3 — Conhecimento curado | Perfil avaliado em linguagem natural; fonte autorizada selecionada | Piloto versionado de associações doença–gene–fenótipo, com integridade referencial, licença e proveniência verificadas. Distinguir falta de associação de evidência negativa | Cobertura desigual, licença e vazamento de casos |
| 4 — Priorização e evidências | Relações auditadas; escopo de hipóteses e método aprovados | Baseline reproduzível de priorização e suporte por fonte; comparar perfil ouro e perfil produzido. Saída: relatório de erros, citações verificáveis e gate específico satisfeito, não alegação diagnóstica | Confundir similaridade com causalidade; citação sem suporte |
| 5 — Orquestração investigativa | Ferramentas individuais avaliadas, orçamento e política de LLM aprovados | Diálogo de esclarecimento e síntese por ferramentas, comparação com pipeline fixo, falhas controladas e revisão humana. Avançar somente com benefício mensurado e sem regressões de segurança pré-especificadas | LLM inventar fatos, seguir instrução de fonte ou aumentar custo sem utilidade |
| 6 — Interoperabilidade | Contratos de perfil/conhecimento estabilizados e acesso licenciado | Incrementos separados para Phenopackets, SNOMED e OMOP; conformidade e proveniência avaliadas por integração, sem simulação | Confundir mapeamento com equivalência ou violar licença |

O levantamento de licenças pode ocorrer antes da fase de interoperabilidade; integração não deve ser usada para contornar fragilidades do núcleo. SNOMED e OMOP continuam obrigatórios na visão global, não removidos por este faseamento.

## Próximo passo de maior valor

Revisar clinicamente a rubrica e o conjunto técnico de desenvolvimento da [Fase 2](FASE_2_LINGUAGEM_E_AVALIACAO.md). Depois, definir autoria independente, tamanho e gates para validação; o holdout continuará sem texto ou conceito exposto até o método final ser congelado.

O contrato operacional da Fase 1 está implementado, mas isso não encerra sua validação científica. Não foi executado novo holdout, não foram promovidos modelos experimentais e não foram criadas traduções auxiliares.

## Decisões pendentes

- PO e orientador: escopo demonstrável do agente e contribuição principal da dissertação; até onde priorizar doenças, genes e hipóteses.
- Especialista: esquema de anotação e adequação clínica dos exemplos e saídas.
- Pesquisa: fontes autorizadas de associações e literatura, baselines, gates, tamanho dos conjuntos e separação entre desenvolvimento e avaliação inédita.
- Metodologia/orientador: autoria independente, rubrica, unidades de bloqueio contra vazamento, composição dos estratos e abertura do holdout da Fase 2.
- Engenharia/PO: provedor ou execução local de LLM, orçamento, latência aceitável e política de envio de dados; não há escolha feita.
- Instituição: acesso SNOMED/OMOP e eventual validação com dados reais.

## Marcos anteriores

[Sprint V1](sprint_v1_7_days.md), [bancada](workbench_v1.md) e protocolos experimentais existentes documentam módulos e decisões históricas. Gates reprovados e holdout consumido permanecem preservados. Este roadmap não reinicia avaliações, não redefine resultados e não estabelece cronograma retroativo.
