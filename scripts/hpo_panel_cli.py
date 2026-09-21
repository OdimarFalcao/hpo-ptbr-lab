"""Atalho para a CLI do painel, mantido para os comandos já documentados.

A CLI vive em `src/hpo_ptbr/cli/`. Com o projeto instalado
(`pip install -e .`), use diretamente:

    hpo-painel coverage data/raw/<painel>.snp --build GRCh37
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hpo_ptbr.cli.__main__ import main  # noqa: E402

raise SystemExit(main())
