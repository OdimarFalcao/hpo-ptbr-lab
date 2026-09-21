"""Painel de posições genotipadas (formato EIGENSTRAT `.snp`).

O AADR e a maioria dos recursos de DNA antigo distribuem os genótipos em
EIGENSTRAT. O arquivo `.snp` lista **quais posições foram ensaiadas** — é
exatamente a informação necessária para responder se uma variante de doença
pode sequer ser observada nesse conjunto de dados.

Formato, seis colunas separadas por espaço:

    rs3094315   1  0.020130  752566  G  A
    ^SNP id     ^cromossomo  ^posicao fisica  ^ref  ^alt
                   ^posicao genetica (Morgans)

## Build do genoma: a armadilha central

Coordenada física só tem sentido dentro de uma montagem do genoma. A mesma
variante ocupa posições diferentes em GRCh37 e GRCh38. Cruzar fontes de
builds distintos produz interseção proxima de zero — que parece resultado
("nenhuma variante patogenica esta no painel") mas e erro de unidade.

Este modulo nao tenta adivinhar o build: ele **exige** que seja declarado,
registra no manifesto, e `check_coverage` recusa cruzar fontes com builds
diferentes. Nenhuma conversao de coordenadas e feita aqui; liftover e uma
operacao com perdas e precisa ser decisao explicita, com ferramenta propria.

Nenhum arquivo normalizado e gerado: o `.snp` ja e tabular e minimo. Grava-se
apenas o manifesto de proveniencia.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .hashing import raw_sha256

GENOME_BUILDS = ("GRCh37", "GRCh38")

# EIGENSTRAT codifica cromossomos como inteiros.
CHROMOSOME_CODES = {**{str(n): str(n) for n in range(1, 23)}, "23": "X", "24": "Y", "90": "MT", "91": "XY"}

# Comprimento de cada cromossomo em cada montagem (bp). Uma posicao nunca pode
# exceder o comprimento do cromossomo que a contem: e isso que permite VERIFICAR
# o build declarado em vez de apenas confiar nele.
CHROMOSOME_LENGTHS = {
    "GRCh37": {
        "1": 249250621, "2": 243199373, "3": 198022430, "4": 191154276,
        "5": 180915260, "6": 171115067, "7": 159138663, "8": 146364022,
        "9": 141213431, "10": 135534747, "11": 135006516, "12": 133851895,
        "13": 115169878, "14": 107349540, "15": 102531392, "16": 90354753,
        "17": 81195210, "18": 78077248, "19": 59128983, "20": 63025520,
        "21": 48129895, "22": 51304566, "X": 155270560, "Y": 59373566,
        "MT": 16569,
    },
    "GRCh38": {
        "1": 248956422, "2": 242193529, "3": 198295559, "4": 190214555,
        "5": 181538259, "6": 170805979, "7": 159345973, "8": 145138636,
        "9": 138394717, "10": 133797422, "11": 135086622, "12": 133275309,
        "13": 114364328, "14": 107043718, "15": 101991189, "16": 90338345,
        "17": 83257441, "18": 80373285, "19": 58617616, "20": 64444167,
        "21": 46709983, "22": 50818468, "X": 156040895, "Y": 57227415,
        "MT": 16569,
    },
}

# Tamanhos publicados dos paineis mais usados em DNA antigo. Servem para
# *sugerir* qual painel o arquivo parece ser, nunca para afirmar.
KNOWN_PANEL_SIZES = {
    1233013: "1240K (captura, ~1,24 milhao de SNPs)",
    1150639: "1240K variante reduzida",
    597573: "Human Origins (array, ~600 mil SNPs)",
    621799: "Human Origins variante",
}


@dataclass(frozen=True)
class PanelIndex:
    """Posições ensaiadas, indexadas por cromossomo."""

    genome_build: str
    panel_label: str
    positions: dict[str, frozenset[int]]
    unknown_chromosome_codes: tuple[str, ...]

    @property
    def total(self) -> int:
        return sum(len(p) for p in self.positions.values())

    def is_assayed(self, chromosome: str, position: int) -> bool:
        return position in self.positions.get(str(chromosome).upper(), frozenset())

    def counts_by_chromosome(self) -> dict[str, int]:
        def ordem(nome: str) -> tuple[int, str]:
            return (int(nome), "") if nome.isdigit() else (99, nome)

        return {c: len(self.positions[c]) for c in sorted(self.positions, key=ordem)}


def load_panel(
    snp_path: str | Path,
    genome_build: str,
    panel_label: str = "",
) -> PanelIndex:
    """Lê um `.snp` EIGENSTRAT. O build precisa ser declarado por quem chama."""
    if genome_build not in GENOME_BUILDS:
        raise ValueError(
            f"Build do genoma precisa ser declarado explicitamente, um de {GENOME_BUILDS}. "
            f"Recebido: {genome_build!r}. Consulte a documentação do conjunto de dados; "
            "não é possível inferir o build a partir do arquivo."
        )

    posicoes: dict[str, set[int]] = {}
    desconhecidos: Counter[str] = Counter()
    linhas_invalidas = 0

    with Path(snp_path).open(encoding="utf-8") as handle:
        for linha in handle:
            campos = linha.split()
            if len(campos) < 4:
                if linha.strip():
                    linhas_invalidas += 1
                continue
            codigo = campos[1]
            cromossomo = CHROMOSOME_CODES.get(codigo)
            if cromossomo is None:
                desconhecidos[codigo] += 1
                continue
            try:
                posicao = int(campos[3])
            except ValueError:
                linhas_invalidas += 1
                continue
            posicoes.setdefault(cromossomo, set()).add(posicao)

    if not posicoes:
        raise ValueError(
            f"Nenhuma posição válida lida de {snp_path}. "
            "Confirme que o arquivo é um .snp EIGENSTRAT de seis colunas."
        )

    return PanelIndex(
        genome_build=genome_build,
        panel_label=panel_label or Path(snp_path).stem,
        positions={c: frozenset(p) for c, p in posicoes.items()},
        unknown_chromosome_codes=tuple(sorted(desconhecidos)),
    )


def verify_declared_build(index: PanelIndex) -> dict[str, object]:
    """Confere o build declarado contra a evidencia interna do proprio arquivo.

    Uma posicao maior que o comprimento do cromossomo naquele build e
    impossivel. Quando um cromossomo cabe num build e estoura no outro, ele
    decide. Isso transforma o build de 'declarado e torcer' em 'declarado e
    verificado', sem depender de documentacao externa.
    """
    evidencia = []
    compativeis_por_build = {b: 0 for b in GENOME_BUILDS}
    exclusivos = {b: 0 for b in GENOME_BUILDS}
    impossiveis = []

    for cromossomo, posicoes in index.positions.items():
        if not posicoes:
            continue
        maxima = max(posicoes)
        cabe = {
            build: maxima <= CHROMOSOME_LENGTHS[build].get(cromossomo, 0)
            for build in GENOME_BUILDS
        }
        for build, ok in cabe.items():
            if ok:
                compativeis_por_build[build] += 1
        somente = [b for b, ok in cabe.items() if ok and not any(
            v for k, v in cabe.items() if k != b
        )]
        if len(somente) == 1:
            exclusivos[somente[0]] += 1
        if not any(cabe.values()):
            impossiveis.append(cromossomo)
        evidencia.append(
            {
                "chromosome": cromossomo,
                "max_position": maxima,
                "fits": cabe,
                "decides_for": somente[0] if len(somente) == 1 else None,
            }
        )

    evidencia.sort(key=lambda e: (not e["chromosome"].isdigit(), e["chromosome"].zfill(2)))
    apontados = [b for b, n in exclusivos.items() if n > 0]

    if impossiveis:
        veredito = "impossivel"
        explicacao = (
            f"Cromossomos com posicao maior que o comprimento em qualquer build: "
            f"{impossiveis}. O arquivo, o mapeamento de cromossomos ou a tabela de "
            "comprimentos esta errado."
        )
    elif len(apontados) > 1:
        veredito = "contraditorio"
        explicacao = f"Cromossomos diferentes apontam para builds diferentes: {exclusivos}."
    elif not apontados:
        veredito = "inconclusivo"
        explicacao = (
            "Nenhum cromossomo tem posicao alta o suficiente para distinguir os "
            "builds. A declaracao nao pode ser verificada por este metodo."
        )
    elif apontados[0] == index.genome_build:
        veredito = "consistente"
        explicacao = (
            f"{exclusivos[apontados[0]]} cromossomo(s) so cabem em {apontados[0]}, "
            f"que e o build declarado. Nenhum aponta para outro build."
        )
    else:
        veredito = "contradiz_declaracao"
        explicacao = (
            f"O build declarado e {index.genome_build}, mas {exclusivos[apontados[0]]} "
            f"cromossomo(s) so cabem em {apontados[0]}. A declaracao provavelmente esta errada."
        )

    return {
        "declared": index.genome_build,
        "verdict": veredito,
        "explanation": explicacao,
        "chromosomes_exclusive_to": exclusivos,
        "chromosomes_compatible_with": compativeis_por_build,
        "evidence": evidencia,
        "method": (
            "Uma posicao nao pode exceder o comprimento do cromossomo naquela "
            "montagem. Verificacao interna, sem consulta externa."
        ),
    }


def build_manifest(
    snp_path: str | Path,
    index: PanelIndex,
    output_metadata: str | Path,
    *,
    source_url: str = "",
) -> dict[str, object]:
    caminho = Path(snp_path)
    por_cromossomo = index.counts_by_chromosome()
    autossomicos = sum(n for c, n in por_cromossomo.items() if c.isdigit())

    manifest = {
        "schema_version": "genotype-panel-manifest-v1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source": {
            "url": source_url,
            "file": caminho.name,
            "sha256": raw_sha256(caminho),
            "format": "EIGENSTRAT .snp",
        },
        "genome_build": {
            "declared": index.genome_build,
            "inferred": False,
            "verification": verify_declared_build(index),
            "note": (
                "O build nao e inferido do arquivo: e declarado por quem executa e "
                "precisa vir da documentacao do conjunto de dados. Cruzar fontes de "
                "builds diferentes produz intersecao espuria."
            ),
        },
        "panel": {
            "label": index.panel_label,
            "assayed_positions": index.total,
            "autosomal_positions": autossomicos,
            "by_chromosome": por_cromossomo,
            "resembles_known_panel": KNOWN_PANEL_SIZES.get(index.total, "não corresponde a um painel conhecido pelo tamanho"),
            "size_match_is_suggestive_only": True,
        },
        "parsing": {
            "unknown_chromosome_codes": list(index.unknown_chromosome_codes),
            "note": (
                "Códigos de cromossomo fora do esperado são contados e listados, "
                "nunca descartados em silêncio."
            ),
        },
        "no_normalized_copy": (
            "O .snp ja e tabular e minimo; nao se gera copia derivada. A "
            "proveniencia e o sha256 do arquivo original."
        ),
    }
    Path(output_metadata).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


_COMPLEMENTO = str.maketrans("ACGT", "TGCA")


def read_panel_alleles(
    snp_path: str | Path,
    wanted: set[tuple[str, int]],
) -> dict[tuple[str, int], tuple[tuple[str, str], ...]]:
    """Os dois alelos que o painel ensaia em cada posição pedida.

    Estar na posição não basta. O `.snp` declara quais dois alelos o painel
    distingue naquela posição — por exemplo G/A. Se a variante patogênica ali
    é G>T, o painel pergunta "G ou A?" e nunca vê o T: em DNA antigo, com
    chamada pseudo-haploide, uma leitura com T é simplesmente descartada.

    Lê o arquivo de novo, mas guarda só as posições pedidas: carregar os
    alelos de 1,2 milhão de posições custaria memória sem necessidade.
    """
    encontrados: dict[tuple[str, int], list[tuple[str, str]]] = {}
    with Path(snp_path).open(encoding="utf-8") as handle:
        for linha in handle:
            campos = linha.split()
            if len(campos) < 6:
                continue
            cromossomo = CHROMOSOME_CODES.get(campos[1])
            if cromossomo is None:
                continue
            try:
                chave = (cromossomo, int(campos[3]))
            except ValueError:
                continue
            if chave in wanted:
                encontrados.setdefault(chave, []).append(
                    (campos[4].upper(), campos[5].upper())
                )
    return {chave: tuple(pares) for chave, pares in encontrados.items()}


def classify_allele(
    ref: str, alt: str, panel_pairs: tuple[tuple[str, str], ...]
) -> str:
    """Relação entre a variante e os alelos que o painel distingue.

    - `allele_match`: o painel distingue exatamente ref e alt.
    - `strand_flip_match`: casa pela fita complementar. O painel pode estar
      orientado na outra fita; é provável que seja a mesma variante, mas
      precisa de confirmação antes de uso.
    - `different_alleles`: mesma posição, alelos diferentes. O painel não
      observa a variante patogênica.
    """
    alvo = {ref, alt}
    for par in panel_pairs:
        if set(par) == alvo:
            return "allele_match"
    complemento = {ref.translate(_COMPLEMENTO), alt.translate(_COMPLEMENTO)}
    for par in panel_pairs:
        if set(par) == complemento:
            return "strand_flip_match"
    return "different_alleles"


def check_coverage(
    index: PanelIndex,
    variants: list[dict[str, object]],
    variants_genome_build: str,
) -> dict[str, object]:
    """Quais variantes caem em posições que o painel ensaiou.

    Recusa se os builds divergirem. Um resultado de cobertura calculado entre
    builds diferentes seria numericamente válido e cientificamente falso.
    """
    if variants_genome_build != index.genome_build:
        raise ValueError(
            f"Build divergente: o painel está em {index.genome_build} e as variantes "
            f"em {variants_genome_build}. Cruzar coordenadas de builds diferentes "
            "produz interseção espúria. Converta explicitamente (liftover) e registre "
            "a conversão, ou use a distribuição da fonte no mesmo build."
        )

    ensaiadas, ausentes = [], []
    for variante in variants:
        cromossomo = str(variante["chromosome"]).upper()
        posicao = int(variante["position"])
        destino = ensaiadas if index.is_assayed(cromossomo, posicao) else ausentes
        destino.append(variante)

    total = len(variants)
    return {
        "schema_version": "panel-coverage-v1",
        "genome_build": index.genome_build,
        "panel_label": index.panel_label,
        "summary": {
            "variants_checked": total,
            "assayed": len(ensaiadas),
            "not_assayed": len(ausentes),
            "percent_assayed": round(100 * len(ensaiadas) / total, 2) if total else None,
        },
        "assayed": ensaiadas,
        "not_assayed": ausentes,
        "limitations": [
            "Posição ensaiada não garante genótipo observado num indivíduo: "
            "cobertura, dano e filtros de qualidade decidem isso por amostra.",
            "Ausência do painel significa que a pergunta não pode ser feita com "
            "esses dados, não que a variante esteja ausente na população.",
        ],
    }
