# Fase 2 — linguagem clínica natural e avaliação do perfil HPO

## Status e relação com o projeto

Este documento combina o desenho prospectivo com o registro da infraestrutura mínima implementada em 12/09/2026. O protocolo executável, o conjunto sintético de desenvolvimento e o resultado exploratório existem; validação clínica, conjunto de validação, holdout e estudo humano continuam planejados e não autorizados. Ele detalha a Fase 2 posterior ao núcleo operacional da [Fase 1](ARQUITETURA_AGENTE.md#contrato-implementado-na-fase-1) e segue a [visão canônica](AGENTE.md), o [plano geral de avaliação](AVALIACAO_AGENTE.md) e as [decisões vigentes](DECISOES_AGENTE.md).

**Fato atual:** a bancada recebe texto PT-BR, detecta menções, oferece candidatos HPO, classifica contexto, permite revisão humana e exporta um perfil estruturado. Os casos sintéticos existentes são úteis como testes funcionais e material exploratório, mas parte deles contém literalmente os rótulos que o sistema deve recuperar.

**Implementado nesta etapa:** congelamento por hashes do baseline existente; protocolo de desenvolvimento sem gates aprovados; rubrica; nove menções em onze casos sintéticos; reserva explícita de validação e holdout; executor local; métricas e taxonomia de erros. Nenhum método foi melhorado antes ou depois do run. HPO continua sendo infraestrutura semântica do agente, não o produto final.

## 1. Problema e hipótese

### Problema metodológico

Quando uma descrição sintética contém diretamente o rótulo HPO esperado — por exemplo, quando a entrada e o índice compartilham a mesma expressão — detecção e normalização podem ser resolvidas por correspondência lexical. Isso cria **vazamento do alvo para a entrada** e favorece métodos exact/fuzzy/BM25. O resultado demonstra que o software encontra termos já presentes e que o contrato funciona, mas não demonstra que ele:

- compreende uma narrativa clínica fluida;
- recupera paráfrases, descrições leigas ou formulações abreviadas;
- separa achados relevantes de texto incidental;
- lida corretamente com ambiguidade, negação, incerteza, família e tempo;
- sugere o nível de especificidade HPO adequado;
- reduz o trabalho de revisão sem introduzir novos erros.

Esse viés não invalida os testes funcionais existentes. Ele limita a interpretação científica e impede tratá-los como evidência de generalização ou fluidez clínica.

### Hipótese avaliável

A hipótese da Fase 2 é que um núcleo assistido, avaliado em descrições sintéticas independentes e linguisticamente naturais, pode produzir perfis HPO revisáveis com rastreabilidade e menor carga de correção do que baselines explicitamente definidos, sem regressão crítica em falsos positivos, contexto ou segurança.

A evidência pretendida não é “eficácia clínica” nem capacidade diagnóstica. A fase deve produzir estimativas reproduzíveis de:

1. recuperação de menções em linguagem não literal;
2. normalização para o conceito e a especificidade corretos;
3. preservação de contexto e lacunas do perfil;
4. esforço necessário para revisão humana;
5. modos de falha e condições em que o sistema deve se abster.

## 2. O que conta como linguagem clínica natural em PT-BR

Nesta fase, linguagem clínica natural significa texto sintético escrito como narrativa plausível de anamnese, evolução ou resumo de achados, sem copiar rótulos HPO como regra de geração. A naturalidade não será presumida apenas porque o texto está em português; deverá ser avaliada segundo uma rubrica antes de qualquer execução do sistema.

O conjunto deverá representar, em proporções aprovadas antes da coleta:

- linguagem técnica usada por profissionais e linguagem leiga atribuível a paciente/família;
- paráfrases que expressem o conceito sem repetir seu rótulo preferencial;
- negação, incerteza, suspeita e histórico familiar;
- temporalidade: início, passado resolvido, progressão, estabilidade e recorrência;
- gravidade, frequência e lateralidade quando informadas;
- abreviações clínicas autorizadas pela rubrica, além de ortografia e acentuação variáveis;
- sentenças longas, coordenação de múltiplos achados e referências pronominais simples;
- achados irrelevantes, informação administrativa neutra e controles sem fenótipo;
- ambiguidades genuínas nas quais mais de um HPO é plausível ou a evidência não permite decidir;
- regionalismos somente quando houver fonte rastreável ou validação por especialista, nunca por invenção não marcada.

Não serão usados prontuários reais, textos identificáveis, dados pessoais ou material clínico copiado sem licença e governança próprias. “Sintético” descreve a origem do texto, não garante por si só ausência de viés ou realismo.

### Estratos de literalidade

Cada menção deverá receber uma classe definida pela rubrica, independente da saída do sistema:

- **literal:** coincide com rótulo ou sinônimo autorizado;
- **variação lexical:** flexão, ortografia, abreviação ou ordem de palavras sem mudança conceitual;
- **paráfrase clínica:** descrição técnica não idêntica ao vocabulário indexado;
- **descrição leiga:** formulação cotidiana que exige normalização semântica;
- **ambígua/insuficiente:** mais de uma interpretação razoável ou falta evidência para um conceito específico;
- **não fenotípica:** trecho que não deve gerar anotação HPO.

A rubrica deverá esclarecer como classificar combinações e qual dimensão tem precedência. Os estratos não serão inferidos dos acertos do sistema.

## 3. Estratégia de dados e anotação

### Papéis e independência

Para reduzir vazamento de formulação, quem redige a descrição não deverá receber uma lista de rótulos para simplesmente reescrevê-los. A organização preferida, a confirmar conforme disponibilidade, separa:

1. **desenho dos cenários:** define fatos clínicos abstratos e restrições de segurança;
2. **autoria das descrições:** redige narrativas naturais sem consultar rankings ou previsões;
3. **anotação HPO:** marca offsets, conceitos, contexto e caracterização usando a rubrica e o snapshot autorizado;
4. **adjudicação:** resolve discordâncias sem consultar a saída do método avaliado;
5. **execução e análise:** roda baselines somente depois do congelamento aplicável.

Uma mesma pessoa poderá acumular papéis apenas se isso for inevitável e estiver documentado como ameaça à validade. “Cegamento” significa ocultar previsões, rankings e métricas durante autoria/anotação; não significa ocultar informações necessárias para produzir o padrão-ouro.

### Unidade de anotação

Cada caso deverá registrar, no mínimo:

- identificador não clínico e versão;
- texto sintético integral;
- trechos e offsets ouro, incluindo política para menções descontínuas ou implícitas;
- HPO ID alvo ou marcação explícita de ambiguidade/abstenção;
- contexto ouro: presente, ausente, incerto ou histórico familiar;
- caracterização declarada no texto e campos realmente ausentes;
- estrato linguístico e domínio;
- autoria, revisão e adjudicação por identificadores de função, conforme política aprovada;
- fonte conceitual, versão da HPO/tradução e licenças aplicáveis;
- histórico de alterações sem resultados do sistema embutidos no texto.

### Rubrica e adjudicação

Antes da coleta, a rubrica deverá decidir: limites de span, coordenação, anáfora, achados compostos, conceito mais específico suportado, ancestral aceitável, ambiguidade, ausência de evidência, negação de classe versus instância, família e temporalidade. Exemplos de treinamento dos anotadores deverão ficar fora dos conjuntos avaliativos ou ser registrados como desenvolvimento.

Discordâncias serão preservadas até adjudicação. O relatório deverá publicar a forma de concordância escolhida e seus numeradores/denominadores; nenhum índice específico ou quantidade de anotadores é presumido neste plano. Adequação clínica requer especialista; revisão técnica pelo pesquisador não a substitui.

### Proveniência, licença e privacidade

Cada artefato terá manifesto com origem, finalidade, autores/revisores por papel, versão, licença, hashes, datas de congelamento e relação com conjuntos anteriores. Material público não é automaticamente reutilizável. Textos digitados na bancada não serão coletados por telemetria; estudos de tempo ou interação exigem protocolo e consentimento separados.

## 4. Separação metodológica e prevenção de vazamento

### Conjuntos

- **Desenvolvimento:** pode ser inspecionado e reutilizado para diagnóstico de erros e escolha de candidatos. Toda mudança motivada por seus resultados deve ser registrada.
- **Validação:** conjunto intermediário congelado, usado de maneira limitada para selecionar entre alternativas já especificadas. Consulta repetida o converte, na prática, em desenvolvimento e deverá ser declarada.
- **Holdout:** conjunto selado para uma execução autorizada depois do congelamento de método, parâmetros, rubrica, métricas, gates e código. Após a abertura, passa a ser avaliação consumida e não pode orientar ajuste apresentado como independente.

O tamanho, a composição e a quantidade de partições dependem de aprovação metodológica; este documento não fixa números.

### Unidades de bloqueio

Separar apenas por linha ou HPO ID não basta. Antes do particionamento, casos deverão ser agrupados para impedir que parentes próximos atravessem conjuntos:

- cenário-base e suas paráfrases;
- template de redação ou família de frases;
- autor e rodada de autoria, quando isso puder revelar estilo;
- rótulo, sinônimo e variantes lexicais derivadas da mesma expressão;
- conceito HPO e conceitos correlatos segundo uma política ontológica pré-declarada;
- fonte ou caso público de origem, se futuramente autorizado.

A política para conceitos correlatos deverá definir como tratar ancestrais, descendentes e vizinhos ontológicos sem escolher a regra depois de observar resultados. Um relatório de auditoria de vazamento deve preceder qualquer execução de validação ou holdout.

### Reprodutibilidade

Seeds, algoritmo de divisão, versão do ambiente, ordem dos casos e hashes serão fixados no protocolo antes da execução. Seeds controlam operações aleatórias; não tornam determinística a autoria humana nem corrigem viés de seleção. A seed e os números concretos só serão definidos após aprovação do desenho e do tamanho dos conjuntos.

Testes unitários, snapshots de UI e sanity checks com rótulos literais continuam necessários para engenharia, mas não contam como evidência de generalização linguística.

## 5. Cenários de avaliação

### Detecção de menções

Avaliar se o sistema encontra o trecho correto, omite menções implícitas ou não literais e cria falsos positivos em informação irrelevante. Reportar separadamente correspondência exata e sobreposição relaxada, sem permitir que o critério relaxado esconda fragmentação inadequada.

### Normalização e ranking HPO

Com spans ouro e spans detectados, medir se o conceito correto aparece nas primeiras posições. Erros deverão distinguir conceito errado, ancestral genérico, descendente específico demais e conceito plausível porém não sustentado pelo texto. Um HPO ID válido não é necessariamente uma anotação correta.

### Contexto e perfil

Avaliar presente, ausente, incerto e histórico familiar em matriz de confusão. Conferir se idade/início, gravidade, evolução, frequência, lateralidade e histórico familiar são preenchidos apenas quando declarados e se ausência de informação permanece pendência, não negação.

### Fluidez e revisão humana

Em estudo aprovado, comparar tarefas equivalentes com e sem assistência ou entre versões controladas. Observar tempo até perfil revisado, número de ações, candidatos examinados, menções incluídas manualmente, correções de limites/conceito/contexto/caracterização, abandonos e erro residual após revisão. A interface deve aceitar narrativa contínua; não se exigirá que o usuário converta previamente o caso em uma lista de rótulos HPO.

### Segurança e abstenção

Incluir controles negativos, texto ambíguo, menções negadas, familiares e evidência insuficiente. Avaliar falsos positivos, transformação indevida de desconhecido em ausente, extrapolação para diagnóstico, IDs inexistentes e linguagem que sugira certeza clínica. O comportamento esperado diante de suporte insuficiente pode ser pedir revisão ou se abster, conforme regra pré-registrada.

## 6. Métricas e análise de erros

| Dimensão | Métricas candidatas | Estratificação mínima proposta |
|---|---|---|
| Menção | precisão, recall e F1 exatos; medida relaxada separada; contagem de offsets inválidos | literalidade, extensão do trecho, domínio, controle negativo |
| Conceito | precisão/recall/F1 por conjunto de conceitos; desempenho ponta a ponta | literal, variação, paráfrase, leigo, ambíguo; nível de especificidade |
| Ranking | Recall@k e MRR em spans ouro; k fixado no protocolo | cobertura PT, método, estrato linguístico |
| Contexto | matriz de confusão, macro-F1 e medida por classe | presente, ausente, incerto, familiar, temporalidade |
| Pendências | precisão do preenchimento, omissão indevida e preenchimento sem suporte por campo | início, gravidade, evolução, frequência, lateralidade, família |
| Revisão | tempo, ações, correções, inclusões manuais, erro residual e abandono | experiência do revisor, caso, ordem e condição experimental |
| Segurança | falsos positivos em controles, especificidade excessiva, negação invertida, diagnóstico/extrapolação | tipo adversarial e gravidade definida antes da execução |

Sempre publicar numerador, denominador, casos excluídos e intervalos/incerteza compatíveis com o desenho aprovado. Micro e macro médias deverão ser diferenciadas. Ranking com spans ouro mede linking; resultado ponta a ponta incorpora detecção e não deve ser confundido com ele.

“Calibração” não será atribuída aos scores atuais, que não são probabilidades. Se a revisão humana coletar confiança prospectivamente em uma escala definida, poderá ser analisada a relação entre confiança e correção pós-revisão. Essa coleta, escala e métrica dependem de aprovação; sem isso, reportar correção e discordância, não calibração.

### Taxonomia mínima de erro

- menção omitida, espúria, fragmentada ou fundida;
- conceito errado no mesmo ramo ou em ramo diferente;
- conceito genérico demais ou específico demais;
- candidato correto fora do corte;
- rótulo/sinônimo PT ausente ou não validado;
- negação, incerteza, família ou temporalidade incorreta;
- caracterização inventada, omitida ou contraditória;
- ambiguidade forçada em vez de abstenção;
- erro corrigido pelo humano versus erro residual após revisão.

A análise qualitativa deverá preservar resultados negativos e separar falha do método, limitação dos dados e discordância do padrão-ouro.

## 7. Incrementos possíveis de produto, condicionados aos resultados

Nenhum item desta seção está autorizado para implementação por este plano. Primeiro mede-se o problema; depois decide-se se a mudança é justificada.

| Necessidade observável | Incremento candidato | Evidência exigida antes de implementar |
|---|---|---|
| Usuário precisa decompor o caso manualmente | manter entrada narrativa e melhorar segmentação/destaques explicáveis | omissões e carga de correção atribuíveis à segmentação |
| Paráfrases não chegam ao ranking | recuperação híbrida lexical-semântica offline, com fallback explícito | ganho por estrato sem aumento crítico de falsos positivos; candidato previamente especificado |
| Muitos candidatos semelhantes | comparação de conceito, definição, sinônimos e posição ontológica | redução de escolhas incorretas ou tempo, sem induzir especificidade excessiva |
| Casos de maior risco ficam misturados | fila de revisão orientada por regras auditáveis de risco | taxonomia de risco aprovada e benefício mensurado; score não apresentado como probabilidade |
| Contexto ou pendências passam despercebidos | resumo de conflitos e campos ausentes antes da exportação | redução de omissões sem preencher informação automaticamente |
| Sistema não tem suporte suficiente | ação explícita “não foi possível normalizar” e inclusão manual rastreável | casos de ambiguidade/abstenção definidos e avaliados |

O núcleo continuará local, sem persistência automática. Não serão introduzidos novos modelos, LLMs, APIs externas, diagnóstico, priorização doença–gene, RAG, SNOMED CT, OMOP ou Phenopackets nesta fase.

## 8. Riscos, limites e ameaças à validade

- **Realismo sintético:** autores podem produzir texto artificialmente limpo ou previsível.
- **Vazamento lexical:** rótulos, sinônimos, templates ou paráfrases irmãs podem atravessar conjuntos.
- **Viés de anotação:** quem conhece o método pode escolher spans ou conceitos favoráveis.
- **Padrão-ouro incerto:** HPO permite diferentes níveis de granularidade e algumas narrativas não sustentam solução única.
- **Cobertura PT desigual:** ausência de tradução/sinônimo pode ser confundida com falha do ranker.
- **Amostra e revisores:** poucos casos, domínios ou perfis profissionais limitam generalização.
- **Efeito de aprendizagem:** ordem fixa pode melhorar tempo sem melhoria do produto.
- **Métrica incompleta:** média global pode esconder falhas em negação, família, ambiguidade ou controles negativos.
- **Validade externa:** desempenho em texto sintético não demonstra desempenho em prontuários ou prática clínica.
- **Mudança de ferramenta:** trocar método, snapshot ou rubrica durante a avaliação quebra comparabilidade.

### Critérios de parada

A execução deverá parar, sem “consertar” o holdout, se ocorrer qualquer uma das condições pré-registradas: quebra de cegamento, vazamento entre partições, manifesto incompleto, mudança não versionada de dados/método, exposição de dado pessoal, corrupção de offsets/IDs, execução prematura do holdout ou falha que invalide uma parte material das previsões. Incidente e decisão deverão ser registrados; repetir exige novo status metodológico explícito.

Falha em gate não autoriza ajuste posterior no holdout. Resultado negativo é entregável válido.

## 9. Plano operacional sequencial

1. **Aprovar perguntas e escopo:** confirmar com PO/orientador a contribuição da Fase 2 e manter diagnóstico fora do escopo.
2. **Congelar protocolo antes dos dados avaliativos:** definir rubrica, papéis, partições, unidades de bloqueio, métricas, gates e critérios de parada.
3. **Treinar a rubrica em material de desenvolvimento:** resolver ambiguidades do manual usando apenas exemplos declarados como desenvolvimento.
4. **Coletar e curar textos sintéticos independentes:** registrar proveniência, naturalidade, licença e ausência de dados pessoais.
5. **Anotar e adjudicar sem previsões:** produzir padrão-ouro, medir discordâncias e congelar manifestos/hashes.
6. **Auditar vazamento e separar conjuntos:** aplicar grupos, seed e algoritmo pré-registrados; selar validação e holdout.
7. **Confirmar o baseline já congelado antes dos dados:** verificar hashes de código, snapshot, dependências e parâmetros antes de cada execução.
8. **Executar experimentos offline somente no desenvolvimento:** comparar componentes isolados, publicar erros e escolher no máximo alternativas previstas.
9. **Usar validação conforme protocolo:** decidir promoção sem reotimização iterativa disfarçada.
10. **Conduzir revisão humana autorizada:** coletar somente medidas consentidas e sem telemetria textual silenciosa.
11. **Congelar candidato final e executar holdout uma vez:** verificar pré-condições e registrar que o conjunto foi consumido.
12. **Analisar e decidir produto:** implementar apenas melhorias sustentadas pelos achados em autorização posterior; caso contrário, preservar baseline e resultado negativo.

Cada passo deve gerar artefato pequeno e verificável antes do próximo. A ordem impede que uma interface mais fluida seja confundida com melhora metodológica ou que uma mudança de método seja escolhida a partir do holdout.

## 10. Critérios de aceite e entregáveis

### Critérios de aceite propostos

A Fase 2 estará concluída quando, sem prometer eficácia clínica:

- existir protocolo aprovado e versionado antes da avaliação;
- descrições sintéticas naturais forem independentes dos rótulos-alvo conforme rubrica;
- desenvolvimento, validação e holdout estiverem separados e auditados contra vazamento;
- padrão-ouro, discordâncias e adjudicação tiverem proveniência;
- baseline congelado e candidatos offline forem comparados por módulo e ponta a ponta;
- resultados forem estratificados por literalidade, paráfrase, contexto, ambiguidade e controles;
- especificidade excessiva, ausência de detecção e falsos positivos forem analisados;
- estudo humano, se autorizado, reportar tempo/carga e erro residual sem coleta silenciosa;
- IDs, fontes, versões e decisões forem reproduzíveis;
- resultados negativos, limites e holdout consumido permanecerem explícitos;
- qualquer incremento de produto vier em etapa posterior e vinculado a evidência observada.

Nenhum valor numérico de gate é aprovado por este documento. Gates deverão ser definidos prospectivamente com justificativa e responsáveis.

### Entregáveis esperados

- protocolo executável e versão narrativa correspondente;
- rubrica de autoria/anotação e guia de adjudicação;
- manifesto de proveniência, licença, privacidade e partições;
- relatório de auditoria de vazamento;
- baseline congelado com fingerprint de código, dados e ambiente;
- previsões e métricas por caso/estrato, sem texto sensível;
- matrizes de contexto e relatório de especificidade;
- relatório de erros, abstenções e ameaças à validade;
- relatório de revisão humana, somente se aprovado;
- decisão registrada de promover, revisar ou interromper cada candidato.

## 11. Decisões pendentes por responsável

| Responsável | Decisão necessária antes da execução |
|---|---|
| Usuário/PO | objetivo demonstrável, recursos disponíveis, se haverá estudo humano e quais fluxos de produto merecem comparação |
| Orientador | desenho científico, unidades de bloqueio, tamanho/amostragem, gates, uso de validação e condição de abertura do holdout |
| Especialista clínico | rubrica, naturalidade, adequação e especificidade dos HPO, ambiguidades aceitáveis, gravidade das falhas |
| Metodologia/pesquisa | estratégia de concordância/adjudicação, análise estatística, seeds, intervalos e controle de múltiplas comparações se aplicável |
| Instituição/ética | necessidade de submissão/consentimento para participação humana; qualquer uso futuro de dados reais requer decisão separada |
| Engenharia/PO | quais candidatos já existentes podem ser executados offline; novo modelo ou serviço exige autorização posterior |

Até essas decisões, somente o desenvolvimento técnico sintético pode ser repetido. Não há autorização para abrir validação/holdout, promover método ou afirmar generalização.

## 12. Implementação e resultado de desenvolvimento

### Artefatos implementados

- `data/protocol/phase2_baseline_freeze.json`: commit, estado da árvore, versões, parâmetros e hashes congelados antes da infraestrutura nova.
- `data/protocol/phase2_evaluation_protocol.json`: política sintética/local, métricas, bloqueios e autorização exclusiva do desenvolvimento.
- `data/eval/phase2_development.json`: onze casos, nove menções, dois controles e padrão-ouro técnico pendente de revisão clínica.
- `data/eval/phase2_split_registry.json`: famílias do desenvolvimento e espaços deliberadamente vazios para validação e holdout independentes.
- [rubrica de anotação](FASE_2_RUBRICA_ANOTACAO.md), validador/auditor em `src/hpo_ptbr/phase2_evaluation.py` e executor `scripts/run_phase2_development.py`.
- `data/results/phase2_development_*`: metadados, detalhes por menção, erros, resumo e relatório narrativo.

### Resultado observado

O baseline fuzzy congelado obteve 0% de F1 de span exato, 0% de recall relaxado e 0% de Accuracy@1/@5 quando recebeu as próprias menções ouro. O contexto atingiu 66,67% de accuracy e macro-F1 de 44,23%; acertou a negação coberta pela regra atual, mas errou duas formulações de incerteza e o histórico familiar. Os dois controles não produziram falsos positivos neste conjunto pequeno.

A análise registrou oito menções não detectadas, um span sobreposto incorreto, nove conceitos Top-1 errados, nove falhas de paráfrase e quatro falhas de cobertura portuguesa em conceitos sem rótulo PT no snapshot. Não houve caso em que o Top-1 errado fosse ancestral ou descendente do ouro; portanto, “genérico demais” e “específico demais” ficaram em zero, sem concluir que o risco inexiste.

O baseline marcou todos os campos de caracterização como pendentes. Isso recuperou 100% dos campos realmente ausentes, mas a precisão foi 77,78% e doze valores explícitos no texto deixaram de ser estruturados. O proxy computacional registrou 33 componentes de correção; tempo humano permaneceu não medido porque nenhuma observação consentida foi fornecida.

Esses números descrevem apenas nove menções sintéticas não adjudicadas. Não são intervalo de desempenho, evidência clínica, gate aprovado ou teste de generalização.

### Recomendações após os erros

1. Submeter os nove conceitos, spans, limites de evidência e graus de especificidade à revisão clínica antes de ampliar o conjunto.
2. Testar no desenvolvimento uma cobertura rastreável de paráfrases e sinônimos, sem promovê-los automaticamente a tradução oficial.
3. Especificar mudanças pequenas no detector e nas regras de incerteza/família e compará-las sempre contra o manifesto congelado.
4. Criar validação por autoria independente somente depois de congelar as alternativas; manter o holdout fora do repositório acessível ao desenvolvimento.
5. Planejar um estudo humano separado para medir tempo e ações; até lá, manter o proxy claramente rotulado.

## 13. Iteração 1 — filtro da árvore fenotípica

Em 14/09/2026, após os erros manuais `começou → HP:0003674`, `esquerda → HP:0012835` e candidatos de modo de herança, foi implementado um invariante: candidatos do perfil devem ser descendentes de `HP:0000118`, sem aceitar a raiz.

O índice completo de 19.836 conceitos não foi removido e continua disponível para inspeção ontológica. O universo traduzido usado automaticamente caiu de 7.158 registros para 6.980 fenótipos. Busca de seleção e exportação aplicam a mesma barreira, impedindo que uma requisição adulterada reintroduza categoria não fenotípica.

No caso sintético de marcos do desenvolvimento, o único span `começou` desapareceu. Nos onze casos de desenvolvimento, as previsões caíram de um span incorreto para zero: `wrong_span` passou de 1 para 0 e `mention_not_detected` de 8 para 9. Recall exato, recall relaxado e Accuracy@5 permaneceram em 0%. Portanto, a iteração corrigiu escopo e reduziu dano, mas não tornou a extração útil.

Não foram alterados limiar, scorer, modelo, contexto, tradução ou dataset oficial. O próximo problema é tornar conceitos sem rótulo PT representáveis sem confundir alcançabilidade com recuperação de paráfrases.

## 14. Iteração 2 — cobertura oficial e linking offline

O PO autorizou avaliar conceitos sem rótulo PT desde que a ausência fosse explícita, o rótulo oficial inglês e sua fonte/versão fossem preservados e toda decisão continuasse humana. Antes da execução foi registrado `data/protocol/phase2_iteration2_offline_protocol.json`. Validação e holdout permaneceram fechados.

O índice derivado contém os 19.119 descendentes de `HP:0000118`, sem a raiz: 6.980 com rótulo PT e 12.139 com `label_pt_status=unavailable`. Foram indexados 49.218 termos: 6.980 rótulos oficiais PT, 19.119 rótulos oficiais EN e 23.119 sinônimos exatos EN. Cada candidato registra o termo que determinou o score, idioma, campo, fonte, versão e revisão humana obrigatória. Nenhum dataset oficial ou tradução foi alterado.

### Resultado observado

| Método em trecho-ouro | Accuracy@1 | Accuracy@5 | Alvos sem PT no Top-5 |
|---|---:|---:|---:|
| baseline fuzzy PT | 0/9 | 0/9 | 0/4 |
| termos oficiais exact | 0/9 | 0/9 | 0/4 |
| termos oficiais fuzzy | 0/9 | 0/9 | 0/4 |
| termos oficiais BM25 | 0/9 | 0/9 | 0/4 |
| termos oficiais SapBERT local | 0/9 | 1/9 | 0/4 |

O único alvo correto apareceu na terceira posição para “vem perdendo força de forma contínua” (`HP:0003323`). Nos outros oito casos, o alvo ficou fora do Top-5. Entre os primeiros candidatos errados apareceram conceitos lexical ou semanticamente próximos, como anomalia da orelha interna para comprometimento do ouvido interno, e conceitos específicos não sustentados pelo texto. Isso confirma que alcançabilidade terminológica não equivale a normalização correta.

O detector congelado continuou produzindo zero spans nos onze casos e zero falsos positivos nos dois controles. Esse controle não torna o linking seguro: rankers avaliados em span-ouro não detectam menções e, portanto, não possuem taxa própria de falso positivo. O experimento mediu somente linking condicionado a um trecho fornecido.

### Decisão e limites

A regra pré-registrada exigia ganho no Top-5, recuperação de pelo menos um alvo sem PT e ausência de aumento de falsos positivos automáticos. A segunda condição falhou. O status é `do_not_integrate`; API, frontend, detector e exportação não receberam o novo índice.

Os nove alvos são desenvolvimento sintético com padrão-ouro técnico pendente de revisão clínica. O ganho de um caso não demonstra generalização. A primeira construção dos embeddings do SapBERT no CPU também foi custosa; eventual candidato futuro precisaria de cache derivado e versionado, mas desempenho de produção não foi objetivo desta execução.

Próxima recomendação objetiva: antes de outro método, revisar clinicamente spans e granularidade dos nove alvos e classificar os oito erros por relação ontológica. Só depois definir uma hipótese nova e única para linking de paráfrases, preservando o índice como infraestrutura rastreável e mantendo a aplicação sem integração.
