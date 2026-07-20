from pathlib import Path

from hpo_ptbr.deployment import check_dashboard_readiness


def test_dashboard_artifacts_and_dependencies_are_ready():
    root = Path(__file__).resolve().parents[1]

    result = check_dashboard_readiness(root)

    assert result["ready"] is True
    assert result["missing_files"] == []
    assert result["offline_dependencies_in_dashboard"] == []
