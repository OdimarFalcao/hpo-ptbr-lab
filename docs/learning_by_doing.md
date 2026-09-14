# Aprendizado de TI aplicado ao HPO-PTBR

## Princípio

O projeto será usado para reforçar conteúdos de concursos por aplicação prática. O estudo não será transformado em uma segunda carga de trabalho e nenhuma tecnologia será adicionada apenas porque aparece em edital.

Após cada incremento relevante, a explicação para Odimar seguirá quatro perguntas:

1. Qual conceito de TI foi aplicado?
2. Qual problema concreto do projeto ele resolveu?
3. Como foi implementado e testado?
4. Como o tema costuma aparecer em concursos?

## Mapa de aplicação

| Tema recorrente nos editais | Aplicação natural no projeto |
|---|---|
| Engenharia de requisitos | pergunta de pesquisa, escopo, critérios de aceite e gates de promoção |
| Engenharia de software | separação entre detecção, linking, avaliação, interface e exportação |
| Testes de software | testes unitários, integração, regressão, repetibilidade e CI |
| Banco e modelagem de dados | esquema de casos, chaves HPO, integridade referencial e normalização |
| Engenharia e qualidade de dados | proveniência, hashes, metadados, splits e prevenção de vazamento |
| Análise de dados e estatística | amostragem, métricas, estratificação e análise de erros |
| Segurança e LGPD | uso exclusivo de dados públicos/sintéticos, minimização e rastreabilidade |
| DevOps | Git, GitHub Actions, dependências reproduzíveis e checks automatizados |
| Gestão ágil | sprint curta, backlog, critérios de pronto, revisão e registro de riscos |
| UX e acessibilidade | fluxo de revisão compreensível para profissional sem formação em computação |
| Interoperabilidade | HPO, JSON, futuro Phenopacket, SNOMED CT e OMOP sem integrações fictícias |
| IA e PLN | embeddings, NER, avaliação de viés, erros e limites de generalização |

## Regra de documentação

O código e os relatórios continuam sendo a fonte técnica. O vault registra decisões duráveis e andamento. Explicações didáticas serão produzidas por marco, não para cada comando ou alteração trivial.

## Marcos aplicados

### Benchmark V1 — requisitos e desenvolvimento

- **Requisitos:** os critérios de aceite foram convertidos em um protocolo JSON verificável.
- **Modelagem de dados:** caso, menção, HPO ID, offsets, contexto e forma superficial possuem campos explícitos.
- **Integridade referencial:** o gerador rejeita IDs inexistentes, repetidos ou usados em avaliações anteriores.
- **Amostragem estratificada:** cada domínio possui quatro conceitos no desenvolvimento, com formas e contextos balanceados.
- **TDD e regressão:** testes verificam offsets, exclusões, distribuições e hashes dos artefatos.
- **Auditoria:** plano de seleção, dataset, revisão e manifesto ficam separados e versionados.
- **Validação semântica:** paráfrases foram confrontadas com definições e sinônimos da fonte oficial, sem consultar saídas dos algoritmos.
- **Segregação de funções:** revisão técnica, confirmação humana e futura validação por profissional de saúde são estados diferentes e não intercambiáveis.
- **Controle de mudanças:** a única correção textual possui antes, depois, justificativa, fonte e novos hashes.

### Benchmark V1 — avaliação reproduzível

- **Decomposição de problemas:** detecção do trecho, linking HPO e contexto são medidos separadamente; assim, um erro do detector não é atribuído indevidamente ao ranker.
- **Métrica ponta a ponta:** o acerto exige simultaneamente span exato, HPO Top-1 e contexto correto, aproximando a medida do fluxo que o usuário realmente utiliza.
- **Accuracy versus macro-F1:** prever sempre `present` alcançou 66,67% de accuracy porque essa é a classe majoritária, mas somente 20,00% de macro-F1 porque as três classes minoritárias tiveram desempenho zero.
- **Controles negativos:** duas descrições sem fenótipos verificam se o detector produz falsos positivos mesmo quando não existe alvo anotado.
- **Análise estratificada:** separar rótulos oficiais, variações ortográficas e paráfrases revelou que fuzzy resolve ortografia no linking, mas nenhum método lexical detecta as paráfrases.
- **Pré-registro e integridade:** o SHA-256 do dataset e os parâmetros foram fixados antes da execução; o novo holdout continua não selecionado.
- **Resultado negativo útil:** BM25 recuperou parte das paráfrases quando recebeu o span ouro, mas a pipeline automática não localizou esses trechos. Isso orienta o próximo método para detecção, sem esconder a limitação.

### Benchmark V1 — candidatos controlados

- **Desenho fatorial simples:** fuzzy+contexto, semântico+contexto e híbrido+contexto isolam qual componente produz cada ganho ou erro.
- **Escopo em PLN:** o classificador examina somente o texto anterior à menção na mesma sentença. Isso evita carregar uma negação de outra frase, mas perdeu uma incerteza cuja pista apareceu depois do fenômeno.
- **Classes desbalanceadas:** macro-F1 subiu de 20,00% para 95,92%, mostrando ganho nas quatro classes, não apenas na classe majoritária `present`.
- **Critério de rejeição:** F1 maior não basta. O híbrido chegou a 77,14%, mas foi reprovado porque gerou falso positivo em 50% dos controles negativos.
- **Regressão de segurança:** zero HPO IDs inválidos continuou sendo requisito eliminatório em todas as configurações.
- **Controle de configuração:** modelo, revisão, hash, aliases, limiar e regras linguísticas foram registrados antes da execução; nenhuma correção foi feita após ver o erro.
- **Viés de desenvolvimento:** as regras de contexto foram especificadas após inspecionar textos sintéticos. O resultado é útil para engenharia, mas só casos inéditos poderão testar generalização.

### Bancada assistida — ontologia e interação humana

- **Ontologia versus terminologia:** o rótulo é apenas uma forma de apresentar o conceito; o HPO ID preserva a identidade e as relações `is_a` permitem navegar do conceito específico para classes mais gerais.
- **Modelo de dados separado:** o ranker continua usando registros leves, enquanto `HpoConcept` concentra definição, sinônimos, pais e filhos. Isso evita misturar recuperação textual com estrutura ontológica.
- **DAG e busca em largura:** o caminho até `HP:0000118` usa busca em largura e desempate por ID, produzindo o menor caminho determinístico mesmo quando uma classe possui vários pais.
- **Human-in-the-loop:** o usuário adiciona omissões, corrige sobreposições, troca candidatos, confirma contexto e descarta falsos positivos. A automação propõe; a revisão determina o perfil exportado.
- **Privacidade por concepção:** revisão e texto ficam somente no `session_state` e no download. Não foi criado banco apenas para praticar persistência.
- **Recuperação explicável:** Exact, fuzzy e BM25 aparecem separadamente com motivo e score de ranking; SapBERT só é carregado após ação explícita para um trecho.
- **Contrato de exportação:** `hpo-ptbr-review-v1` registra versão, offsets, origem, decisão, contexto, HPO selecionado e alterações humanas sem usar os termos confiança, diagnóstico ou Phenopacket.

### NER — agregação de subpalavras

- **Tokenização:** WordPiece pode dividir uma palavra portuguesa em várias subpalavras e produzir sequências BIOES inconsistentes.
- **Agregação de classes:** probabilidades de `B/I/E/S` são somadas por grupo semântico e depois agregadas por `word_id`, em vez de usar apenas o maior rótulo de cada subpalavra.
- **Pós-processamento geral:** pontuação encerra entidades e nenhum léxico dos casos foi adicionado.
- **Resultado de desenvolvimento:** F1 exato subiu de 0,00% para 65,57%, mas precisão de 64,52%, recall de 66,67% e 2/5 paráfrases ficaram abaixo dos gates.
- **Controle científico:** o método foi desenhado após dry-run no desenvolvimento; portanto, permanece offline e não autoriza holdout ou promoção ao dashboard.
