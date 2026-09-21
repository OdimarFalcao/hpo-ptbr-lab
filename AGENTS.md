# Contrato operacional do projeto

Atualizado em 2026-09-21.

## Objetivo

Painel de alvos fenotípicos para DNA antigo: dado um conjunto de posições
genotipadas, medir de quais doenças monogênicas é possível perguntar se um
indivíduo carrega a variante causadora. Serve ao objetivo (c) do mestrado do
PO (inferência de doenças monogênicas em dados genômicos antigos).

A bancada de anotação de texto clínico que existia aqui foi retirada da
linha principal e está preservada na etiqueta `frente-a-final`. Não
reintroduzir código dela sem pedido explícito.

## Stack

- Python 3.11+, **somente biblioteca padrão**. `tests/test_package_imports.py`
  falha se um módulo importar biblioteca externa.
- `pytest` para testes.

## Estrutura

```
src/hpo_ptbr/
  ontology.py          vocabulário e hierarquia da HPO
  hpoa.py              doença -> fenótipos
  gene_disease.py      gene <-> doença
  term_targets.py      fenótipo -> doenças -> genes
  clinvar.py           variantes patogênicas germinativas por build
  genotype_panel.py    posições/alelos ensaiados; verificação do build
  target_coverage.py   cruzamento doença a doença
  hashing.py           hashes independentes de plataforma
  data.py              metadados do snapshot terminológico
  cli/                 um módulo por comando; __main__ só despacha
scripts/
  build_snapshot.py, build_ontology_index.py   geram o snapshot terminológico
  hpo_panel_cli.py                             atalho para a CLI
```

Cálculo fica nos módulos; a CLI só lê argumentos, chama e imprime.

## Pontos de entrada

- `hpo-painel <comando>` (após `pip install -e .[dev]`)
- `python scripts/hpo_panel_cli.py <comando>` (sem instalar)
- `python -m pytest -q`

## Regras

1. **Build do genoma é declarado e verificado.** Nunca inferir; nunca cruzar
   builds diferentes; nenhum liftover sem decisão explícita do PO.
2. **Toda exclusão é contada e exposta.** Filtro que remove dados registra o
   que removeu e por quê, no manifesto e na saída.
3. **Nada de tradução automática.** Sem rótulo oficial em português, exibe-se
   o inglês marcado como `[sem PT]`.
4. **Toda ingestão grava manifesto** com sha256 da fonte, versão declarada
   (ou o registro de que a fonte não declara) e contagens.
5. **Nenhum download pela ferramenta.** Fontes vêm de `data/raw/`.
6. **Não alterar resultados já registrados** em `data/processed/` sem
   explicar a mudança; regenerar deve reproduzir os mesmos bytes.
7. **Não tocar nos 8 scripts de contabilidade/DOCX** em `scripts/`
   (`add_aula04_escrituracao.py`, `audit_aula04_review.py`,
   `audit_contas_review.py`, `docx_to_qa_html.py`, `make_contact_sheet.py`,
   `merge_contas_review.py`, `render_qa_html.cjs`, `render_qa_html.mjs`).
   Não pertencem a este projeto.
8. **Não commitar, dar push nem apagar arquivos** sem o PO pedir.

## Riscos conhecidos

1. `ontology.path_to_root` percorre **um** caminho num grafo de múltiplos
   pais. Serve para testar pertinência à subárvore `HP:0000118` (verificado:
   19.119 conceitos, idêntico à travessia completa), mas **não** é teste de
   ancestralidade geral. A expansão por ancestrais precisa de travessia
   completa do grafo.
2. `term` e `coverage` usam só anotação direta da HPO, sem expansão pela
   hierarquia. Os resultados declaram `ancestor_expansion: false`.
3. `association_type` só é preenchido pelo OMIM; o Orphanet inteiro chega
   como `UNKNOWN`. Filtrar por mendeliana remove esse catálogo.
4. ClinVar e `genes_to_disease.txt` não declaram versão; a proveniência é o
   sha256 no manifesto.
5. `data.load_snapshot` descarta conceitos sem `label_pt`. Não usar para
   nada que precise do vocabulário completo; use `ontology`.

## Prioridade atual

1. Discutir com o orientador o resultado do relatório de viabilidade
   (33 doenças OMIM alcançáveis pelo 1240K) e a alternativa de partir das
   leituras brutas de genoma inteiro.
2. Travessia correta de ancestrais na HPO.
3. Busca de termo HPO por rótulo.
