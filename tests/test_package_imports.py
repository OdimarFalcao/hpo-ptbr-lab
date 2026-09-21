"""O painel de alvos não pode depender da bancada de ranqueamento.

São duas frentes com dependências diferentes: o painel usa só a biblioteca
padrão, o ranqueamento usa rapidfuzz, rank_bm25 e modelos semânticos. Um
`import` ansioso no `__init__.py` fazia a CLI do painel falhar com
`ModuleNotFoundError: rapidfuzz` num ambiente onde essas bibliotecas não
estão instaladas — sem nunca ter precisado delas.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Subprocesso, nao import direto: a suite ja carregou esses modulos, entao
# verificar sys.modules no processo atual nao provaria nada.
SONDA = """
import sys
sys.path.insert(0, {src!r})
from hpo_ptbr import gene_disease, genotype_panel, hpoa, term_targets  # noqa: F401
pesadas = [m for m in ("rapidfuzz", "rank_bm25", "torch", "transformers")
           if m in sys.modules]
print(",".join(pesadas))
"""


def test_painel_de_alvos_importa_sem_dependencias_de_ranqueamento() -> None:
    resultado = subprocess.run(
        [sys.executable, "-c", SONDA.format(src=str(ROOT / "src"))],
        capture_output=True, text=True, check=True,
    )
    puxadas = resultado.stdout.strip()
    assert puxadas == "", (
        f"o painel de alvos puxou dependências do ranqueamento: {puxadas}. "
        "O __init__.py precisa continuar preguiçoso (PEP 562)."
    )


def test_api_publica_continua_acessivel() -> None:
    """Preguicoso nao pode significar quebrado: os nomes de antes seguem valendo."""
    import hpo_ptbr

    for nome in ("FuzzyMapper", "ExactMapper", "Bm25Mapper", "load_snapshot", "HpoRecord"):
        assert hasattr(hpo_ptbr, nome), f"{nome} sumiu da API pública"
        assert nome in dir(hpo_ptbr)


def test_atributo_inexistente_ainda_levanta_attribute_error() -> None:
    import hpo_ptbr

    try:
        hpo_ptbr.NaoExiste  # noqa: B018
    except AttributeError:
        return
    raise AssertionError("acesso a nome inexistente deveria levantar AttributeError")
