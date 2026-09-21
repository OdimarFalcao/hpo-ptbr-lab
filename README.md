# Alcance Genômico

O Alcance Genômico avalia **de quais doenças monogênicas um conjunto de dados genômicos permite perguntar** se um indivíduo carrega a variante causadora. Foi desenvolvido para dados de DNA antigo, em que cada conjunto de dados lê apenas uma parte do genoma, e serve como etapa preparatória para a inferência de doenças monogênicas em indivíduos antigos.

A ferramenta também descreve os indivíduos presentes no conjunto de dados: origem, datação, tipo de sequenciamento e cobertura.

O comando é `alcance`.

## Como funciona

Uma doença monogênica é causada por uma alteração específica no DNA. Para saber se um conjunto de dados permite investigá-la, a ferramenta liga quatro fontes públicas:

```text
doença ─── gene ─── variante patogênica ─── posição lida no conjunto de dados
 (HPO)     (HPO)        (ClinVar)              (painel de genotipagem do AADR)
```

Uma doença é considerada **alcançável** quando o conjunto de dados lê a posição da variante patogênica e distingue os dois alelos envolvidos.

O **painel de genotipagem** é a lista fixa de posições do DNA que um conjunto de dados lê em todos os indivíduos. O painel 1240K do AADR lê cerca de 1,2 milhão de posições. Neste projeto, "painel" tem sempre esse sentido.

## Resultado atual

**Alcance do painel 1240K** (AADR v66.p1, GRCh37) com o ClinVar de 11/09/2026:

| etapa | resultado |
|---|---:|
| variantes patogênicas de uma base (SNV) no ClinVar | 178.934 |
| em posição lida pelo painel 1240K | 108 |
| com os dois alelos distinguidos pelo painel | 54 (52 variantes, 17 genes) |
| doenças OMIM alcançáveis | **33 de 6.484** |
| doenças alcançáveis, incluindo Orphanet | 56 de 9.142 |

**Indivíduos do AADR** (arquivo de metadados `.anno`, v66.p1):

| medida | resultado |
|---|---:|
| registros | 23.089 |
| indivíduos distintos | 21.433 |
| registros de pessoas atuais, usados como referência | 3.970 |
| registros do Brasil | 87 |

Um mesmo indivíduo pode ter mais de um registro, e os registros atuais fazem parte do total.

A discussão desses resultados está em `docs\relatorios\o_que_os_dados_permitem_perguntar.docx`.

## Instalação

Requer Python 3.11 ou superior. A ferramenta usa apenas a biblioteca padrão.

```powershell
git clone https://github.com/OdimarFalcao/hpo-ptbr-lab.git
cd hpo-ptbr-lab
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
```

O comando `alcance` fica disponível com o ambiente virtual ativo. Como alternativa, use `python scripts\alcance.py` no lugar de `alcance`.

## Dados de entrada

Os arquivos de origem ficam em `data\raw\`, fora do controle de versão.

| arquivo | conteúdo | versão | origem |
|---|---|---|---|
| `phenotype.hpoa` | sintomas de cada doença | HPO 2026-06-23 | [HPO](https://github.com/obophenotype/human-phenotype-ontology/releases/tag/v2026-06-23) |
| `genes_to_disease.txt` | genes de cada doença | HPO 2026-06-23 | [HPO](https://github.com/obophenotype/human-phenotype-ontology/releases/tag/v2026-06-23) |
| `variant_summary.txt.gz` | variantes e sua classificação clínica | 11/09/2026 | [ClinVar, NCBI](https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/) |
| `v66.p1_1240K.aadr.patch.PUB.snp` | posições e alelos do painel 1240K | AADR v66.p1 | [Harvard Dataverse](https://doi.org/10.7910/DVN/FFIDCW) |
| `v66.p1_1240K.aadr.PUB.anno` | metadados dos indivíduos | AADR v66.p1 | [Harvard Dataverse](https://doi.org/10.7910/DVN/FFIDCW) |

Os nomes do `.snp` e do `.anno` diferem (`patch`); a correspondência entre os dois arquivos está em verificação e fica registrada no manifesto do `anno`.

Os rótulos da HPO em português e o índice da ontologia já acompanham o repositório, em `data\processed\`.

## Uso

**Alcance de doenças**, na ordem:

```powershell
alcance snapshot
alcance panel data\raw\v66.p1_1240K.aadr.patch.PUB.snp --build GRCh37 --rotulo "AADR v66.p1 1240K"
alcance clinvar --build GRCh37
alcance coverage data\raw\v66.p1_1240K.aadr.patch.PUB.snp --build GRCh37 --rotulo "AADR v66.p1 1240K"
```

A versão do genoma de referência (`--build`) é informada pelo usuário e conferida contra o próprio arquivo, para que todas as fontes sejam comparadas na mesma versão.

**Descrição dos indivíduos:**

```powershell
alcance anno data\raw\v66.p1_1240K.aadr.PUB.anno
```

**Consultas à HPO**, a qualquer momento depois do `snapshot`:

```powershell
alcance search "ataxia"
alcance profile OMIM:224900
alcance term HP:0001251
```

## Comandos

| comando | função |
|---|---|
| `snapshot` | prepara as associações doença–sintoma e gene–doença da HPO |
| `panel` | descreve o painel de genotipagem e confere a versão do genoma |
| `clinvar` | seleciona as variantes patogênicas herdadas |
| `coverage` | calcula, doença a doença, até onde o painel alcança |
| `anno` | descreve os indivíduos do conjunto de dados |
| `search` | encontra o identificador de uma doença pelo nome |
| `profile` | mostra os sintomas e os genes de uma doença |
| `term` | mostra as doenças e os genes associados a um sintoma |

As opções de cada comando aparecem em `alcance <comando> --help`. O comportamento detalhado está em [`docs/USO_ALCANCE.md`](docs/USO_ALCANCE.md).

## Resultados e proveniência

Os resultados ficam em `data\processed\`. Cada comando grava também um manifesto (`*_metadata.json`) com a impressão digital (sha256) da fonte, a versão usada e as contagens de cada etapa, o que permite reproduzir qualquer número.

| arquivo | comando | conteúdo |
|---|---|---|
| `hpo_annotations.csv` | `snapshot` | associações doença–sintoma |
| `gene_disease.csv` | `snapshot` | associações gene–doença |
| `genotype_panel_metadata.json` | `panel` | descrição do painel e verificação da versão do genoma |
| `clinvar_pathogenic.csv` | `clinvar` | variantes patogênicas selecionadas |
| `target_coverage.csv` | `coverage` | nível alcançado por cada doença |
| `aadr_anno_metadata.json` | `anno` | descrição dos indivíduos |

## Como ler os resultados

- **Alcançável** indica que a pergunta pode ser feita com os dados: o painel lê a posição e distingue os alelos da variante. A resposta para cada indivíduo vem da análise dos seus genótipos.
- O cálculo abrange as variantes de uma única base (SNV), que são as observadas por um painel de SNPs.
- As doenças são ligadas aos sintomas pela anotação direta da HPO. A expansão pela hierarquia da ontologia está entre as próximas etapas.
- Sintomas com nome oficial em português aparecem em português; os demais aparecem em inglês, marcados com `[sem PT]`.
- A descrição dos indivíduos apresenta todas as contagens do arquivo. Os critérios de seleção (região, período, tipo de sequenciamento, cobertura) serão definidos com a orientação do projeto.

## Testes

```powershell
python -m pytest -q
```

## Atualizar a HPO

Coloque em `data\raw\` os arquivos `hp.json`, `hp-pt.babelon.tsv`, `phenotype.hpoa` e `genes_to_disease.txt` da nova release e execute:

```powershell
python scripts\build_snapshot.py
python scripts\build_ontology_index.py
alcance snapshot
```

O `snapshot` confere se o `phenotype.hpoa` pertence à mesma release da ontologia.

## Documentação

- [`docs/USO_ALCANCE.md`](docs/USO_ALCANCE.md): entradas, saídas e regras de cada comando.
- [`AGENTS.md`](AGENTS.md): regras de desenvolvimento, termos e pontos de atenção.
- `docs\relatorios\o_que_os_dados_permitem_perguntar.docx`: resultados e próximos passos.

A versão anterior do repositório, dedicada à anotação de texto clínico, está preservada na etiqueta git `frente-a-final`.
