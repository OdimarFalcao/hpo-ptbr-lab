# Sprint de 7 dias — fechamento do V1

Registro do recorte V1 de agosto de 2026, preservado como histórico de execução e pendências daquela sprint. Não define o produto final nem um novo prazo. Para planejamento posterior, consulte a [visão do agente](AGENTE.md) e o [roadmap incremental](ROADMAP_AGENTE.md); protocolos experimentais continuam válidos para suas respectivas avaliações.

## Objetivo da sprint

Fechar um V1 acadêmico reproduzível que permita demonstrar, sem alegação clínica, o fluxo:

```text
descrição sintética em português
→ detecção de menções fenotípicas
→ candidatos HPO válidos
→ contexto da menção
→ revisão humana
→ exportação estruturada
```

O resultado esperado não é um produto clínico. É uma demonstração experimental que apresenta o que funciona, mede os erros e preserva as limitações encontradas.

## Critérios de aceite do V1

- Usar somente dados públicos e sintéticos.
- Validar todos os IDs contra o snapshot `hpo-2026-06-23_pt-62f1d254`.
- Não reutilizar o holdout consumido nem seus conceitos no novo benchmark.
- Separar métricas de detecção, normalização e contexto.
- Manter scores de ranking identificados como não calibrados.
- Executar o novo holdout uma única vez, depois do congelamento do método.
- Exibir evidência textual, alternativas e decisão humana no dashboard.
- Produzir relatório reproduzível, análise de erros e limitações.
- Manter testes, CI e documentação sincronizados.

## Plano diário

### Dia 1 — requisitos e qualidade dos dados

- Pré-registrar o protocolo do benchmark V1.
- Definir modelo de dados para casos e menções.
- Implementar validação de offsets, IDs, splits, contexto e diversidade.
- Criar testes unitários do validador.

Conceitos praticados: engenharia de requisitos, critérios de aceite, modelagem de dados, integridade referencial e TDD.

### Dia 2 — construção do benchmark

- Selecionar 36 HPO IDs inéditos e distribuídos entre nove domínios.
- Produzir as 20 descrições de desenvolvimento, incluindo dois controles sem fenótipo.
- Anotar offsets, tipo de superfície e contexto da menção.
- Executar validações automáticas e revisão linguística sem consultar rankings.

Conceitos praticados: amostragem estratificada, qualidade de dados, metadados, linhagem e prevenção de vazamento.

### Dia 3 — avaliação reproduzível

- [x] Adaptar o avaliador para detecção, linking, contexto e resultado ponta a ponta.
- [x] Calcular métricas gerais e por estrato.
- [x] Executar somente o conjunto de desenvolvimento.
- [x] Gerar taxonomia de erros.

Conceitos praticados: análise de dados, métricas, testes funcionais, observabilidade e auditoria de resultados.

Resultado: fuzzy liderou o F1 ponta a ponta geral com 50,79%, mas todos os métodos tiveram 0% de recall de detecção nas paráfrases. O baseline de contexto obteve 66,67% de accuracy e somente 20,00% de macro-F1. O próximo incremento deve tratar detecção semântica e contexto como problemas separados.

### Dia 4 — método candidato

- [x] Selecionar e pré-registrar um detector compatível com português clínico.
- [x] Fixar modelo, revisão, parâmetros e regra de decisão.
- [x] Comparar com o baseline lexical somente no desenvolvimento.
- [x] Registrar resultado positivo ou negativo sem ajuste retroativo.

Conceitos praticados: desenho experimental, controle de configuração, viés, versionamento e MLOps básico.

Resultado: o classificador de contexto passou seu gate com macro-F1 de 95,92%. SapBERT e a união lexical-semântica recuperaram 4/12 paráfrases, mas reprovaram por falso positivo em 1/2 controles. Nenhuma configuração semântica foi promovida ou ajustada após a execução.

### Dia 5 — fluxo do revisor

- [x] Manter o detector lexical como padrão e a IA experimental sob ação explícita.
- [x] Exibir contexto: presente, ausente, incerto ou histórico familiar.
- [x] Permitir incluir omissões, corrigir limites e descartar falsos positivos.
- [x] Preservar rankings separados e seleção humana do HPO.

Conceitos praticados: UX, requisitos funcionais e não funcionais, segurança por concepção e projeto centrado no usuário.

### Dia 6 — congelamento e interoperabilidade

- [x] Gerar índice ontológico determinístico com definições, sinônimos e relações `is_a`.
- [x] Excluir referências cruzadas SNOMED CT do artefato e da interface.
- [x] Gerar exportação `hpo-ptbr-review-v1` para menções revisadas.
- [x] Manter revisão somente na sessão e no download.
- [ ] Avaliar Phenopacket somente depois de validar o contrato experimental atual.

Conceitos praticados: hashes, rastreabilidade, integridade, interoperabilidade, JSON e governança de dados.

### Dia 7 — fechamento

- [x] Especificar e executar a agregação WordPiece somente no desenvolvimento.
- [x] Registrar a reprovação do gate sem promover o NER.
- [ ] Executar suíte completa, prontidão do dashboard e verificações de Git.
- [ ] Atualizar painel, tarefas e memória persistente.

Conceitos praticados: CI/CD, gestão de configuração, revisão de sprint, qualidade de software e comunicação técnica.

## Regra de escopo

Conteúdos de concurso serão aprendidos quando aparecerem naturalmente no trabalho. Não serão adicionados banco de dados, microsserviços, Kubernetes, autenticação ou infraestrutura apenas para cobrir edital. Cada incremento técnico deverá registrar o conceito aplicado, por que foi necessário e como ele aparece no projeto.
