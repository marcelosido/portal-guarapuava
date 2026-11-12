"""Teste de fumaça do portal: abre as duas páginas com dados simulados e mexe nos filtros."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import coletar
from tests import servidor_simulado

APP = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture(scope="module")
def pasta(tmp_path_factory):
    destino = tmp_path_factory.mktemp("dados_app")
    with servidor_simulado.servidor() as (url, _):
        assert coletar.main(["--anos", "2025", "2026", "--pausa", "0", "--hoje", "2026-10-30",
                             "--url", url, "--pasta", str(destino)]) == 0
    return destino


def abrir(pasta, monkeypatch):
    monkeypatch.setenv("PORTAL_PASTA_DADOS", str(pasta))
    return AppTest.from_file(APP, default_timeout=90).run()


def test_pagina_de_indicadores(pasta, monkeypatch):
    at = abrir(pasta, monkeypatch)
    assert not at.exception
    assert at.title[0].value == "Guarapuava em números"
    rotulos = [m.label for m in at.metric]
    for esperado in ["Superávit orçamentário", "Receita corrente líquida", "Gasto com pessoal – Prefeitura",
                     "Gasto com pessoal – Câmara", "Dívida consolidada líquida", "Educação", "Saúde"]:
        assert esperado in rotulos
    pessoal = next(m for m in at.metric if m.label == "Gasto com pessoal – Prefeitura")
    assert pessoal.value == "51,07% da RCL"
    selos = " ".join(m.value for m in at.markdown)
    assert "Acima do limite de alerta" in selos and ":material/warning:" in selos  # cor sempre com ícone e texto
    assert any("não da API oficial" in w.value for w in at.warning)

    at.selectbox[0].set_value(2025).run()  # ano fechado: julga meta e mínimos do ano
    assert not at.exception
    assert next(m for m in at.metric if m.label == "Gasto com pessoal – Prefeitura").value == "49,80% da RCL"


def test_pagina_de_despesa(pasta, monkeypatch):
    at = abrir(pasta, monkeypatch)
    at.switch_page("paginas/despesa.py").run()
    assert not at.exception and at.title[0].value == "Despesa detalhada"
    assert at.selectbox[0].value == 2026 and at.selectbox[1].value == 9
    at.multiselect[0].set_value(["Legislativo (Câmara Municipal)"]).run()
    at.multiselect[1].set_value(["Saúde"]).run()  # Câmara não tem despesa em Saúde
    assert any("Nenhuma despesa" in i.value for i in at.info)
    at.multiselect[1].set_value([]).run()
    at.text_input[0].set_value("vencimentos").run()
    assert not at.exception
    assert any(c.value.startswith("1 linha ") for c in at.caption)


def test_sem_dados_orienta_a_coletar(tmp_path, monkeypatch):
    at = abrir(tmp_path, monkeypatch)
    assert not at.exception
    assert any("python coletar.py" in i.value for i in at.info)
