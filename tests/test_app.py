"""Teste de fumaça do portal: abre todas as páginas com dados simulados e mexe nos filtros."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import coletar
from tests import servidor_simulado

APP = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture(scope="module")
def pasta(tmp_path_factory):
    destino = tmp_path_factory.mktemp("dados_app")
    with servidor_simulado.servidor(municipios=12) as (url, _):
        assert coletar.main(["--anos", "2025", "2026", "--pausa", "0", "--hoje", "2026-10-30", "--url", url,
                             "--pncp-url", servidor_simulado.url_pncp(url), "--pasta", str(destino)]) == 0
    return destino


def abrir(pasta, monkeypatch, pagina: str | None = None):
    monkeypatch.setenv("PORTAL_PASTA_DADOS", str(pasta))
    at = AppTest.from_file(APP, default_timeout=120).run()
    if pagina:
        at.switch_page(pagina).run()
    assert not at.exception, at.exception
    topo = at.markdown[0].value  # todas as páginas começam pelo cabeçalho com a ilustração
    assert "class='gp-topo'" in topo and "<svg" in topo and "Guarapuava em números" in topo
    return at


def textos(at) -> str:
    return " ".join(m.value for m in at.markdown)


def test_visao_geral(pasta, monkeypatch):
    at = abrir(pasta, monkeypatch)
    assert at.title[0].value == "Visão geral"
    assert "Pontos de atenção" in [s.value for s in at.subheader]
    assert "Gasto com pessoal da Prefeitura: acima do limite de alerta" in textos(at)
    assert ":orange-badge[:material/warning: Atenção]" in textos(at)  # cor sempre com ícone e texto
    assert "contratações emergenciais" in textos(at)  # pontos de atenção das compras
    rotulos = [m.label for m in at.metric]
    for esperado in ["Superávit orçamentário", "Receita corrente líquida", "Gasto com pessoal – Prefeitura",
                     "Gasto com pessoal – Câmara", "Dívida consolidada líquida", "Educação", "Saúde"]:
        assert esperado in rotulos
    assert next(m for m in at.metric if m.label == "Gasto com pessoal – Prefeitura").value == "51,07% da RCL"
    assert any("não da API oficial" in w.value for w in at.warning)

    at.selectbox[0].set_value(2025).run()  # ano fechado: julga meta e mínimos do ano
    assert not at.exception
    assert next(m for m in at.metric if m.label == "Gasto com pessoal – Prefeitura").value == "49,80% da RCL"


def test_receitas(pasta, monkeypatch):
    at = abrir(pasta, monkeypatch, "paginas/receitas.py")
    assert at.title[0].value == "Receitas"
    assert "Impostos e transferências nos últimos 12 meses" in [s.value for s in at.subheader]
    fonte = next(s for s in at.selectbox if s.label == "Fonte de receita")
    assert fonte.value == "iptu"
    fonte.set_value("iss").run()
    assert not at.exception


def test_despesas(pasta, monkeypatch):
    at = abrir(pasta, monkeypatch, "paginas/despesa.py")
    assert at.title[0].value == "Despesas"
    assert at.selectbox[0].value == 2026 and at.selectbox[1].value == 9
    at.multiselect[0].set_value(["Legislativo (Câmara Municipal)"]).run()
    at.multiselect[1].set_value(["Saúde"]).run()  # Câmara não tem despesa em Saúde
    assert any("Nenhuma despesa" in i.value for i in at.info)
    at.multiselect[1].set_value([]).run()
    at.text_input[0].set_value("vencimentos").run()
    assert not at.exception
    assert any(c.value.startswith("1 linha ") for c in at.caption)


def test_compras(pasta, monkeypatch):
    at = abrir(pasta, monkeypatch, "paginas/compras.py")
    assert at.title[0].value == "Compras e contratos"
    assert {"Contratações publicadas", "Valor estimado", "Contratação direta", "Contratos assinados"} <= \
        {m.label for m in at.metric}
    assert "Pontos de atenção" in [s.value for s in at.subheader]
    assert "UNIVERSIDADE ESTADUAL" not in textos(at)
    modalidade = next(m for m in at.multiselect if m.label == "Modalidade")
    modalidade.set_value(["Dispensa"]).run()
    assert not at.exception


def test_comparar_cidades(pasta, monkeypatch):
    at = abrir(pasta, monkeypatch, "paginas/comparar.py")
    assert at.title[0].value == "Comparar cidades"
    minha = next(s for s in at.selectbox if s.label == "Sua cidade")
    outra = next(s for s in at.selectbox if s.label == "Comparar com")
    assert minha.value == "4109401" and outra.value != "4109401"
    outra.set_value("4100103").run()
    assert not at.exception
    assert any("Abatiá" in s.value for s in at.subheader)
    next(s for s in at.selectbox if s.label == "Colorir o mapa por").set_value("pessoal_pct").run()
    assert not at.exception


def test_sobre_os_dados(pasta, monkeypatch):
    at = abrir(pasta, monkeypatch, "paginas/sobre.py")
    assert at.title[0].value == "Sobre os dados"
    assert {"De onde vêm os dados", "Conferência dos dados", "Como os pontos de atenção são calculados"} <= \
        {s.value for s in at.subheader}


@pytest.mark.parametrize("pagina", [None, "paginas/receitas.py", "paginas/compras.py", "paginas/comparar.py",
                                    "paginas/sobre.py"])
def test_sem_dados_orienta_a_coletar(tmp_path, monkeypatch, pagina):
    at = abrir(tmp_path, monkeypatch, pagina)
    assert at.info or at.dataframe  # mensagem de "ainda não coletado" (ou só a tabela de fontes, na página Sobre)
