"""Teste ponta a ponta do coletor contra a API simulada (paginação, retentativa, incremental)."""

import json

import pandas as pd
import pytest

import coletar
from despesas.api import ClienteSiconfi
from tests import servidor_simulado

ARGS = ["--anos", "2025", "2026", "--pausa", "0", "--hoje", "2026-10-30"]
SO_MUNICIPIO = [*ARGS, "--modulos", "municipio"]


def test_paginacao_segue_hasmore_e_offset():
    with servidor_simulado.servidor() as (url, contador):
        cliente = ClienteSiconfi(base_url=url, pausa=0)
        itens = cliente.msc_orcamentaria("4109401", 2026, 8, classe=6)
        esperado = servidor_simulado.gerar_msc(2026, 8, 6, "4109401")
        assert len(itens) == len(esperado) > servidor_simulado.TAMANHO_PAGINA
        assert contador["msc_orcamentaria"] == -(-len(esperado) // servidor_simulado.TAMANHO_PAGINA)


def test_espaco_no_parametro_vira_percent20():
    with servidor_simulado.servidor() as (url, _):
        itens = ClienteSiconfi(base_url=url, pausa=0).rreo("4109401", 2026, 4)
        assert any(i["cod_conta"] == "TotalDespesas" for i in itens)  # servidor exige "RREO-Anexo 01"


def test_coleta_completa_e_incremental(tmp_path):
    falha = {"rreo:an_exercicio=2025&nr_periodo=1&co_tipo_demonstrativo=RREO&no_anexo=RREO-Anexo%2001"
             "&co_esfera=M&id_ente=4109401&offset=0"}
    with servidor_simulado.servidor(falhar_uma_vez=falha) as (url, contador):
        todos = [*ARGS, "--url", url, "--pncp-url", servidor_simulado.url_pncp(url), "--pasta", str(tmp_path)]
        assert coletar.main(todos) == 0
        primeira = sum(contador.values())

        fato = pd.read_parquet(tmp_path / "fDespesa.parquet")
        assert sorted(fato["ano"].unique()) == [2025, 2026]
        assert fato.loc[fato["ano"] == 2026, "mes"].max() == 9  # out/2026 ainda não publicado
        meta = json.loads((tmp_path / "metadados.json").read_text(encoding="utf-8"))
        assert meta["ultimo_mes"] == "2026-09" and meta["meses"] == 21
        assert meta["meses_ainda_nao_publicados"] == ["10/2026"]

        conc = pd.read_csv(tmp_path / "conciliacao_rreo.csv", sep=";", decimal=",", encoding="utf-8-sig")
        assert len(conc) == 10 * 5  # 6 bimestres de 2025 + 4 de 2026, 5 medidas
        por_medida = conc.groupby("medida")["status"].agg(set).to_dict()
        assert por_medida["liquidado"] == {"Conciliado"}  # inclusive o 1º bim/2025, que falhou uma vez (503)
        assert por_medida["dotacao_atualizada"] == {"Divergente"}
        assert conc.loc[conc["medida"] == "dotacao_atualizada", "diferenca"].round(2).eq(1469.54).all()

        ind = pd.read_csv(tmp_path / "fIndicadores.csv", sep=";", decimal=",", encoding="utf-8-sig",
                          dtype={"poder": str}, keep_default_na=False)
        rreo = ind[ind["relatorio"] == "RREO"]
        assert sorted(set(zip(rreo["ano"], rreo["periodo"]))) == [(2025, b) for b in range(1, 7)] + [(2026, b) for b in range(1, 5)]
        rgf = ind[(ind["relatorio"] == "RGF") & (ind["chave"] == "pessoal_pct")]
        assert set(rgf["poder"]) == {"E", "L"}
        assert rgf[(rgf["ano"] == 2026) & (rgf["periodo"] == 2) & (rgf["poder"] == "E")]["valor"].item() == 51.07
        assert not (tmp_path / "fDespesa.csv").exists()  # o CSV grande só sai com --csv
        assert meta["ultimo_rreo"] == "2026-4" and meta["ultimo_rgf"] == "2026-2"
        assert rreo[(rreo["ano"] == 2026) & (rreo["periodo"] == 4) & (rreo["chave"] == "populacao")]["valor"].item() == 189630

        # novos módulos: receita mês a mês (Anexo 3), compras (PNCP) e comparativo
        rcl = pd.read_csv(tmp_path / "fReceitaCorrente.csv", sep=";", decimal=",", encoding="utf-8-sig", dtype={"referencia": str})
        assert sorted(set(zip(rcl["ano"], rcl["periodo"]))) == [(2025, 6), (2026, 4)]  # ano fechado + último bimestre
        assert meta["pncp"]["status"] == "ok" and meta["pncp"]["contratacoes"] > 0
        assert meta["comparativo"]["status"] == "ok" and meta["comparativo"]["ano"] == 2025
        assert (tmp_path / "fContratos.csv").exists() and (tmp_path / "fComparativo.csv").exists()

        # Segunda execução: recoleta só os 3 últimos meses, o mês não publicado e os 2 últimos relatórios
        assinaturas = {a.name: a.read_bytes() for a in tmp_path.iterdir() if a.name != "metadados.json"}
        assert coletar.main(todos) == 0
        segunda = sum(contador.values()) - primeira
        assert segunda < primeira / 3
        # Nada mudou na fonte -> arquivos byte a byte iguais (o Git não registra mudança à toa)
        assert {a.name: a.read_bytes() for a in tmp_path.iterdir() if a.name != "metadados.json"} == assinaturas


def test_csv_abre_no_excel_brasileiro(tmp_path):
    with servidor_simulado.servidor() as (url, _):
        assert coletar.main(["--anos", "2026", "2026", "--pausa", "0", "--hoje", "2026-03-15", "--csv",
                             "--modulos", "municipio", "--url", url, "--pasta", str(tmp_path)]) == 0
    texto = (tmp_path / "fDespesa.csv").read_text(encoding="utf-8-sig")
    cabecalho, primeira_linha = texto.splitlines()[:2]
    assert cabecalho.split(";")[:3] == ["ano", "mes", "poder_orgao"]
    assert "," in primeira_linha.split(";")[-1]  # decimal com vírgula
    dim = pd.read_csv(tmp_path / "dNatureza.csv", sep=";", dtype=str, encoding="utf-8-sig")
    assert {"natureza_despesa", "elemento_desc", "grupo_desc"} <= set(dim.columns)


def test_recusa_misturar_entes(tmp_path):
    (tmp_path / "metadados.json").write_text(json.dumps({"id_ente": "4106902"}), encoding="utf-8")
    assert coletar.main([*ARGS, "--url", "http://127.0.0.1:9/", "--pasta", str(tmp_path)]) == 2


@pytest.mark.parametrize("anos", [["2026", "2025"], ["2025", "2030"]])
def test_intervalo_invalido(tmp_path, anos):
    assert coletar.main(["--anos", *anos, "--hoje", "2026-10-30", "--pasta", str(tmp_path)]) == 2


def test_tempo_esgotado_nao_e_falha(tmp_path):
    """Sem tempo para o comparativo: grava o que tem, sai com sucesso e deixa o resto para a próxima vez."""
    with servidor_simulado.servidor() as (url, _):
        assert coletar.main([*ARGS, "--url", url, "--pncp-url", servidor_simulado.url_pncp(url), "--pasta", str(tmp_path),
                             "--modulos", "comparativo", "--tempo-max", "0"]) == 0
    meta = json.loads((tmp_path / "metadados.json").read_text(encoding="utf-8"))
    assert meta["comparativo"]["status"] == "parcial"


def test_falha_total_do_pncp_marca_a_execucao(tmp_path, monkeypatch):
    monkeypatch.setattr("despesas.api.time.sleep", lambda segundos: None)  # sem esperar entre as tentativas
    with servidor_simulado.servidor() as (url, _):
        codigo = coletar.main([*ARGS, "--url", url, "--pncp-url", "http://127.0.0.1:9/api/consulta/",
                               "--pasta", str(tmp_path), "--modulos", "pncp"])
    meta = json.loads((tmp_path / "metadados.json").read_text(encoding="utf-8"))
    assert codigo == 1 and meta["pncp"]["status"] == "falhou"
    assert len(meta["pncp"]["falhas"]) == 2  # desiste depois de dois períodos seguidos com erro
