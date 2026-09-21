"""Viabilidade do painel de alvos: de quantas doenças o painel genotipado fala.

Cruza as quatro fontes:

    doença (phenotype.hpoa) ── gene (genes_to_disease) ── variante patogênica
    (ClinVar) ── posição e alelos ensaiados (.snp do painel)

e classifica cada doença pelo **ponto mais fundo que alcança** no funil:

    1. sem_variante_patogenica   nenhuma variante P/LP germinativa ligada a ela
    2. sem_snv                   só há variantes que não são SNV (indel, CNV...)
    3. snv_fora_do_painel        há SNV, mas em nenhuma posição ensaiada
    4. posicao_alelo_diferente   o painel está na posição, mas ensaia outros alelos
    5. alelo_por_fita_oposta     casa pela fita complementar (provável, não confirmado)
    6. alelo_patogenico_ensaiado o painel distingue exatamente ref e alt

Só o nível 6 permite perguntar "este indivíduo antigo carrega a variante".
O nível 5 provavelmente também, após confirmar a orientação da fita.

## Decisões que definem o número

- **Ligação variante→doença é direta**, pelo campo `PhenotypeIDS` do ClinVar,
  não pelo gene. Um gene pode causar várias doenças; uma variante no gene
  não é evidência para todas elas.
- **Por que só SNV.** Um painel de SNPs genotipa posições, com dois alelos
  cada. Deleção, duplicação e inserção não são observáveis por ele, mesmo
  quando a posição inicial coincide.
- **Dois universos de doenças são relatados**: as com gene declarado
  mendeliano pelo OMIM, e as com qualquer gene associado. A diferença é o
  Orphanet, que não classifica o tipo de associação.

Isto mede se a pergunta **pode ser feita** com esses dados. Não mede
frequência, penetrância, nem se algum indivíduo carrega a variante.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from .clinvar import PathogenicVariant
from .gene_disease import MENDELIAN, GeneDiseaseIndex
from .genotype_panel import PanelIndex, check_coverage, classify_allele
from .hashing import content_sha256
from .hpoa import HpoaIndex

TIERS = (
    "sem_variante_patogenica",
    "sem_snv",
    "snv_fora_do_painel",
    "posicao_alelo_diferente",
    "alelo_por_fita_oposta",
    "alelo_patogenico_ensaiado",
)

TIER_LABELS = {
    "sem_variante_patogenica": "sem variante patogênica ligada no ClinVar",
    "sem_snv": "só variantes que não são SNV",
    "snv_fora_do_painel": "SNV, mas nenhuma em posição ensaiada",
    "posicao_alelo_diferente": "posição ensaiada, alelos diferentes",
    "alelo_por_fita_oposta": "alelo casa pela fita oposta",
    "alelo_patogenico_ensaiado": "alelo patogênico ensaiado",
}

REPORT_COLUMNS = (
    "disease_id",
    "disease_name",
    "tier",
    "has_mendelian_gene",
    "genes",
    "pathogenic_variants",
    "pathogenic_snv",
    "snv_at_panel_position",
    "allele_match",
    "strand_flip_match",
    "best_review_stars_matched",
    "matched_variation_ids",
)


def _nivel(contagem: dict[str, int]) -> str:
    if contagem["allele_match"]:
        return "alelo_patogenico_ensaiado"
    if contagem["strand_flip_match"]:
        return "alelo_por_fita_oposta"
    if contagem["position"]:
        return "posicao_alelo_diferente"
    if contagem["snv"]:
        return "snv_fora_do_painel"
    if contagem["plp"]:
        return "sem_snv"
    return "sem_variante_patogenica"


def assess_targets(
    hpoa_index: HpoaIndex,
    gene_index: GeneDiseaseIndex,
    variants: tuple[PathogenicVariant, ...],
    variants_genome_build: str,
    panel: PanelIndex,
    panel_alleles: dict[tuple[str, int], tuple[tuple[str, str], ...]],
    *,
    min_review_stars: int = 0,
) -> dict[str, object]:
    """Classifica cada doença-alvo pelo nível que alcança no funil."""
    # A recusa de builds divergentes mora em check_coverage; passar por ela
    # garante que nenhum caminho deste modulo a contorne.
    snvs = [v for v in variants if v.is_snv and v.review_stars >= min_review_stars]
    cobertura = check_coverage(
        panel,
        [{"chromosome": v.chromosome, "position": v.position, "_v": v} for v in snvs],
        variants_genome_build,
    )
    na_posicao = {id(item["_v"]) for item in cobertura["assayed"]}

    relacao_alelo: dict[int, str] = {}
    for item in cobertura["assayed"]:
        variante: PathogenicVariant = item["_v"]
        pares = panel_alleles.get((variante.chromosome, variante.position), ())
        relacao_alelo[id(variante)] = classify_allele(variante.ref, variante.alt, pares)

    # Doencas com perfil fenotipico: o universo sao as que a HPO descreve.
    com_perfil = {
        a.database_id: a.disease_name
        for a in hpoa_index.annotations
        if a.aspect == "P" and not a.excluded
    }
    genes_por_doenca: dict[str, set[str]] = {}
    mendeliana: set[str] = set()
    for associacao in gene_index.associations:
        if associacao.disease_id not in com_perfil:
            continue
        genes_por_doenca.setdefault(associacao.disease_id, set()).add(associacao.gene_symbol)
        if associacao.association_type == MENDELIAN:
            mendeliana.add(associacao.disease_id)

    variantes_por_doenca: dict[str, list[PathogenicVariant]] = {}
    ignoradas_por_estrela = 0
    for variante in variants:
        if variante.review_stars < min_review_stars:
            ignoradas_por_estrela += 1
            continue
        for doenca in variante.disease_ids:
            if doenca in genes_por_doenca:
                variantes_por_doenca.setdefault(doenca, []).append(variante)

    linhas = []
    for doenca in sorted(genes_por_doenca):
        ligadas = variantes_por_doenca.get(doenca, [])
        contagem = {"plp": len(ligadas), "snv": 0, "position": 0,
                    "allele_match": 0, "strand_flip_match": 0}
        casadas: list[PathogenicVariant] = []
        for variante in ligadas:
            if not (variante.is_snv and variante.review_stars >= min_review_stars):
                continue
            contagem["snv"] += 1
            if id(variante) not in na_posicao:
                continue
            contagem["position"] += 1
            relacao = relacao_alelo[id(variante)]
            if relacao in ("allele_match", "strand_flip_match"):
                contagem[relacao] += 1
                casadas.append(variante)
        linhas.append(
            {
                "disease_id": doenca,
                "disease_name": com_perfil[doenca],
                "tier": _nivel(contagem),
                "has_mendelian_gene": doenca in mendeliana,
                "genes": ";".join(sorted(genes_por_doenca[doenca])),
                "pathogenic_variants": contagem["plp"],
                "pathogenic_snv": contagem["snv"],
                "snv_at_panel_position": contagem["position"],
                "allele_match": contagem["allele_match"],
                "strand_flip_match": contagem["strand_flip_match"],
                "best_review_stars_matched": max((v.review_stars for v in casadas), default=""),
                "matched_variation_ids": ";".join(sorted({v.variation_id for v in casadas})),
            }
        )

    def funil(filtro) -> dict[str, object]:
        selecionadas = [l for l in linhas if filtro(l)]
        por_nivel = Counter(l["tier"] for l in selecionadas)
        total = len(selecionadas)
        return {
            "diseases": total,
            "by_tier": {t: por_nivel.get(t, 0) for t in TIERS},
            "percent_allele_assayed": (
                round(100 * por_nivel.get("alelo_patogenico_ensaiado", 0) / total, 2)
                if total else None
            ),
        }

    relacoes = Counter(relacao_alelo.values())
    return {
        "schema_version": "target-coverage-v1",
        "genome_build": panel.genome_build,
        "panel_label": panel.panel_label,
        "min_review_stars": min_review_stars,
        "universes": {
            "mendelian_declared_by_omim": funil(lambda l: l["has_mendelian_gene"]),
            "any_gene_association": funil(lambda l: True),
        },
        "variants": {
            "pathogenic_retained": len(variants),
            "ignored_below_min_stars": ignoradas_por_estrela,
            "snv_considered": len(snvs),
            "snv_at_panel_position": len(na_posicao),
            "allele_match": relacoes.get("allele_match", 0),
            "strand_flip_match": relacoes.get("strand_flip_match", 0),
            "different_alleles": relacoes.get("different_alleles", 0),
        },
        "diseases": linhas,
        "limitations": [
            "Mede se a pergunta pode ser feita com o painel, não se algum indivíduo "
            "carrega a variante.",
            "Posição ensaiada não garante genótipo observado: cobertura, dano pós-morte "
            "e filtros de qualidade decidem isso por amostra.",
            "Ligação variante→doença pelo PhenotypeIDS do ClinVar; variante sem esse "
            "vínculo não conta para nenhuma doença.",
            "Somente SNV: um painel de SNPs não observa indels nem variação estrutural.",
            "Casamento pela fita oposta é provável, não confirmado.",
        ],
    }


def write_report(
    resultado: dict[str, object],
    output_csv: str | Path,
    output_metadata: str | Path,
    *,
    sources: dict[str, object],
    output_csv_label: str = "",
) -> dict[str, object]:
    """Grava o relatório por doença e o manifesto com o funil."""
    csv_path = Path(output_csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for linha in resultado["diseases"]:
            writer.writerow(linha)

    manifest = {
        "schema_version": "target-coverage-manifest-v1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "sources": sources,
        "genome_build": resultado["genome_build"],
        "panel_label": resultado["panel_label"],
        "min_review_stars": resultado["min_review_stars"],
        "universes": resultado["universes"],
        "variants": resultado["variants"],
        "tier_labels": TIER_LABELS,
        "limitations": resultado["limitations"],
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
