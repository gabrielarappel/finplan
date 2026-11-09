"""Teste de fumaça da interface: percorre login e as quatro telas sem exceções."""
from streamlit.testing.v1 import AppTest


def _logado():
    at = AppTest.from_file("app.py", default_timeout=60).run()
    at.text_input[0].set_value("demo@finplan.app")
    at.text_input[1].set_value("demo123")
    at.button[0].click().run()
    return at


def test_login_invalido():
    at = AppTest.from_file("app.py", default_timeout=60).run()
    at.text_input[0].set_value("x@y.com")
    at.text_input[1].set_value("errada")
    at.button[0].click().run()
    assert not at.session_state["logado"]


def test_telas_sem_excecao():
    at = _logado()
    assert at.session_state["logado"]
    for pagina in ["Visão geral", "Lançamentos", "Simulação", "Relatórios"]:
        at.sidebar.radio[0].set_value(pagina).run()
        assert not at.exception, f"{pagina}: {at.exception}"
