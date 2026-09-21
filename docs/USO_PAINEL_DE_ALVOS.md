# Uso — painel de alvos fenotípicos

Guia operacional da CLI `scripts/hpo_panel_cli.py`. Tudo aqui roda sobre
dados versionados locais: **nenhum comando baixa nada da rede**.

Esta é a frente de "painel de alvos" do repositório. A outra frente — a
bancada de anotação e ranqueamento — tem entradas próprias e depende de
`rapidfuzz`, `rank_bm25` e modelos semânticos, que o painel não usa.

---

## 0. Pré-requisitos

O painel precisa apenas da biblioteca padrão do Python (3.11+). Se algum
comando falhar com `ModuleNotFoundError`, confirme qual interpretador está
em uso:

```
python -c "import sys; print(sys.version, sys.prefix)"
```

Três arquivos brutos precisam existir em `data/raw/`, todos da **mesma
release da HPO** (em uso: `2026-06-23`):

| arquivo | o que é | origem |
|---|---|---|
| `phenotype.hpoa` | doença apresenta fenótipo | release da HPO |
| `genes_to_disease.txt` | gene associado a doença, e de que tipo | release da HPO |
| `v66.p1_1240K.aadr.patch.PUB.snp` | posições genotipadas do painel AADR | Harvard Dataverse |

---

## 1. `snapshot` — normalizar as fontes

Roda uma vez por release. Converte os arquivos brutos em CSVs versionados
com manifesto de proveniência.

```
python scripts\hpo_panel_cli.py snapshot
```

O que ele garante, e por que importa:

- **Recusa o arquivo se a release declarada no cabeçalho do `phenotype.hpoa`
  divergir do snapshot terminológico em uso.** Perfil de uma release lido
  com o vocabulário de outra produz resultado que parece certo e não é.
- `genes_to_disease.txt` **não declara release** no cabeçalho. Não há como
  verificar. O que dá para medir é a sobreposição de identificadores de
  doença com o snapshot de anotações — o percentual vai para o manifesto.
  Sobreposição baixa indica releases divergentes.
- Registra a cobertura em português das anotações. Hoje: 40,62%. Termo sem
  rótulo oficial nunca é traduzido automaticamente.

Saídas: `data/processed/hpo_annotations.csv`, `gene_disease.csv` e os dois
manifestos `*_metadata.json`.

---

## 2. `search` — achar o identificador de uma doença

```
python scripts\hpo_panel_cli.py search "ataxia" --limite 10
```

Busca por substring no **nome da doença**. Entre colchetes vêm os genes
associados, quando existem.

---

## 3. `profile` — perfil de uma doença

Da doença para os fenótipos e genes.

```
python scripts\hpo_panel_cli.py profile OMIM:224900
python scripts\hpo_panel_cli.py profile OMIM:224900 --somente-mendelianas
python scripts\hpo_panel_cli.py profile OMIM:224900 --aspects P C I
python scripts\hpo_panel_cli.py profile OMIM:224900 --json
```

Aspectos: `P` fenótipo (padrão), `C` curso clínico, `I` herança,
`M` modificador, `H` história pregressa.

Na tabela de fenótipos, a coluna `?` marcada com **NÃO** significa
fenótipo *explicitamente descartado* naquela doença (qualificador `NOT` na
fonte) — a afirmação oposta, não uma ocorrência.

---

## 4. `term` — caminho inverso: fenótipo → doenças → genes

Do achado para as doenças candidatas. É o comando que monta o recorte.

```
python scripts\hpo_panel_cli.py term HP:0001249
python scripts\hpo_panel_cli.py term HP:0001249 --somente-mendelianas
python scripts\hpo_panel_cli.py term HP:0001249 --somente-com-gene --limite 50
python scripts\hpo_panel_cli.py term HP:0001249 --json
```

O rodapé é a parte que decide se o recorte se sustenta:

```
2473 doença(s) apresentam · 1329 após filtros · 1234 gene(s) distintos (1232 mendelianos)
  580 sem gene conhecido nesta fonte
  564 com gene não mendeliano, das quais 554 apenas porque a fonte
      não classifica o tipo de associação (todo o Orphanet chega assim)
  22 doença(s) descartam explicitamente este fenótipo (qualificador NOT)
```

Três limites que o resultado declara e que precisam ser lidos:

1. **`NOT` não conta como ocorrência.** Sai separado, em `excluded_in`.
2. **Só anotação direta.** Doença anotada num termo *descendente* do
   consultado não aparece. Doença rara costuma ser anotada em termos muito
   específicos, então a cobertura real é maior que o número exibido. A
   expansão por ancestrais ainda não está implementada — o JSON registra
   `ancestor_expansion: false` para que nenhum resultado seja lido como
   exaustivo.
3. **`association_type` só é preenchido pelo OMIM.** Todo o Orphanet chega
   como `UNKNOWN`. Filtrar por mendeliana remove esse catálogo inteiro, e
   isso **não** significa que essas doenças não sejam monogênicas.

Marcação `*` ao lado do gene: associação não classificada como mendeliana
pela fonte.

> O identificador HPO precisa ser conhecido de antemão — `search` procura
> por nome de doença, não de fenótipo. Busca de termo por rótulo ainda não
> existe.

---

## 5. `panel` — caracterizar o painel de posições genotipadas

```
python scripts\hpo_panel_cli.py panel data\raw\v66.p1_1240K.aadr.patch.PUB.snp ^
  --build GRCh37 --rotulo "AADR v66.p1 1240K"
```

`--build` é **obrigatório e não é inferido**: coordenada sem montagem
declarada não significa nada.

A ferramenta então **verifica a declaração contra o próprio arquivo**. Uma
posição não pode exceder o comprimento do cromossomo naquela montagem, e
GRCh37 e GRCh38 têm comprimentos diferentes — logo, uma posição que cabe
numa e estoura na outra decide sozinha. Veredictos possíveis:

| veredicto | significado | saída |
|---|---|---|
| `consistente` | a evidência interna confirma o build declarado | 0 |
| `inconclusivo` | todas as posições cabem nos dois builds | 0, com aviso |
| `contradiz_declaracao` | o arquivo só cabe no outro build | **1** |
| `contraditorio` | há evidência para os dois | **1** |
| `impossivel` | posição maior que qualquer montagem | **1** |

No arquivo real do AADR: 15 cromossomos só cabem em GRCh37, nenhum aponta
para GRCh38 — **GRCh37 confirmado sem consultar documentação externa**.

Por que isso não é preciosismo: o próximo passo é cruzar variantes
patogênicas com estas posições. Interseção entre builds diferentes roda
sem erro, devolve um número plausível e está cientificamente errada. Essa
verificação é o que impede isso.

---

## 6. `clinvar` — variantes patogênicas

Baixe **pelo navegador ou PowerShell** (a ferramenta não baixa nada):

```
Invoke-WebRequest https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz -OutFile data\raw\variant_summary.txt.gz
python scripts\hpo_panel_cli.py clinvar --build GRCh37
```

**Entrada:** `variant_summary.txt.gz` (várias centenas de MB). `--build` é
obrigatório e precisa ser o do painel — o AADR 1240K é GRCh37.

**O que faz, em ordem, contando cada exclusão:**

1. fica só com as linhas do build declarado (o arquivo traz cada variante em
   GRCh37 **e** GRCh38; nenhum liftover é feito);
2. fica só com origem germinativa (somática é de tumor, não é herdada);
3. fica só com `Pathogenic`, `Likely pathogenic` ou
   `Pathogenic/Likely pathogenic`. `Conflicting classifications` sai e é
   **contado à parte**;
4. descarta posição ausente (o ClinVar marca com `-1`).

Traduz `Orphanet:100` para `ORPHA:100`, senão nenhuma variante do Orphanet
casaria com as doenças da HPO.

**Saída:** `data\processed\clinvar_pathogenic.csv` (fora do git, grande) e
`clinvar_pathogenic_metadata.json`, com o funil completo, estrelas de revisão
e a data de avaliação mais recente — o arquivo não declara versão, e isso
fica registrado.

---

## 7. `coverage` — de quantas doenças o painel fala

```
python scripts\hpo_panel_cli.py coverage data\raw\v66.p1_1240K.aadr.patch.PUB.snp --build GRCh37 --rotulo "AADR v66.p1 1240K"
python scripts\hpo_panel_cli.py coverage ... --estrelas-minimas 2
```

**Entrada:** os snapshots de `snapshot` e `clinvar`, mais o `.snp`. O build
do painel é verificado de novo; builds divergentes são recusados.

**O que faz:** para cada doença com perfil fenotípico e gene associado,
encontra as variantes patogênicas ligadas **diretamente** a ela (campo
`PhenotypeIDS` do ClinVar, não pelo gene) e classifica a doença pelo ponto
mais fundo que alcança:

| nível | significado |
|---|---|
| sem variante patogênica | nada no ClinVar ligado a ela |
| só não-SNV | só indel, CNV etc. — painel de SNP não observa |
| SNV fora do painel | há SNV, nenhuma em posição ensaiada |
| posição ensaiada, alelos diferentes | o painel está lá, mas pergunta "G ou A?" e a variante é G>T |
| casa pela fita oposta | provável, precisa confirmar orientação |
| **alelo patogênico ensaiado** | **o painel distingue exatamente ref e alt** |

Só o último nível permite perguntar se um indivíduo antigo carrega a
variante. Estar na posição **não basta**: em DNA antigo, com chamada
pseudo-haploide, uma leitura com um alelo que o painel não ensaia é
descartada.

Relata dois universos: doenças com gene mendeliano declarado pelo OMIM, e
doenças com qualquer gene associado (inclui o Orphanet).

**Saída:** `data\processed\target_coverage.csv` (uma linha por doença, com
nível, contagens e IDs das variantes casadas) e
`target_coverage_metadata.json`, com o funil.

Isto mede se a pergunta **pode ser feita**, não se alguém carrega a variante.

---

## Como testar que a aplicação está correta

Suíte completa:

```
python -m pytest -q
```

Mas o teste que prova alguma coisa é o que mostra a ferramenta **reprovando
o caso errado**:

```
:: declara o build errado de propósito — deve acusar e sair com 1
python scripts\hpo_panel_cli.py panel data\raw\v66.p1_1240K.aadr.patch.PUB.snp --build GRCh38
echo %ERRORLEVEL%

:: identificador inexistente — deve falhar, não devolver lista vazia
python scripts\hpo_panel_cli.py term HP:1234567
python scripts\hpo_panel_cli.py profile OMIM:999999
```

Uma verificação que nunca reprova nada não está verificando nada.

---

## O que ainda não existe

- Expansão por ancestrais no grafo da HPO (o termo consultado não alcança
  seus descendentes). Atenção: `path_to_root` em `ontology.py` **não** serve
  para isso — percorre um caminho único num grafo de múltiplos pais e perde
  cerca de 42% dos ancestrais reais.
- Busca de termo HPO por rótulo.
