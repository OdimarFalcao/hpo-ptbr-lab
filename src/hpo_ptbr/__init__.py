"""Alcance Genômico: de quais doenças monogênicas os dados de DNA antigo
permitem perguntar.

Cruza doenças monogênicas (HPO), genes (HPO genes_to_disease), variantes
patogênicas (ClinVar) e posições genotipadas (painel de genotipagem em formato
EIGENSTRAT, como o 1240K do AADR) para medir de quais doenças um conjunto de dados genômicos
antigos permite perguntar.

Só biblioteca padrão. Módulos:

- `ontology`        vocabulário e hierarquia da HPO
- `hpoa`            doença -> fenótipos (phenotype.hpoa)
- `gene_disease`    gene <-> doença (genes_to_disease.txt)
- `term_targets`    fenótipo -> doenças -> genes
- `clinvar`         variantes patogênicas germinativas por build
- `genotype_panel`  posições e alelos ensaiados; verificação do build
- `target_coverage` o cruzamento, doença a doença
- `hashing`         hashes de conteúdo independentes de plataforma
- `data`            metadados do snapshot terminológico
- `cli`             a interface de linha de comando (`alcance`)

A bancada de anotação de texto clínico que coexistiu com esta ferramenta está
preservada na etiqueta git `frente-a-final`.
"""
