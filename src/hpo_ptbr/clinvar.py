"""Variantes patogênicas do ClinVar (`variant_summary.txt.gz`).

Quarta fonte do Alcance Genômico, e a primeira fora da HPO:

- `hp.json`             -> vocabulário de fenótipos
- `phenotype.hpoa`      -> doença apresenta fenótipo
- `genes_to_disease`    -> gene associado a doença
- `variant_summary`     -> **qual alteração exata no DNA** causa a doença

É ela que permite a pergunta ao painel de genotipagem: o que se procura no genoma
não é o gene, é a posição e o alelo da variante patogênica.

## Filtros, em ordem, todos contabilizados no manifesto

1. **Build.** O arquivo traz cada variante duas vezes, uma linha por
   montagem (GRCh37 e GRCh38). Fica só o build declarado. Nenhum liftover.
2. **Origem germinativa.** Variante somática (de tumor) não é herdada e não
   pertence a doença monogênica.
3. **Classificação.** Fica só `Pathogenic`, `Likely pathogenic` e
   `Pathogenic/Likely pathogenic`. `Conflicting classifications` sai e é
   contado à parte: é o grupo onde submetedores discordam, e o número
   precisa estar visível.

Nada é descartado sem contagem. O funil fica no manifesto.

## O que o arquivo não declara

Não há versão no cabeçalho. O manifesto registra o sha256 e a data de
avaliação mais recente encontrada nas linhas, que serve de aproximação da
data de corte. Não é a versão; é o melhor que o arquivo permite dizer.
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .hashing import content_sha256, raw_sha256

# O ClinVar renomeou a coluna de classificação germinativa em 2024. As duas
# grafias sao aceitas; qualquer outra coisa falha nomeando o cabecalho lido.
SIGNIFICANCE_COLUMNS = ("ClinicalSignificance", "GermlineClassification")

REQUIRED_COLUMNS = (
    "#AlleleID",
    "Type",
    "GeneID",
    "GeneSymbol",
    "PhenotypeIDS",
    "PhenotypeList",
    "OriginSimple",
    "Assembly",
    "Chromosome",
    "ReviewStatus",
    "VariationID",
    "PositionVCF",
    "ReferenceAlleleVCF",
    "AlternateAlleleVCF",
)

ACCEPTED_SIGNIFICANCE = frozenset(
    {"Pathogenic", "Likely pathogenic", "Pathogenic/Likely pathogenic"}
)
CONFLICTING = "Conflicting classifications of pathogenicity"
ACCEPTED_ORIGIN = frozenset({"germline", "germline/somatic"})
# Muitos laboratorios clinicos submetem sem declarar a origem. Para doenca
# mendeliana isso quase sempre e germinativo, mas "quase sempre" e decisao
# metodologica, nao do codigo: fica atras de uma opcao explicita.
UNDECLARED_ORIGIN = frozenset({"unknown", "not provided"})

# Estrelas de revisao, na convencao do proprio ClinVar.
REVIEW_STARS = {
    "practice guideline": 4,
    "reviewed by expert panel": 3,
    "criteria provided, multiple submitters, no conflicts": 2,
    "criteria provided, single submitter": 1,
    "criteria provided, conflicting classifications": 1,
    "criteria provided, conflicting interpretations": 1,
}

SNV = "single nucleotide variant"

SNAPSHOT_COLUMNS = (
    "variation_id",
    "allele_id",
    "gene_symbol",
    "gene_id",
    "variant_type",
    "clinical_significance",
    "review_status",
    "review_stars",
    "chromosome",
    "position",
    "ref",
    "alt",
    "disease_ids",
    "phenotype_list",
)

_OMIM = re.compile(r"\bOMIM:(\d{6})\b")
_ORPHANET = re.compile(r"\bOrphanet:(\d+)\b")
_DATA = re.compile(r"([A-Z][a-z]{2} \d{2}, \d{4})")


@dataclass(frozen=True)
class PathogenicVariant:
    variation_id: str
    allele_id: str
    gene_symbol: str
    gene_id: str
    variant_type: str
    clinical_significance: str
    review_status: str
    review_stars: int
    chromosome: str
    position: int
    ref: str
    alt: str
    disease_ids: tuple[str, ...]
    phenotype_list: str

    @property
    def is_snv(self) -> bool:
        return self.variant_type == SNV

    def to_row(self) -> dict[str, object]:
        linha = asdict(self)
        linha["disease_ids"] = ";".join(self.disease_ids)
        return linha


def disease_ids_from_phenotype_field(valor: str) -> tuple[str, ...]:
    """Extrai OMIM e Orphanet de `PhenotypeIDS`, no vocabulario da HPO.

    O ClinVar escreve `Orphanet:100`; a HPO escreve `ORPHA:100`. Sem essa
    traducao, nenhuma variante do Orphanet casaria com as doenças-alvo.
    """
    omim = {f"OMIM:{n}" for n in _OMIM.findall(valor)}
    orpha = {f"ORPHA:{n}" for n in _ORPHANET.findall(valor)}
    return tuple(sorted(omim | orpha))


def primary_significance(valor: str) -> str:
    """`Pathogenic; risk factor` -> `Pathogenic`. O primeiro termo e a classificacao."""
    return valor.split(";")[0].strip()


def _abrir(source: Path) -> io.TextIOBase:
    if source.suffix == ".gz":
        return io.TextIOWrapper(gzip.open(source, "rb"), encoding="utf-8", newline="")
    return source.open(encoding="utf-8", newline="")


def _coluna_de_classificacao(cabecalho: list[str], source: Path) -> str:
    faltando = [c for c in REQUIRED_COLUMNS if c not in cabecalho]
    presentes = [c for c in SIGNIFICANCE_COLUMNS if c in cabecalho]
    if faltando or not presentes:
        raise ValueError(
            f"Cabeçalho inesperado em {source.name}. "
            f"Colunas ausentes: {faltando + ([] if presentes else list(SIGNIFICANCE_COLUMNS))}. "
            f"Cabeçalho encontrado: {cabecalho}. "
            "Confirme que o arquivo é o variant_summary.txt.gz do ClinVar."
        )
    return presentes[0]


def build_snapshot(
    source_path: str | Path,
    output_csv: str | Path,
    output_metadata: str | Path,
    *,
    genome_build: str,
    source_url: str = "",
    output_csv_label: str = "",
    include_undeclared_origin: bool = False,
) -> dict[str, object]:
    """Filtra o ClinVar para variantes patogênicas germinativas num build.

    `include_undeclared_origin` aceita tambem origem `unknown`/`not provided`.
    O manifesto registra a escolha e, nos dois casos, quantas variantes
    patogenicas cada origem excluida levou embora.
    """
    origens_aceitas = ACCEPTED_ORIGIN | (UNDECLARED_ORIGIN if include_undeclared_origin else frozenset())
    if genome_build not in ("GRCh37", "GRCh38"):
        raise ValueError(
            f"Build precisa ser declarado: GRCh37 ou GRCh38. Recebido: {genome_build!r}."
        )
    source = Path(source_path)

    funil = Counter()
    classificacoes_excluidas: Counter[str] = Counter()
    origens_excluidas: Counter[str] = Counter()
    patogenicas_excluidas_por_origem: Counter[str] = Counter()
    datas: list[datetime] = []
    variantes: dict[str, PathogenicVariant] = {}

    with _abrir(source) as handle:
        leitor = csv.reader(handle, delimiter="\t")
        cabecalho = next(leitor)
        coluna_sig = _coluna_de_classificacao(cabecalho, source)
        idx = {nome: i for i, nome in enumerate(cabecalho)}
        idx_data = idx.get("LastEvaluated")

        for campos in leitor:
            if len(campos) < len(cabecalho):
                funil["linhas_malformadas"] += 1
                continue
            funil["linhas_lidas"] += 1

            if campos[idx["Assembly"]] != genome_build:
                continue
            funil["no_build"] += 1

            origem = campos[idx["OriginSimple"]]
            classificacao = primary_significance(campos[idx[coluna_sig]])
            if origem not in origens_aceitas:
                origens_excluidas[origem] += 1
                # Contar tudo que saiu por origem misturaria benignas com
                # patogenicas e esconderia o que de fato importa.
                if classificacao in ACCEPTED_SIGNIFICANCE:
                    patogenicas_excluidas_por_origem[origem] += 1
                continue
            funil["germinativas"] += 1

            if classificacao not in ACCEPTED_SIGNIFICANCE:
                classificacoes_excluidas[classificacao] += 1
                continue
            funil["patogenicas"] += 1

            # O ClinVar marca posicao ausente com -1 ou "na". "-1" converte para
            # inteiro sem erro, entao so o try/except deixaria passar uma
            # variante sem coordenada.
            try:
                posicao = int(campos[idx["PositionVCF"]])
            except ValueError:
                posicao = 0
            if posicao <= 0:
                funil["sem_posicao_vcf"] += 1
                continue

            revisao = campos[idx["ReviewStatus"]]
            variante = PathogenicVariant(
                variation_id=campos[idx["VariationID"]],
                allele_id=campos[idx["#AlleleID"]],
                gene_symbol=campos[idx["GeneSymbol"]],
                gene_id=campos[idx["GeneID"]],
                variant_type=campos[idx["Type"]],
                clinical_significance=classificacao,
                review_status=revisao,
                review_stars=REVIEW_STARS.get(revisao, 0),
                chromosome=campos[idx["Chromosome"]].upper(),
                position=posicao,
                ref=campos[idx["ReferenceAlleleVCF"]].upper(),
                alt=campos[idx["AlternateAlleleVCF"]].upper(),
                disease_ids=disease_ids_from_phenotype_field(campos[idx["PhenotypeIDS"]]),
                phenotype_list=campos[idx["PhenotypeList"]],
            )
            # Uma variante pode aparecer em mais de uma linha (alelos
            # diferentes da mesma VariationID). A chave inclui o alelo.
            chave = f"{variante.variation_id}:{variante.alt}"
            if chave in variantes:
                funil["duplicatas"] += 1
                continue
            variantes[chave] = variante

            if idx_data is not None:
                achada = _DATA.search(campos[idx_data])
                if achada:
                    datas.append(datetime.strptime(achada.group(1), "%b %d, %Y"))

    if not variantes:
        raise ValueError(
            f"Nenhuma variante patogênica germinativa em {genome_build} encontrada em "
            f"{source.name}. Funil: {dict(funil)}."
        )

    ordenadas = sorted(
        variantes.values(),
        key=lambda v: (_ordem_cromossomo(v.chromosome), v.position, v.variation_id, v.alt),
    )

    csv_path = Path(output_csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SNAPSHOT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for variante in ordenadas:
            writer.writerow(variante.to_row())

    tipos = Counter(v.variant_type for v in ordenadas)
    estrelas = Counter(v.review_stars for v in ordenadas)
    com_doenca = sum(1 for v in ordenadas if v.disease_ids)

    manifest = {
        "schema_version": "clinvar-pathogenic-snapshot-manifest-v1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source": {
            "url": source_url,
            "file": source.name,
            "sha256": raw_sha256(source),
            "declares_release": False,
            "latest_last_evaluated": max(datas).date().isoformat() if datas else None,
            "significance_column": coluna_sig,
            "note": (
                "variant_summary nao declara versao. latest_last_evaluated e a data "
                "de avaliacao mais recente nas linhas retidas: aproxima a data de "
                "corte, nao e a versao."
            ),
        },
        "genome_build": {"declared": genome_build, "liftover": False},
        "filters": {
            "origin_accepted": sorted(origens_aceitas),
            "include_undeclared_origin": include_undeclared_origin,
            "significance_accepted": sorted(ACCEPTED_SIGNIFICANCE),
        },
        "funnel": {
            "rows_read": funil["linhas_lidas"],
            "rows_in_build": funil["no_build"],
            "germline": funil["germinativas"],
            "pathogenic_or_likely": funil["patogenicas"],
            "without_vcf_position": funil["sem_posicao_vcf"],
            "duplicates": funil["duplicatas"],
            "malformed_rows": funil["linhas_malformadas"],
            "retained": len(ordenadas),
        },
        "excluded": {
            "conflicting_classifications": classificacoes_excluidas.get(CONFLICTING, 0),
            "by_significance_top": dict(classificacoes_excluidas.most_common(12)),
            "by_origin": dict(origens_excluidas.most_common()),
            "pathogenic_by_origin": dict(patogenicas_excluidas_por_origem.most_common()),
            "note": (
                "by_origin conta todas as classificacoes; pathogenic_by_origin conta "
                "so as patogenicas/provaveis que o filtro de origem removeu."
            ),
        },
        "retained": {
            "by_variant_type": dict(tipos.most_common()),
            "snv": tipos.get(SNV, 0),
            "by_review_stars": {str(k): estrelas[k] for k in sorted(estrelas)},
            "genes": len({v.gene_symbol for v in ordenadas if v.gene_symbol}),
            "linked_to_omim_or_orphanet": com_doenca,
            "without_disease_link": len(ordenadas) - com_doenca,
        },
        "outputs": {
            "csv": output_csv_label or csv_path.name,
            "csv_sha256": content_sha256(csv_path),
        },
    }
    Path(output_metadata).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def _ordem_cromossomo(nome: str) -> tuple[int, str]:
    return (int(nome), "") if nome.isdigit() else (99, nome)


def load_snapshot(csv_path: str | Path) -> tuple[PathogenicVariant, ...]:
    with Path(csv_path).open(encoding="utf-8", newline="") as handle:
        variantes = tuple(
            PathogenicVariant(
                variation_id=linha["variation_id"],
                allele_id=linha["allele_id"],
                gene_symbol=linha["gene_symbol"],
                gene_id=linha["gene_id"],
                variant_type=linha["variant_type"],
                clinical_significance=linha["clinical_significance"],
                review_status=linha["review_status"],
                review_stars=int(linha["review_stars"]),
                chromosome=linha["chromosome"],
                position=int(linha["position"]),
                ref=linha["ref"],
                alt=linha["alt"],
                disease_ids=tuple(d for d in linha["disease_ids"].split(";") if d),
                phenotype_list=linha["phenotype_list"],
            )
            for linha in csv.DictReader(handle)
        )
    if not variantes:
        raise ValueError(f"Snapshot ClinVar vazio: {csv_path}")
    return variantes
