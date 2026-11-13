"""Comparação entre municípios: escolha do relatório certo, retomada da coleta e indicadores por habitante."""

import datetime as dt

import pandas as pd

from despesas import comparativo
from despesas.api import ClienteSiconfi, Prazo
from tests import servidor_simulado

HOJE = dt.date(2026, 10, 30)


def _cliente(url, prazo=None):
    return ClienteSiconfi(base_url=url, pausa=0, prazo=prazo)


def test_ano_comparado_e_o_ultimo_fechado():
    assert comparativo.ano_comparativo(dt.date(2026, 10, 30)) == 2025
    assert comparativo.ano_comparativo(dt.date(2027, 2, 10)) == 2025  # em fevereiro ainda faltam relatórios de 2026
    assert comparativo.ano_comparativo(dt.date(2027, 3, 1)) == 2026


def test_coleta_retomavel_e_relatorios_simplificados(tmp_path):
    with servidor_simulado.servidor(municipios=6) as (url, contador):
        # 1ª execução sem tempo: nada coletado, nada quebrado
        parcial = comparativo.coletar_comparativo(_cliente(url, Prazo(0)), tmp_path, HOJE, "PR", "4109401")
        assert parcial["status"] == "parcial"
        # 2ª execução: completa
        resumo = comparativo.coletar_comparativo(_cliente(url), tmp_path, HOJE, "PR", "4109401")
        assert resumo["status"] == "ok" and resumo["municipios"] == 7  # 6 primeiros + Guarapuava
        antes = sum(contador.values())
        # 3ª execução: nada a fazer
        assert comparativo.coletar_comparativo(_cliente(url), tmp_path, HOJE, "PR", "4109401")["consultas_nesta_execucao"] == 0
        assert sum(contador.values()) == antes

    lista = pd.read_csv(tmp_path / "dMunicipios.csv", sep=";", dtype={"cod_ibge": str})
    assert "3503406" not in set(lista["cod_ibge"])  # só municípios do PR (o entes traz SP e o estado)
    controle = pd.read_csv(tmp_path / "comparativo_controle.csv", sep=";", dtype={"cod_ibge": str})
    simplificado = controle[(controle["cod_ibge"] == "4100202") & (controle["etapa"] == "extrato")]["detalhe"].item()
    assert '"rgf_periodicidade": "S"' in simplificado and '"rreo_tipo": "RREO Simplificado"' in simplificado
    dados = pd.read_csv(tmp_path / "fComparativo.csv", sep=";", decimal=",", dtype={"cod_ibge": str})
    pessoal = dados[(dados["cod_ibge"] == "4100202") & (dados["chave"] == "pessoal_pct")]
    assert len(pessoal) == 1  # RGF simplificado semestral foi encontrado


def test_falha_num_municipio_nao_impede_os_outros(tmp_path, monkeypatch):
    monkeypatch.setattr("despesas.api.time.sleep", lambda segundos: None)  # sem esperar entre as tentativas
    with servidor_simulado.servidor(municipios=4, falhar_sempre={"dca:4100103"}) as (url, _):
        resumo = comparativo.coletar_comparativo(_cliente(url), tmp_path, HOJE, "PR", "4109401")
    assert resumo["falhas_nesta_execucao"] == 2 and resumo["status"] == "ok"
    controle = pd.read_csv(tmp_path / "comparativo_controle.csv", sep=";", dtype={"cod_ibge": str})
    falhas = controle[controle["situacao"] == "falha"]
    assert set(falhas["etapa"]) == {"dca_ie", "dca_id"} and set(falhas["cod_ibge"]) == {"4100103"}


def test_indicadores_por_habitante():
    dados = pd.DataFrame([
        {"ano": 2025, "cod_ibge": "1", "fonte": "rreo14", "chave": "populacao", "valor": 1000.0},
        {"ano": 2025, "cod_ibge": "1", "fonte": "dca_ie", "chave": "funcao_12", "valor": 500000.0},
        {"ano": 2025, "cod_ibge": "1", "fonte": "rgf01", "chave": "pessoal_valor", "valor": 2000000.0},
        {"ano": 2025, "cod_ibge": "1", "fonte": "rreo14", "chave": "educacao_pct", "valor": 26.5},
        {"ano": 2025, "cod_ibge": "2", "fonte": "dca_ie", "chave": "funcao_10", "valor": 300000.0},
    ])
    lista = pd.DataFrame({"cod_ibge": ["1", "2"], "municipio": ["A", "B"], "populacao": [999, 600]})
    t = comparativo.tabela_indicadores(dados, lista, 2025).set_index("cod_ibge")
    assert t.loc["1", "educacao_hab"] == 500.0 and "pessoal_hab" not in t
    assert t.loc["2", "saude_hab"] == 500.0  # sem população no RREO: usa a do cadastro de entes
    assert t.loc["1", "educacao_pct"] == 26.5 and pd.isna(t.loc["2", "educacao_pct"])


def test_peso_no_orcamento():
    """De cada R$ 100 gastos (DCA I-E, sem intraorçamentárias), quanto foi para a área."""
    dados = pd.DataFrame([
        {"ano": 2025, "cod_ibge": "1", "fonte": "dca_ie", "chave": "despesa_total", "valor": 1_000_000.0},
        {"ano": 2025, "cod_ibge": "1", "fonte": "dca_ie", "chave": "funcao_12", "valor": 264_000.0},
        {"ano": 2025, "cod_ibge": "1", "fonte": "dca_ie", "chave": "funcao_10", "valor": 244_000.0},
        {"ano": 2025, "cod_ibge": "1", "fonte": "dca_id", "chave": "investimentos", "valor": 16_000.0},
        {"ano": 2025, "cod_ibge": "2", "fonte": "dca_ie", "chave": "funcao_12", "valor": 5_000.0},  # sem total
    ])
    lista = pd.DataFrame({"cod_ibge": ["1", "2"], "municipio": ["A", "B"], "populacao": [1000, 600]})
    t = comparativo.tabela_indicadores(dados, lista, 2025).set_index("cod_ibge")
    pesos = t.loc["1", ["educacao_peso", "saude_peso", "investimento_peso"]].astype(float).round(6).tolist()
    assert pesos == [26.4, 24.4, 1.6]
    assert pd.isna(t.loc["2", "educacao_peso"])  # sem a despesa total, não há peso


def test_cidades_do_mesmo_porte():
    pop = pd.Series({"g": 190_000, "a": 120_000, "b": 450_000, "c": 899_000, "d": 95_000, "e": 15_000, "f": 101_000,
                     "h": 300_000, "i": 250_000, "j": 140_000, "k": 2_000_000})
    grupo, frase = comparativo.cidades_do_mesmo_porte(pop, "g")
    assert set(grupo) == {"g", "a", "b", "c", "f", "h", "i", "j"} and frase == "8 cidades de 100 mil a 900 mil habitantes"
    # faixa com menos de 8 cidades (a capital): as 12 de população mais próxima, ela incluída
    grupo, frase = comparativo.cidades_do_mesmo_porte(pop, "k")
    assert grupo[0] == "k" and len(grupo) == len(pop) and frase.startswith("as 11 cidades")
