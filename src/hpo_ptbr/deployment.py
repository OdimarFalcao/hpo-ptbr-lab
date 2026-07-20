from __future__ import annotations

from pathlib import Path

DASHBOARD_REQUIRED_FILES = (
    "streamlit_app.py",
    "requirements.txt",
    "data/processed/hpo_ptbr.csv",
    "data/processed/metadata.json",
    "data/processed/untranslated_terms.csv",
    "data/results/evaluation_summary.csv",
    "data/results/evidence_evaluation_summary.json",
    "data/demo/synthetic_descriptions.json",
)

HEAVY_OFFLINE_DEPENDENCIES = {"sentence-transformers", "torch"}


def _requirement_names(path: Path) -> set[str]:
    names = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", "-r")):
            continue
        name = line.split("[", 1)[0]
        for separator in ("<", ">", "=", "!", "~"):
            name = name.split(separator, 1)[0]
        names.add(name.strip().lower())
    return names


def check_dashboard_readiness(root: str | Path) -> dict[str, object]:
    project_root = Path(root)
    missing_files = [
        relative
        for relative in DASHBOARD_REQUIRED_FILES
        if not (project_root / relative).is_file()
    ]
    dashboard_dependencies = _requirement_names(project_root / "requirements.txt")
    offline_leaks = sorted(dashboard_dependencies & HEAVY_OFFLINE_DEPENDENCIES)
    semantic_requirements = project_root / "requirements-semantic.txt"
    semantic_dependencies = (
        _requirement_names(semantic_requirements)
        if semantic_requirements.is_file()
        else set()
    )
    checks = {
        "required_files_present": not missing_files,
        "dashboard_dependencies_lightweight": not offline_leaks,
        "semantic_dependency_isolated": "sentence-transformers"
        in semantic_dependencies,
    }
    return {
        "ready": all(checks.values()),
        "checks": checks,
        "missing_files": missing_files,
        "offline_dependencies_in_dashboard": offline_leaks,
    }
