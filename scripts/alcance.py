"""Atalho para a CLI do Alcance Genômico, para usar sem instalar.

    python scripts/alcance.py coverage data/raw/<painel>.snp --build GRCh37

Com o projeto instalado (`pip install -e .[dev]`), use diretamente:

    alcance coverage data/raw/<painel>.snp --build GRCh37
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hpo_ptbr.cli.__main__ import main  # noqa: E402

raise SystemExit(main())
