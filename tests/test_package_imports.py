"""O painel roda só com a biblioteca padrão.

Garantia de projeto: nenhuma dependência instalável é necessária para
reproduzir os números do painel. Se algum módulo passar a importar uma
biblioteca externa, este teste falha e obriga a decisão a ser explícita.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SONDA = """
import sys
sys.path.insert(0, {src!r})
antes = set(sys.modules)
import hpo_ptbr.cli.__main__  # carrega a CLI e, por ela, todos os modulos
from hpo_ptbr import (clinvar, data, gene_disease, genotype_panel, hashing,  # noqa: F401
                      hpoa, ontology, target_coverage, term_targets)
externos = sorted(
    nome.split(".")[0] for nome in set(sys.modules) - antes
    if not nome.startswith("hpo_ptbr")
    and nome.split(".")[0] not in sys.stdlib_module_names
)
print(",".join(sorted(set(externos))))
"""


def test_painel_usa_so_biblioteca_padrao() -> None:
    resultado = subprocess.run(
        [sys.executable, "-c", SONDA.format(src=str(ROOT / "src"))],
        capture_output=True, text=True, check=True,
    )
    assert resultado.stdout.strip() == "", (
        f"dependência externa importada: {resultado.stdout.strip()}"
    )
