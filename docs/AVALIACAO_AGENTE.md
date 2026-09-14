# Plano de avaliação do agente

Referência: [visão](AGENTE.md), fontes V1–V3, e [arquitetura](ARQUITETURA_AGENTE.md). Este é um plano prospectivo, não protocolo congelado, resultado experimental ou autorização para executar holdout. Valores de gates, amostras e métodos novos dependem de pré-registro e aprovação específica.

O desenho operacional para linguagem clínica natural está detalhado na [Fase 2](FASE_2_LINGUAGEM_E_AVALIACAO.md). A infraestrutura e um desenvolvimento sintético exploratório foram implementados; revisão clínica, validação, holdout, gates e avaliação humana permanecem prospectivos.

## Perguntas avaliáveis

O agente melhora a construção do perfil, a recuperação/priorização e a rastreabilidade em comparação com módulos isolados e pipeline fixo? Quais erros introduz? A assistência reduz esforço sem prejudicar correção? São perguntas separadas; desempenho de linking não demonstra desempenho diagnóstico.

## Dados e separação experimental

- Nesta fase, somente casos públicos/sintéticos sem dados pessoais. Casos reais futuros exigem autorização e governança própria; publicação prévia não elimina avaliação de licença e privacidade.
- Registrar fonte, versão, idioma, domínio, alvo, contexto, processo de construção e revisão. Manter controles sem fenótipo, ambiguidades e ausência de evidência nos protocolos futuros, sem alterar conjuntos existentes.
- Separar desenvolvimento e holdout antes de consulta a rankings. Evitar parentesco entre templates/paráfrases e separar por caso; definir também bloqueio por conceito, doença ou fonte conforme pergunta científica.
- Os dados já inspecionados orientam desenvolvimento, não avaliação independente. Holdout consumido não volta a ser inédito. Novo holdout existente permanece não selecionado/não executado até autorização e congelamento aplicáveis.
- Pré-registrar modelo/revisão, dados, parâmetros, baseline, métricas, gates, critérios de exclusão e commit/fingerprint do método. Resultado negativo deve permanecer disponível. Não ajustar o método no holdout.
- Casos que repetem literalmente o rótulo HPO alvo servem como testes funcionais, mas favorecem recuperação lexical e não demonstram fluidez clínica ou generalização. A avaliação principal deverá ter autoria independente, estratos de literalidade e bloqueio de rótulos, sinônimos, variantes, templates e conceitos correlatos entre partições.
- Desenvolvimento, validação e holdout terão funções distintas. Testes unitários e sanity checks não serão contabilizados como prova de generalização.

## Medidas por módulo

| Módulo | Medidas propostas | Comparação e análise |
|---|---|---|
| Extração | Precisão, recall e F1 de trecho exato; relaxado separado; offsets inválidos | Literalidade, ortografia, paráfrases técnicas/leigas, ambiguidades, domínios e controles negativos |
| Normalização | Accuracy@1/@5, MRR com corte declarado, IDs inválidos; erros de especificidade e distância ontológica definida | Spans ouro versus detectados; separar cobertura PT e qualidade do ranking |
| Contexto | Matriz de confusão, macro-F1 e desempenho por classe | Presente, ausente, incerto, familiar; não esconder minorias pela accuracy global |
| Conhecimento | Integridade das relações e proporção com proveniência verificável; cobertura explicitada | Relações ausentes, desatualizadas, contraditórias ou sem licença adequada |
| Priorização | Recall@K e MRR, K e universo de candidatos pré-fixados | Alvos curados de casos autorizados; perfil ouro versus produzido; ablação do contexto e de fontes |
| Evidências | Existência/resolução da referência, proporção de afirmações sustentadas e cobertura das afirmações por fonte | Avaliar suporte real por revisão humana; URL válida não prova suporte; referência inacessível fica não verificável |
| Orquestração | Sucesso de tarefas, escolhas de ferramentas, chamadas desnecessárias, latência e custo | Agente versus pipeline fixo, com mesmas ferramentas e dados; ablações sem diálogo e sem síntese LLM |
| Segurança | Taxas e contagens de afirmações sem suporte, citações/IDs inventados, instruções de fontes seguidas e extrapolações diagnósticas | Casos adversariais sintéticos, falha de fonte, negação/família, evidência insuficiente e contradição |
| Usabilidade | Tempo, ações, omissões, inclusões manuais, correções e erros após revisão | Manual versus assistido em casos comparáveis com ordem controlada; observar carga, fluidez e clareza sem telemetria silenciosa |

Para toda taxa, publicar numerador, denominador, estratos e exclusões; distinguir falha técnica de ausência de evidência. Calibração só será avaliada se houver método probabilístico apropriado, não renomeando scores.

## Avaliação humana e aceite

Odimar valida utilidade, clareza e capacidade de explicar o sistema. Adequação clínica e suporte das hipóteses exigem especialistas. Definir instruções de anotação, discordâncias e adjudicação antes da coleta; informar experiência dos revisores e limitações da amostra.

Testes automatizados verificam contratos, determinismo, IDs e fluxos; não substituem revisão clínica nem demonstram ganho de tempo. A antiga meta de cinco minutos é critério de usabilidade a testar com humanos, não resultado já obtido.

Antes de cada fase, fixar critérios mensuráveis e critérios críticos de bloqueio. Não promover com falha crítica de privacidade, IDs/citações fabricados ou diagnóstico autônomo. Quando não houver suporte, avaliar se o sistema se abstém corretamente, sem considerar toda abstenção como sucesso. Publicar erros e limitações; nenhum resultado sintético, isoladamente, sustenta validade clínica.

## Artefatos esperados

Protocolo versionado, manifesto de dados, decisões de revisão, execução reproduzível, resultados por caso/estrato e relatório de erros. Artefatos de pesquisa autorizados são separados de textos digitados na aplicação: não introduzir persistência automática da revisão para medir usabilidade. Coleta de tempos/interações depende de protocolo e consentimento, não telemetria silenciosa.
