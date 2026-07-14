from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    notebook = {
        "cells": [
            {
                "id": "intro-hpo",
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "# Cobertura HPO em português\n",
                    "Notebook de inspeção do snapshot versionado usado pelo HPO-PTBR Lab.\n",
                ],
            },
            {
                "id": "load-data",
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "import json\n",
                    "from pathlib import Path\n",
                    "import pandas as pd\n",
                    "\n",
                    "ROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()\n",
                    "summary = json.loads((ROOT / 'data/processed/coverage_summary.json').read_text(encoding='utf-8'))\n",
                    "summary\n",
                ],
            },
            {
                "id": "plot-cov",
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "coverage = pd.DataFrame({\n",
                    "    'categoria': ['Com rótulo PT', 'Sem rótulo PT'],\n",
                    "    'termos': [summary['translated_labels_pt'], summary['active_terms'] - summary['translated_labels_pt']],\n",
                    "})\n",
                    "coverage.set_index('categoria').plot.barh(legend=False, title='Cobertura de rótulos HPO em português');\n",
                ],
            },
            {
                "id": "show-gaps",
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "missing = pd.read_csv(ROOT / 'data/processed/untranslated_terms.csv')\n",
                    "missing.head(20)\n",
                ],
            },
        ],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    output = ROOT / "notebooks/01_hpo_pt_coverage.ipynb"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(notebook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
