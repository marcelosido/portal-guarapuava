"""Testes da conferência com o CSV do portal da transparência.

O CSV é SIMULADO no formato das colunas exibidas na página (o arquivo real não foi testado):
código "3" + categoria + grupo + modalidade + zeros, elemento "11 - ...", números 1.234,56.
"""

import pandas as pd
import pytest

import coletar
import conciliar_atende as ca
from tests import servidor_simulado

ENTIDADES = {
    "10131": "MUNICÍPIO DE GUARAPUAVA",
    "10132": "INSTITUTO DE PREVIDENCIA DOS SERVIDORES PUBLICOS DO MUNICIPIO DE GUARAPUAVA- GUARAPUAVA PREV",
    "20231": "CÂMARA MUNICIPAL DE GUARAPUAVA",
}


def br(v: float) -> str:
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@pytest.fixture(scope="module")
def pasta(tmp_path_factory):
    destino = tmp_path_factory.mktemp("dados")
    with servidor_simulado.servidor() as (url, _):
        assert coletar.main(["--anos", "2026", "2026", "--pausa", "0", "--hoje", "2026-10-30",
                             "--modulos", "municipio", "--url", url, "--pasta", str(destino)]) == 0
    return destino


def csv_atende(pasta, caminho, ajuste=0.0, titulo=False):
    fato = pd.read_parquet(pasta / "fDespesa.parquet")
    ago = fato[(fato["ano"] == 2026) & (fato["mes"] == 8)].assign(n6=lambda d: d["natureza_despesa"].str[:6])
    agg = ago.groupby(["poder_orgao", "n6"])[["dotacao_atualizada", "liquidado"]].sum().reset_index()
    linhas = []
    for i, r in agg.iterrows():
        n = r["n6"]
        liquidado = r["liquidado"] + (ajuste if i == 0 else 0.0)
        linhas.append({
            "Entidade": ENTIDADES[r["poder_orgao"]],
            "Natureza da Despesa - Categoria Econômica": f"{n[0]} - Aplicações diretas",
            "Natureza da Despesa - Grupo": f"{n[1]} - Aplicações diretas",
            "Natureza da Despesa - Elemento": f"{int(n[4:6])} - Aplicações diretas",
            "Conta - Código": "3" + n[:4] + "0" * 14,
            "Conta - Descrição da Conta": "Aplicações diretas",
            "Prevista para o Ano": br(r["dotacao_atualizada"]),
            "Liquidado até o Mês": br(liquidado),
            "Percentual": br(100 * liquidado / r["dotacao_atualizada"]) if r["dotacao_atualizada"] else "0,00",
        })
    texto = pd.DataFrame(linhas).to_csv(sep=";", index=False)
    if titulo:
        texto = "DEMONSTRATIVO DAS DESPESAS\nEntidade: Todos;Ano: 2026;Mês: Agosto\n\n" + texto
    caminho.write_bytes(texto.encode("cp1252"))
    return caminho


def test_arquivo_identico_bate(pasta, tmp_path, capsys):
    arq = csv_atende(pasta, tmp_path / "Demonstrativo.csv", titulo=True)
    assert ca.main([str(arq), "--ano", "2026", "--mes", "8", "--pasta", str(pasta)]) == 0
    saida = capsys.readouterr().out
    assert "diferença R$ 0,00" in saida
    comp = pd.read_csv(pasta / "conciliacao_atende_2026_08.csv", sep=";", decimal=",", encoding="utf-8-sig",
                       dtype={"poder_orgao": str, "natureza6": str})
    assert set(comp["status_liquidado"]) == {"Igual"}
    assert comp["dif_previsto_x_atualizada"].abs().max() < 0.01


def test_diferenca_aparece_na_linha_certa(pasta, tmp_path, capsys):
    arq = csv_atende(pasta, tmp_path / "Demonstrativo.csv", ajuste=1234.56)
    assert ca.main([str(arq), "--ano", "2026", "--mes", "8", "--pasta", str(pasta)]) == 1
    comp = pd.read_csv(pasta / "conciliacao_atende_2026_08.csv", sep=";", decimal=",", encoding="utf-8-sig",
                       dtype={"poder_orgao": str, "natureza6": str})
    diferentes = comp[comp["status_liquidado"] == "Diferente"]
    assert len(diferentes) == 1 and diferentes["dif_liquidado"].iloc[0] == pytest.approx(1234.56)
    assert "R$ 1.234,56" in capsys.readouterr().out


def test_mes_nao_coletado(pasta, tmp_path):
    arq = csv_atende(pasta, tmp_path / "Demonstrativo.csv")
    assert ca.main([str(arq), "--ano", "2026", "--mes", "11", "--pasta", str(pasta)]) == 2


@pytest.mark.parametrize("texto,esperado", [
    ("1.234,56", 1234.56), ("1234,56", 1234.56), ("1234.56", 1234.56), ("1,234.56", 1234.56),
    ("R$ 12.345.678,90", 12345678.90), ("", 0.0), ("-15,00", -15.0),
])
def test_para_numero(texto, esperado):
    assert ca.para_numero(texto) == pytest.approx(esperado)


@pytest.mark.parametrize("codigo,elemento,esperado", [
    ("3319000000000000000", "11 - Aplicações diretas", "319011"),
    ("3317100000000000000", "70 - Transferências", "317170"),
    ("3449000000000000000", "52 - Aplicações diretas", "449052"),
    ("3.3.1.90.00.00", "7 - Aplicações diretas", "319007"),
    ("9999", "11", None),
])
def test_natureza6(codigo, elemento, esperado):
    assert ca.natureza6(codigo, elemento) == esperado


def test_poder_orgao():
    assert ca.poder_orgao(ENTIDADES["10132"]) == "10132"
    assert ca.poder_orgao(ENTIDADES["20231"]) == "20231"
    assert ca.poder_orgao("FUNDAÇÃO PROTEGER") == "10131"
    assert ca.poder_orgao("FUNREBOM - GUARAPUAVA") == "10131"
