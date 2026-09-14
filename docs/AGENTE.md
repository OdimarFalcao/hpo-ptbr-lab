# Agente HPO-PTBR — visão canônica

## Objetivo e status

Desenvolver um agente de IA especializado para problemas de ontologia clínica no Brasil: interpretar descrições clínicas em português, reduzir barreiras linguísticas e semânticas no uso da HPO, consultar ontologias e dados curados e auxiliar a investigação de diagnósticos genéticos com hipóteses priorizadas, evidências e referências rastreáveis.

**HPO é infraestrutura semântica, não produto final.** A bancada atual implementa o módulo inicial de construção e revisão de um perfil fenotípico. O agente completo não está implementado. Não realizará diagnóstico autônomo nem substituirá julgamento profissional.

Esta é a referência de visão e planejamento de desenvolvimento, consolidada em 11/09/2026 a partir do esclarecimento de Odimar. Não equivale à aprovação final da metodologia, do recorte da dissertação ou da validação clínica pelo orientador. Em 12/09/2026 foi autorizada e implementada a infraestrutura mínima da Fase 2 com execução exclusiva no desenvolvimento sintético; isso não autoriza validação, holdout, novo método ou alegação clínica.

## Origem e precedência documental

- **Fonte V1:** nota `PROJETOS/Pre-ProjetoMestrado/Agente HPO — Consolidado (anotações do orientador 28-05).md`, seções “Visão”, “Fluxo” e “Componentes”, no vault local `C:\Users\xboxf\OneDrive\Área de Trabalho\BACKUP\Obsidian Vault`. Lida integralmente; seu status registra validação do orientador pendente.
- **Fonte V2:** nota `PROJETOS/Pre-ProjetoMestrado/03 - Reunião 28-05-2026 — Rascunhos do orientador.md`, no mesmo vault. Origem: reunião de 28/05/2026; transcrição parcial, com incertezas preservadas.
- **Fonte V3:** `SISTEMA/Memória/MEMORIA.md`, registro “Alinhamento HPO 27/08/2026”, e esclarecimento de Odimar em 11/09/2026: o agente é o objetivo maior, a bancada é módulo inicial.

Essas são referências internas por título e localização, não links dependentes de um drive pessoal. As notas originais não foram alteradas. O material “Estado da Arte e Propostas - HPO PT-BR + Agentes IA” permanece arquivado, não é plano vigente. Recortes de julho/agosto explicam os experimentos e continuam válidos para suas avaliações; não definem sozinhos a finalidade global. Protocolos congelados não são substituídos por esta visão.

## Problema, usuários e jornada alvo

Expressões brasileiras podem diferir dos rótulos disponíveis, ter sinônimos, ambiguidades e contexto de negação, incerteza ou família. Encontrar um ID válido não demonstra correspondência correta nem sustenta uma hipótese diagnóstica.

Usuários pretendidos: profissionais envolvidos em fenotipagem e investigação genética; pesquisadores que avaliam normalização e rastreabilidade. Odimar atua como PO e pesquisador, não substitui avaliação clínica especializada.

Jornada futura: descrição de caso → perguntas de esclarecimento quando necessárias → perfil fenotípico revisado → consulta a conhecimento curado → hipóteses priorizadas → evidências verificadas → síntese em português, com lacunas e revisão profissional. Ausência de informação não será convertida em negação; o sistema deve poder dizer que não há suporte suficiente.

## Escopo e limites

- Escopo global: linguagem PT-BR, HPO, consulta ontológica, relações doença–gene–fenótipo, priorização, explicação rastreável e interação assistida. SNOMED CT e OMOP são obrigatórios no escopo global; integração depende de acesso e desenho próprios. Phenopackets é roadmap de interoperabilidade.
- Agora: núcleo do perfil e infraestrutura de avaliação da linguagem natural no desenvolvimento sintético. Apenas textos públicos/sintéticos sem dados pessoais; sem mudança em datasets oficiais, modelos, validação ou holdout.
- Fora: diagnóstico autônomo, prescrição, decisões clínicas automáticas, uso de prontuários nesta fase, redistribuição SNOMED CT, promessas de eficácia clínica e adaptações de metodologia sem autorização.
- Dados reais futuros exigem decisão separada, autorização, governança e avaliação ética aplicável. Execução local não substitui essas exigências.
- Scores de recuperação/priorização não são probabilidades clínicas. Evidência textual de uma menção não é evidência de doença. Tradução auxiliar futura não será apresentada como tradução oficial.

## Documentos de trabalho

1. [Arquitetura alvo e inventário real](ARQUITETURA_AGENTE.md).
2. [Fases e próximos passos](ROADMAP_AGENTE.md).
3. [Plano de avaliação](AVALIACAO_AGENTE.md).
4. [Decisões e pendências](DECISOES_AGENTE.md).
5. [Bancada existente](workbench_v1.md) e [operação web](web_workbench.md).
6. [Fase 2: linguagem clínica natural e avaliação](FASE_2_LINGUAGEM_E_AVALIACAO.md) e [rubrica de anotação](FASE_2_RUBRICA_ANOTACAO.md).
