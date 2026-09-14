from streamlit.testing.v1 import AppTest


def test_workbench_default_case_runs_without_exception():
    app = AppTest.from_file("streamlit_app.py").run(timeout=20)
    app.radio[0].set_value("Anotação assistida").run(timeout=20)

    assert not app.exception
    analyze = next(
        button for button in app.button if button.label == "Localizar fenótipos"
    )
    analyze.click().run(timeout=30)

    assert not app.exception
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["Detectadas automaticamente"] == "3"
    assert metrics["Adicionadas manualmente"] == "0"
    assert any(
        button.label == "Baixar perfil revisado em JSON"
        for button in app.get("download_button")
    )
