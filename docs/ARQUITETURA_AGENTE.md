# Arquitetura alvo do agente

Referência de escopo: [visão canônica](AGENTE.md), fontes V1–V3. Este documento descreve responsabilidades, não APIs futuras, bibliotecas escolhidas ou funcionalidades prontas.

## Inventário do estado atual

| Capacidade | Estado e evidência local |
|---|---|
| Detecção lexical de menções com offsets | Implementada em `src/hpo_ptbr/evidence.py`; fluxo padrão em `src/hpo_ptbr/web_api.py` |
| Exact, Fuzzy e BM25 | Implementados em `src/hpo_ptbr/rankers.py` |
| Recuperação SapBERT | Opcional, local e acionada explicitamente; `sapbert.py`, `semantic.py` e endpoint semântico |
| Contexto presente/ausente/incerto/familiar | Regras em `src/hpo_ptbr/assertion.py`; confirmação humana |
| Conceitos HPO, definições, sinônimos e hierarquia is_a | Índice local em `src/hpo_ptbr/ontology.py`; não é serviço multi-ontologia |
| Revisão e perfil JSON | Fase 1 implementada em `src/hpo_ptbr/annotation.py` e React em `web/src/`: decisão humana, origem, recuperação, contexto, caracterização, pendências e proveniência; formato experimental aditivo `hpo-ptbr-review-v1` |
| Cobertura terminológica na revisão | O fluxo padrão continua limitado aos rótulos PT oficiais. A busca manual também consulta rótulos e sinônimos ingleses oficiais da HPO, exibindo idioma, fonte e ausência de tradução PT; não há sinônimos PT inventados |
| Avaliação de linguagem natural | Infraestrutura local da Fase 2 em `phase2_evaluation.py`: schema sintético, validação do padrão-ouro, auditoria de vazamento, métricas modulares, pendências, proxy de revisão e taxonomia de erros. Somente desenvolvimento foi executado; não altera o pipeline padrão |
| Experimentos semânticos/híbridos e NER | Código offline em `semantic_evidence.py`, `hybrid_evidence.py`, `mention_ner.py`; existência não significa promoção ao fluxo padrão |
| Agente, diálogo, conhecimento doença–gene, priorização e RAG | Não implementados |
| SNOMED, OMOP, OLS, OxO e Phenopacket oficial | Sem conectores/integração implementados |

Os caminhos abreviados de módulos referem-se a `src/hpo_ptbr/`. A API atual chama um pipeline fixo; não seleciona ferramentas por raciocínio de agente. Fontes PMID presentes em definições ontológicas não constituem RAG nem fundamentação diagnóstica.

## Camadas planejadas

1. **Interação e esclarecimento:** receber descrição autorizada e perguntar apenas sobre lacunas relevantes; manter separado o que foi declarado, inferido como candidato e confirmado. O usuário pode não saber responder.
2. **Perfil fenotípico:** reutilizar detecção, linking, contexto e revisão. Toda inclusão preserva trecho e versão HPO. Mudanças no perfil invalidam resultados derivados, sem reutilizar silenciosamente uma priorização antiga.
3. **Acesso a conhecimento:** consultar versões controladas de associações doença–gene–fenótipo e ontologias; registrar fonte, versão, identificadores e limites de licença. Seleção de fontes e política de atualização pendentes.
4. **Priorização:** ferramenta explícita e reproduzível compara o perfil com conhecimento curado. Método ainda não escolhido; não confundir similaridade fenotípica com causalidade ou diagnóstico.
5. **Verificação de evidências:** verificar se a fonte existe, é recuperável e sustenta cada afirmação. Diferenciar associação curada, definição, publicação e inferência. Expor ausência, contradição e desatualização.
6. **Orquestração e síntese:** LLM para interação e síntese sob ferramentas versionadas, nunca fonte autônoma de fatos clínicos. A ferramenta fornece IDs e resultados; o modelo não inventa associações ou citações. Respostas não sustentadas são omitidas ou marcadas como não verificadas, sem apresentá-las como evidência.
7. **Revisão e interoperabilidade:** apresentar hipóteses, suporte, incompatibilidades e limitações; exigir revisão profissional. Exportação padronizada será etapa posterior validada contra o padrão escolhido.

## Fluxo controlado e falhas

Caso → esclarecimento → perfil revisado → consulta de conhecimento → priorização → evidências verificadas → síntese explicável → revisão profissional.

Esclarecimentos podem retornar ao perfil; revisão do perfil reinicia etapas dependentes. Fontes indisponíveis devem gerar resposta parcial identificada, nunca substituição por memória do LLM. Conteúdo de textos, ontologias e literatura é dado não confiável para instruções: não pode autorizar ferramentas, publicação ou mudança de política. Limites de chamadas, timeout, cancelamento e rastreamento sem texto sensível serão especificados antes da orquestração.

## Dependências e fronteiras

- HPOA e relações doença–gene–fenótipo: investigar disponibilidade, versão, esquema, licença e cobertura antes de ingestão; não presumir que HPO is_a contém associações diagnósticas.
- SNOMED CT: acesso institucional e licença; não redistribuir conteúdo. OMOP: definir representação e vocabulários autorizados. Não impor passagem por ambos como pré-requisito técnico para cada anotação HPO.
- OLS/OxO: candidatos a consulta/mapeamento, não serviços escolhidos nem equivalência garantida. Relação is_a, referência cruzada e equivalência são distintas.
- Phenopackets: implementação e validação do padrão oficial antes de usar o nome para o arquivo.
- Hoje, estado somente em memória de sessão e download explícito. Persistência, serviços externos ou envio a provedor LLM dependem de nova decisão; nenhum backend de LLM foi escolhido.

Critérios de avanço: [roadmap](ROADMAP_AGENTE.md) e [avaliação](AVALIACAO_AGENTE.md).

## Contrato implementado na Fase 1

Cada anotação exportada preserva trecho e offsets, conceito selecionado, contexto (`present`, `absent`, `uncertain` ou `family_history`), origem automática/manual, métodos de recuperação, decisão humana e sinalização de modificação da sugestão. A caracterização possui `onset_age`, `severity`, `evolution`, `frequency`, `laterality` e `family_history`; valores ausentes geram `pending_characterization` em ordem fixa. Pendências não são convertidas em negação e não bloqueiam a exportação depois que todas as decisões de inclusão/descarte foram revisadas.

A proveniência terminológica da exportação fixa versão HPO, commit da tradução e fontes com hashes. `label_pt_status` diferencia rótulo português oficial de tradução indisponível. Sinônimos do índice atual são oficiais da HPO em inglês; ampliar sinônimos portugueses depende de uma fonte rastreável e revisão especializada.
