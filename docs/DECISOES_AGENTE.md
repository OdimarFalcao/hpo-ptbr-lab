# Registro inicial de decisões do agente

Registro documental de 11/09/2026. Origem: [visão canônica e fontes V1–V3](AGENTE.md). “Direção aprovada” significa autorização do PO para planejamento, não validação final do orientador, seleção de método ou implementação concluída.

| ID | Estado | Decisão e consequência |
|---|---|---|
| D01 | Direção reafirmada pelo PO | O objetivo é o agente especializado; HPO é infraestrutura semântica e a bancada é o primeiro módulo. Recortes experimentais não substituem a finalidade global |
| D02 | Princípio preservado | Não realizar diagnóstico autônomo. Hipóteses futuras serão apoio à investigação, com evidências e revisão profissional |
| D03 | Direção arquitetural | Modularidade: detecção, linking, conhecimento, priorização, verificação e síntese avaliados separadamente. Reutilizar núcleo Python sem migrar métodos silenciosamente |
| D04 | Existente e mantida | Revisão humana explícita do perfil; sugestão não é confirmação. Alterações invalidam resultados dependentes; diálogo investigativo ainda não existe |
| D05 | Direção arquitetural | LLM interage e sintetiza sob ferramentas versionadas; não é fonte autônoma de fatos, IDs, associações ou citações. Modelo/provedor não escolhidos |
| D06 | Existente/parcial | Rastreabilidade de trecho, contexto, ID e snapshot existe. Proveniência de associações e verificação de suporte bibliográfico são requisitos futuros, não RAG implementado |
| D07 | Restrição mantida | Execução local, textos sintéticos, estado de sessão e download explícito; sem persistência automática, telemetria textual ou publicação. Provedor externo exige decisão de dados/custos própria |
| D08 | Regra científica mantida | Dados/modelos versionados; desenvolvimento separado de holdout; preservar protocolos, gates e resultados negativos. Este registro não autoriza novas avaliações |
| D09 | Escopo global preservado | SNOMED CT e OMOP permanecem obrigatórios, com integração incremental após acesso/licença e desenho aprovados. Não redistribuir SNOMED nem simular conectores |
| D10 | Restrição mantida | JSON atual é hpo-ptbr-review-v1, não Phenopacket. Só adotar o nome após implementar e validar padrão oficial |
| D11 | Proposta para aprovação específica | Próxima fase técnica: cobertura PT-BR e especificidade; depois conhecimento curado, priorização/evidências, orquestração e interoperabilidade. Não escolher limiares a partir de erros isolados |
| D12 | Pendente | Escopo final da dissertação, extensão das hipóteses diagnósticas e critérios de validação dependem de discussão com orientador e especialistas |
| D13 | Implementada na Fase 1 | O perfil `hpo-ptbr-review-v1` foi estendido de forma aditiva: caracterização e pendências são por anotação; campos vazios permanecem desconhecidos, e pendências não impedem exportar decisões já revisadas |
| D14 | Implementada na Fase 1 | O detector e os rankers padrão foram preservados. A busca manual acrescenta rótulos/sinônimos oficiais HPO em inglês com fonte e idioma explícitos; ausência de rótulo PT é marcada como `unavailable`, nunca como tradução validada |
| D15 | Implementada parcialmente em 12/09/2026 | Intercalar uma Fase 2 de linguagem clínica natural e avaliação antes de conhecimento curado. Casos com rótulo-alvo literal permanecem testes funcionais; não serão tratados como evidência de generalização. A numeração prospectiva desloca conhecimento, priorização, orquestração e interoperabilidade sem reclassificar experimentos históricos |
| D16 | Implementada na infraestrutura da Fase 2 | Congelar o baseline por hashes mesmo com árvore local suja; autorizar somente desenvolvimento sintético; manter validação sem autoria e holdout selado sem conteúdo até participação independente |
| D17 | Implementada na avaliação da Fase 2 | Paráfrase sintética não é tradução oficial. Rótulo PT é copiado do snapshot ou fica ausente; o padrão-ouro técnico permanece pendente de revisão clínica |
| D18 | Implementada na avaliação da Fase 2 | Tempo humano só pode vir de arquivo local fornecido explicitamente. Sem estudo autorizado, reportar proxy de componentes de correção e `human_elapsed_seconds: null`, sem telemetria automática |
| D19 | Implementada em 14/09/2026 | O universo de fenótipos da bancada foi restringido aos descendentes de `HP:0000118`, excluindo a raiz. A ontologia completa permanece consultável, mas modificadores e outras categorias não podem ser sugeridos, selecionados ou exportados como fenótipos |
| D20 | Resultado negativo preservado | A Iteração 1 eliminou `começou → HP:0003674` e o único span incorreto da Fase 2, mas não melhorou recall nem ranking. Cobertura de conceitos sem PT e compreensão de paráfrases permanecem problemas separados |
| D21 | Autorizada pelo PO e implementada offline em 14/09/2026 | Conceitos fenotípicos sem tradução PT podem ser representados com rótulo oficial EN, fonte e versão, `label_pt_status=unavailable` e revisão humana obrigatória. Essa autorização não permite inventar tradução nem integrar automaticamente o método à bancada |
| D22 | Resultado negativo preservado | O índice oficial completo tornou 12.139 fenótipos sem PT representáveis, mas Exact, Fuzzy e BM25 recuperaram 0/9 alvos no Top-5; SapBERT recuperou 1/9 e 0/4 alvos sem PT. A regra pré-registrada falhou e nenhuma alteração foi integrada à API ou ao frontend |

## Como evoluir este registro

Nova decisão deve registrar problema, alternativas, responsável pela aprovação, consequência e evidência. Mudanças de arquitetura/metodologia exigem aprovação explícita; uma nova decisão pode substituir a anterior com referência, sem apagar história. Não converter ideias de documentos arquivados em compromissos ou fatos bibliográficos.

## Pendências antes da implementação posterior

- Revisar com orientador/especialista o protocolo de cobertura/especificidade já executado no desenvolvimento e definir gates clínicos antes de validação; não ajustar a partir do futuro holdout.
- Revisar clinicamente a rubrica e o padrão-ouro técnico da Fase 2; aprovar autoria independente, tamanho, gates e abertura futura de validação/holdout.
- Definir fonte licenciada e versionada de relações doença–gene–fenótipo; escolher baseline de priorização apenas depois de conhecer os dados.
- Definir fontes bibliográficas e procedimento humano de verificação de suporte.
- Definir papel, orçamento e ambiente do LLM; medir benefício sobre pipeline fixo.
- Discutir licenciamento, padrões e possível validação clínica com instituição/orientador.

Detalhamento: [roadmap](ROADMAP_AGENTE.md) e [avaliação](AVALIACAO_AGENTE.md).
