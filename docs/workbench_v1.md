# Bancada de anotação assistida HPO-PTBR

Este documento descreve o módulo inicial, não a finalidade completa da pesquisa. Visão e planejamento atuais: [agente especializado](AGENTE.md) e [roadmap](ROADMAP_AGENTE.md). As restrições e etapas de formação abaixo pertencem ao recorte da bancada; não retiram RAG, orquestração ou priorização do objetivo global.

## Problema resolvido

O detector automático não localiza todas as paráfrases e métodos semânticos podem produzir falsos positivos. A bancada não esconde esse limite: combina automação lexical, correção humana, informação ontológica oficial e exportação auditável.

## Fluxo do usuário

```text
descrição sintética em português
→ detecção lexical de trechos
→ comparação Exact/Fuzzy/BM25
→ correção de omissões e limites
→ seleção de HPO e contexto
→ consulta à hierarquia
→ perfil fenotípico revisado
→ JSON hpo-ptbr-review-v1
```

Correção humana significa adicionar uma expressão omitida, substituir um trecho sobreposto, trocar o conceito selecionado, confirmar o contexto ou descartar um falso positivo. Nada é persistido automaticamente.

## Informação ontológica

O índice comprimido contém os 19.836 conceitos ativos do snapshot HPO 2026-06-23, com:

- identificador e rótulos inglês/português disponíveis;
- definições oficiais em inglês e a única definição portuguesa versionada;
- sinônimos oficiais e indicação de linguagem clínica ou leiga;
- relações `is_a` de pais e filhos;
- fontes PMID associadas à definição.

Referências cruzadas externas, incluindo SNOMED CT, não são exportadas nem apresentadas.

## Comparação de métodos

- **Exact:** confirma igualdade após normalização.
- **Fuzzy:** mede proximidade de caracteres e resolve parte das variações ortográficas.
- **BM25:** valoriza termos compartilhados entre consulta e rótulo.
- **SapBERT opcional:** compara semanticamente um trecho escolhido pelo usuário. É experimental, local e não participa da detecção automática.

Scores servem apenas para ordenar candidatos. Não são probabilidade nem confiança clínica.

## Contexto da menção

O classificador baseado em pistas portuguesas sugere `present`, `absent`, `uncertain` ou `family_history`. A sugestão considera apenas o contexto anterior na mesma sentença e pode errar; o revisor sempre confirma o valor exportado.

## Trilha semanal do PO

- **3h — Ontologia e HPO:** classe, instância, ID, rótulo, sinônimo, definição, anotação, DAG e `is_a`.
- **2h — IA e PLN:** detecção, entity linking, recuperação, reranking, contexto e revisão humana.
- **1h — Avaliação:** precisão, recall, F1, Accuracy@K, MRR, falso positivo, desenvolvimento e holdout.
- **1h — Validação:** testar casos, explicar decisões e registrar dúvidas para o orientador.

Próximos fundamentos: gene, variante, genótipo, fenótipo, herança mendeliana, penetrância, expressividade, HPOA, exoma/genoma, similaridade semântica e priorização fenotípica. RAG, agentes, fine-tuning, SNOMED CT, OMOP e Phenopackets não entram antes de o núcleo HPO estar sólido.

## Referências orientadas

- HPO em 2024: <https://academic.oup.com/nar/article/52/D1/D1333/7416384>
- Estrutura da HPO: <https://human-phenotype-ontology.github.io/documentation.html>
- SAMS e anotação de sintomas: <https://academic.oup.com/nar/article/50/W1/W677/6582181>
- Princípios OBO Foundry: <https://obofoundry.org/principles/fp-000-summary.html>
- SapBERT: <https://aclanthology.org/2021.naacl-main.334/>
- Phenopackets: <https://www.ga4gh.org/product/phenopackets/>
- Bioinformática aplicada à Medicina — UFC: <https://allyssonallan.github.io/2026_MTA0034_Bioinfo_Med_UFC/>

## Limites

- Somente dados públicos e sintéticos.
- Nenhum diagnóstico ou recomendação terapêutica.
- Sem validação clínica ou afirmação de generalização.
- Sem persistência de texto, usuário ou revisão.
- O JSON é um artefato experimental e não deve ser chamado de Phenopacket.
