# Alcance Genômico

Mede **de quais doenças monogênicas um conjunto de dados de DNA antigo permite perguntar** se um indivíduo carrega a variante causadora.

Comando: `alcance`. Repositório: `hpo-ptbr-lab`. Usa só a biblioteca padrão do Python 3.11+, sem dependências. Não faz diagnóstico.

**Termo usado:** *painel de genotipagem* é a lista fixa de posições do DNA que um conjunto de dados lê em todos os indivíduos. O *painel 1240K* do AADR lê 1,2 milhão de posições. "Painel" neste projeto sempre tem esse sentido.

---

## O que a ferramenta responde

**1. De quais doenças os dados permitem perguntar?** Cruza quatro fontes públicas:

```text
doença ── gene ── variante patogênica ── posição e alelos lidos pelo painel de genotipagem
 (HPO)    (HPO)        (ClinVar)              (arquivo .snp, ex.: painel 1240K do AADR)
```

**2. Quem são os indivíduos do conjunto de dados?** Descreve os metadados do AADR (arquivo `.anno`): local, data, tipo de sequenciamento, cobertura. Só descreve, sem filtrar nem classificar ninguém.

As duas perguntas são independentes: o cruzamento da pergunta 1 não usa o `.anno`.

---

## Instalação

```
git clone https://github.com/OdimarFalcao/hpo-ptbr-lab.git
cd hpo-ptbr-lab
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
```

Isso registra o comando `alcance`. Ele só existe com o ambiente ativo (o prompt começa com `(.venv)`). Sem instalar, use `python scripts\alcance.py` no lugar de `alcance`.

---

## Fontes de dados

A ferramenta não baixa nada. Salve cada arquivo em `data\raw\` (fora do git).

| arquivo | conteúdo | versão em uso | download |
|---|---|---|---|
| `phenotype.hpoa` | doença → fenótipos | HPO 2026-06-23 | `curl.exe -L -o data\raw\phenotype.hpoa https://github.com/obophenotype/human-phenotype-ontology/releases/download/v2026-06-23/phenotype.hpoa` |
| `genes_to_disease.txt` | gene ↔ doença | HPO 2026-06-23 | `curl.exe -L -o data\raw\genes_to_disease.txt https://github.com/obophenotype/human-phenotype-ontology/releases/download/v2026-06-23/genes_to_disease.txt` |
| `variant_summary.txt.gz` | variantes do ClinVar (~420 MB) | setembro de 2026 | `curl.exe -L -C - -o data\raw\variant_summary.txt.gz https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz` |
| `v66.p1_1240K.aadr.patch.PUB.snp` | posições do painel 1240K do AADR | v66.p1 | [Harvard Dataverse, doi:10.7910/DVN/FFIDCW](https://doi.org/10.7910/DVN/FFIDCW) (baixar pelo navegador) |
| `v66.p1_1240K.aadr.PUB.anno` | metadados dos indivíduos do AADR | v66.p1 | mesma coleção no Harvard Dataverse (baixar pelo navegador) |

Os nomes do `.snp` e do `.anno` diferem (`patch`). A correspondência entre os dois ainda não foi confirmada, e o manifesto do `anno` registra isso.

Para conferir se o ClinVar chegou inteiro, compare o MD5 do arquivo com o publicado pelo NCBI:

```
curl.exe -L -o data\raw\variant_summary.txt.gz.md5 https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz.md5
Get-Content data\raw\variant_summary.txt.gz.md5
(Get-FileHash data\raw\variant_summary.txt.gz -Algorithm MD5).Hash.ToLower()
```

Os rótulos em português e o índice da ontologia (`data\processed\hpo_ptbr.csv`, `hpo_ontology.json.gz`, `metadata.json`) **já estão no repositório**, na release HPO 2026-06-23 com a tradução no commit `62f1d254`. Só precisam ser regenerados se a release mudar; veja [Trocar de release](#trocar-de-release).

---

## Uso: primeira execução, em ordem

```
alcance snapshot
alcance panel data\raw\v66.p1_1240K.aadr.patch.PUB.snp --build GRCh37 --rotulo "AADR v66.p1 1240K"
alcance clinvar --build GRCh37
alcance coverage data\raw\v66.p1_1240K.aadr.patch.PUB.snp --build GRCh37 --rotulo "AADR v66.p1 1240K"
alcance anno data\raw\v66.p1_1240K.aadr.PUB.anno
```

Os quatro primeiros respondem à pergunta 1; o último, à pergunta 2. Depois disso, as consultas (`search`, `profile`, `term`) podem ser usadas quantas vezes quiser.

---

## Comandos

**Pergunta 1: de quais doenças os dados permitem perguntar**

| comando | o que faz | exemplo |
|---|---|---|
| `snapshot` | Normaliza `phenotype.hpoa` e `genes_to_disease.txt`. Recusa a execução se a release não bater com a da ontologia. | `alcance snapshot` |
| `search` | Acha o identificador de uma doença pelo nome. | `alcance search "ataxia"` |
| `profile` | Doença → fenótipos e genes. | `alcance profile OMIM:224900` |
| `term` | Fenótipo → doenças que o apresentam → genes. | `alcance term HP:0001251` |
| `panel` | Caracteriza um `.snp` e **verifica** o build declarado contra o próprio arquivo. Sai com erro se a declaração for contradita. | `alcance panel <arquivo.snp> --build GRCh37` |
| `clinvar` | Filtra o ClinVar: build declarado, origem germinativa, Pathogenic/Likely pathogenic. Conta cada exclusão. | `alcance clinvar --build GRCh37` |
| `coverage` | Cruza doenças × ClinVar × painel de genotipagem e classifica cada doença pelo ponto mais fundo que alcança. | `alcance coverage <arquivo.snp> --build GRCh37` |

**Pergunta 2: quem são os indivíduos**

| comando | o que faz | exemplo |
|---|---|---|
| `anno` | Descreve as colunas e os valores do `.anno` do AADR: registros, indivíduos distintos, registros atuais, local, tipo de dado, cobertura e data. Não filtra nem classifica. | `alcance anno data\raw\v66.p1_1240K.aadr.PUB.anno` |

**Opções**

| comando | opção | efeito |
|---|---|---|
| `profile` | `--somente-mendelianas` | só genes com associação mendeliana |
| `profile` | `--aspects P C I M H` | P fenótipo (padrão), C curso, I herança, M modificador, H história |
| `term` | `--somente-mendelianas` | só doenças com gene mendeliano |
| `term` | `--somente-com-gene` | só doenças com algum gene associado |
| `term`, `search` | `--limite N` | quantas linhas exibir |
| `profile`, `term` | `--json` | saída estruturada, para uso em scripts |
| `panel`, `coverage` | `--rotulo "nome"` | nome do painel de genotipagem no relatório |
| `clinvar` | `--incluir-origem-desconhecida` | aceita também origem `unknown`/`not provided` |
| `coverage` | `--estrelas-minimas 0-4` | exige nível mínimo de revisão no ClinVar |
| `panel`, `anno` | `--url` | URL de origem, registrada no manifesto |

`--build` é obrigatório em `panel`, `clinvar` e `coverage`. O painel 1240K do AADR é **GRCh37**.

---

## Arquivos gerados

Todos ficam em `data\processed\`. Cada `*_metadata.json` registra o sha256 da fonte, a versão (ou o registro de que a fonte não declara versão) e as contagens de cada etapa.

| arquivo | gerado por | no git |
|---|---|---|
| `hpo_annotations.csv` + `hpoa_metadata.json` | `snapshot` | só o manifesto (o CSV tem 37 MB) |
| `gene_disease.csv` + `gene_disease_metadata.json` | `snapshot` | sim |
| `genotype_panel_metadata.json` | `panel` | sim |
| `clinvar_pathogenic.csv` + `clinvar_pathogenic_metadata.json` | `clinvar` | só o manifesto |
| `target_coverage.csv` + `target_coverage_metadata.json` | `coverage` | sim |
| `aadr_anno_metadata.json` | `anno` | sim |

`target_coverage.csv` tem uma linha por doença, com o nível alcançado e os identificadores das variantes. Se o ClinVar foi ingerido com `--incluir-origem-desconhecida`, os arquivos levam o sufixo `_origem_ampliada` e não sobrescrevem os do recorte padrão.

---

## Resultado atual

**Pergunta 1.** Painel 1240K do AADR (v66.p1) × ClinVar de 11/09/2026:

| | |
|---|---|
| SNV patogênicas no ClinVar (GRCh37) | 178.934 |
| em posição lida pelo painel 1240K | 108 |
| com os alelos certos | 54 (52 variantes, 17 genes) |
| doenças mendelianas (OMIM) alcançadas | **33 de 6.484** |
| incluindo Orphanet | 56 de 9.142 |

O conjunto de doenças é o mesmo com ou sem `--incluir-origem-desconhecida`.

**Pergunta 2.** Metadados do AADR v66.p1:

| | |
|---|---|
| registros (linhas) | 23.089 |
| indivíduos distintos | 21.433 |
| registros de pessoas atuais | 3.970 |
| registros do Brasil | 87 |

Uma mesma pessoa pode aparecer em mais de uma linha, e os registros atuais estão incluídos no total. Por isso "23.089" não é o número de indivíduos antigos.

Relatório: `docs\relatorios\o_que_os_dados_permitem_perguntar.docx`.

---

## Limitações

- Mede se a pergunta **pode ser feita** com o painel de genotipagem. Não mede se alguém carrega a variante: os genótipos dos indivíduos (`.geno`) não são lidos.
- Considera só SNV: um painel de genotipagem de SNPs não observa inserções, deleções ou variação estrutural.
- Considera só a anotação direta da HPO, sem expansão pela hierarquia da ontologia.
- O `anno` descreve o `.anno`, mas ainda não há critérios para recortar indivíduos (país, antigo ou atual, genoma inteiro ou captura, cobertura).
- Termo sem rótulo oficial em português aparece em inglês, marcado `[sem PT]`, e nunca é traduzido automaticamente.

---

## Testes

```
python -m pytest -q
```

---

## Trocar de release

Salve `hp.json` e `hp-pt.babelon.tsv` da nova release em `data\raw\` e rode:

```
python scripts\build_snapshot.py
python scripts\build_ontology_index.py
alcance snapshot
```

Baixe `phenotype.hpoa` e `genes_to_disease.txt` **da mesma release**. O `snapshot` recusa um `phenotype.hpoa` de outra release; o `genes_to_disease.txt` não declara versão, então a verificação possível é a sobreposição de doenças registrada no manifesto.

---

## Documentação

- [`docs/USO_ALCANCE.md`](docs/USO_ALCANCE.md): entrada e saída de cada comando, em detalhe.
- [`AGENTS.md`](AGENTS.md): termos, regras e riscos conhecidos, para quem mexe no código.

A bancada de anotação de texto clínico que existia neste repositório está preservada na etiqueta `frente-a-final` (`git checkout frente-a-final`).
