# Alcance Genômico

Ferramenta de linha de comando para avaliar o que um conjunto de dados
genômicos permite investigar. O caso de uso atual é DNA antigo e doenças
monogênicas.

O comando é `alcance`. A aplicação usa Python 3.11+ e somente a biblioteca
padrão em tempo de execução. Não faz diagnóstico.

## O que ela responde

Há dois fluxos independentes.

### Alcance de doenças

Dado um painel de genotipagem, identifica para quais doenças existe uma
variante patogênica cuja posição e cujos alelos são observáveis pelo painel:

```text
doença ── gene ── variante patogênica ── posição e alelos do painel
 (HPO)    (HPO)        (ClinVar)              (arquivo .snp)
```

O resultado diz que a pergunta pode ser feita. Não diz que algum indivíduo
carrega a variante, pois o arquivo de genótipos (`.geno`) não é lido.

### Descrição dos indivíduos

O comando `anno` descreve o arquivo de metadados do AADR: número de registros,
indivíduos distintos, local, data, tipo de dado e cobertura. Ele não aplica
filtros nem classifica indivíduos.

Esse fluxo não participa do cálculo de alcance de doenças.

> **Painel de genotipagem** é a lista fixa de posições e alelos examinados em
> todos os indivíduos, como o painel 1240K do AADR. Neste projeto, “painel”
> sempre tem esse significado; o nome da ferramenta é Alcance Genômico.

## Resultado atual

### Alcance do painel 1240K

AADR v66.p1 1240K (GRCh37) × ClinVar de 11/09/2026:

| etapa | resultado |
|---|---:|
| SNV patogênicas no ClinVar | 178.934 |
| em posição examinada pelo 1240K | 108 |
| com os alelos corretos | 54 |
| variantes distintas com alelos corretos | 52 |
| genes | 17 |
| doenças OMIM alcançáveis | **33 de 6.484** |
| doenças alcançáveis incluindo Orphanet | 56 de 9.142 |

Incluir variantes de origem não declarada no ClinVar não muda o conjunto de
doenças alcançáveis.

### Metadados do AADR

| medida | resultado |
|---|---:|
| registros no `.anno` | 23.089 |
| `Individual ID` distintos e não vazios | 21.433 |
| IDs presentes em mais de uma linha | 1.262 |
| registros com data `0` e `present` | 3.970 |
| registros com `Political Entity = Brazil` | 87 |

Essas são contagens descritivas, sem exclusões. Os 23.089 registros não
representam 23.089 indivíduos antigos: há IDs repetidos e registros atuais.

## Instalação

```powershell
git clone https://github.com/OdimarFalcao/hpo-ptbr-lab.git
cd hpo-ptbr-lab
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
```

Isso instala o comando `alcance` e o `pytest`. Sem instalar o projeto, use
`python scripts\alcance.py` no lugar de `alcance`.

## Dados de entrada

A ferramenta não baixa arquivos. Coloque as fontes em `data\raw\`, que fica
fora do git.

| arquivo | finalidade | versão usada |
|---|---|---|
| `phenotype.hpoa` | doença → fenótipos | HPO 2026-06-23 |
| `genes_to_disease.txt` | gene ↔ doença | HPO 2026-06-23 |
| `variant_summary.txt.gz` | variantes e classificações do ClinVar | 11/09/2026 |
| `v66.p1_1240K.aadr.patch.PUB.snp` | posições e alelos do painel 1240K | AADR v66.p1 |
| `v66.p1_1240K.aadr.PUB.anno` | metadados dos indivíduos | AADR v66.p1 |

As fontes da HPO estão na [release 2026-06-23](https://github.com/obophenotype/human-phenotype-ontology/releases/tag/v2026-06-23).
Os arquivos do AADR estão no [Harvard Dataverse](https://doi.org/10.7910/DVN/FFIDCW).
O ClinVar vem do [NCBI](https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/).

O `.snp` contém `patch` no nome e o `.anno` não. A correspondência entre os
dois arquivos ainda não foi confirmada; o manifesto do `anno` registra essa
incerteza.

Os rótulos oficiais em português e o índice da ontologia já estão em
`data\processed\`. Eles só precisam ser regenerados quando a release da HPO
mudar.

## Executar

### 1. Calcular o alcance de doenças

Execute em ordem:

```powershell
alcance snapshot
alcance panel data\raw\v66.p1_1240K.aadr.patch.PUB.snp --build GRCh37 --rotulo "AADR v66.p1 1240K"
alcance clinvar --build GRCh37
alcance coverage data\raw\v66.p1_1240K.aadr.patch.PUB.snp --build GRCh37 --rotulo "AADR v66.p1 1240K"
```

O build é obrigatório e verificado. A aplicação não o infere, não cruza
builds diferentes e não faz liftover.

### 2. Descrever os indivíduos

```powershell
alcance anno data\raw\v66.p1_1240K.aadr.PUB.anno
```

O comando mostra todas as distribuições com até 200 valores distintos. Acima
disso, mostra os 30 valores mais frequentes. Vazios, `..`, `n/a` e valores
semelhantes são contados e preservados.

### 3. Consultar HPO

```powershell
alcance search "ataxia"
alcance profile OMIM:224900
alcance term HP:0001251
```

`search` procura doenças pelo nome; ainda não existe busca de termos HPO pelo
rótulo.

## Comandos

| comando | função |
|---|---|
| `snapshot` | normaliza as associações doença–fenótipo e gene–doença |
| `panel` | caracteriza o painel de genotipagem e verifica o build declarado |
| `clinvar` | seleciona variantes patogênicas germinativas no build declarado |
| `coverage` | cruza doenças, variantes e posições/alelos do painel |
| `anno` | descreve o arquivo de metadados do AADR sem filtrar |
| `search` | procura doenças por nome |
| `profile` | mostra fenótipos e genes de uma doença |
| `term` | mostra doenças e genes associados diretamente a um termo HPO |

Use `alcance <comando> --help` para ver as opções. O contrato completo de
entrada e saída está em [`docs/USO_ALCANCE.md`](docs/USO_ALCANCE.md).

## Saídas e proveniência

Os resultados ficam em `data\processed\`.

| arquivo | comando | conteúdo |
|---|---|---|
| `hpo_annotations.csv` | `snapshot` | associações doença–fenótipo normalizadas |
| `gene_disease.csv` | `snapshot` | associações gene–doença normalizadas |
| `genotype_panel_metadata.json` | `panel` | descrição do painel e verificação do build |
| `clinvar_pathogenic.csv` | `clinvar` | variantes mantidas após o funil de seleção |
| `target_coverage.csv` | `coverage` | nível alcançado para cada doença |
| `aadr_anno_metadata.json` | `anno` | descrição das colunas e distribuições do `.anno` |

Cada ingestão grava um manifesto `*_metadata.json` com o sha256 da fonte,
versão declarada — ou o registro de que não foi declarada — e contagens de
entrada, saída e exclusões.

## Como interpretar

- **Alcançável** significa que o painel distingue os alelos da variante
  patogênica. Não significa que a variante foi observada em alguém.
- Estar apenas na mesma posição não basta: o par de alelos também precisa
  corresponder.
- O cálculo considera SNV. Indels, CNV e variantes estruturais não são
  observáveis pelo painel de SNPs.
- `term` e `coverage` usam anotações diretas da HPO, sem expansão pela
  hierarquia. Os resultados não são exaustivos.
- O Orphanet chega sem classificação de associação mendeliana. Filtrar por
  associação mendeliana remove esse catálogo.
- O `anno` não define ainda o que conta como Brasil, América do Sul, indivíduo
  antigo, genoma inteiro ou cobertura suficiente.
- Termos sem tradução oficial aparecem em inglês com `[sem PT]`; não há
  tradução automática.

## Testes

```powershell
python -m pytest -q
```

A aplicação usa apenas a biblioteca padrão. Um teste falha se algum módulo do
pacote importar uma dependência externa.

## Atualizar a HPO

Baixe `hp.json`, `hp-pt.babelon.tsv`, `phenotype.hpoa` e
`genes_to_disease.txt` da mesma release. Depois execute:

```powershell
python scripts\build_snapshot.py
python scripts\build_ontology_index.py
alcance snapshot
```

`phenotype.hpoa` declara a release e divergências são recusadas.
`genes_to_disease.txt` não declara versão; nesse caso, o manifesto registra o
sha256 e a sobreposição de identificadores com as demais fontes.

## Mais informações

- [`docs/USO_ALCANCE.md`](docs/USO_ALCANCE.md): comportamento detalhado de cada comando.
- [`AGENTS.md`](AGENTS.md): contrato operacional, termos e riscos conhecidos.
- `docs\relatorios\o_que_os_dados_permitem_perguntar.docx`: relatório para discussão com o orientador.

A antiga bancada de anotação de texto clínico está preservada na tag git
`frente-a-final` e não faz parte da linha principal.
