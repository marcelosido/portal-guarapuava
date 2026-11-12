"""Regras dos pontos de atenção: dados reais do RREO/RGF e casos montados para cada regra de compras."""

import pandas as pd

from despesas import alertas, indicadores as ind
from despesas.pncp import COLS_CONTRATACOES, COLS_CONTRATOS, tipar_contratacoes, tipar_contratos
from tests import fixtures_api as fx


def test_dias_uteis_sem_feriados():
    pub = alertas.datas(pd.Series(["2026-10-02T09:00:00", "2026-10-02", ""]))   # sexta-feira; formatos misturados
    fim = alertas.datas(pd.Series(["2026-10-12T17:00:00", "2026-10-02T18:00:00", "2026-10-12"]))
    assert pub.notna().tolist() == [True, True, False]
    assert alertas.dias_uteis(pub, fim).tolist()[:2] == [6, 0]  # 5 a 9/10 e 12/10; mesmo dia = 0
    assert pd.isna(alertas.dias_uteis(pub, fim).iloc[2])


def test_pontos_fiscais_com_os_relatorios_reais_de_agosto_2026():
    r = {**ind.extrair_rreo14(fx.itens(fx.RREO14_2026_4)), **ind.extrair_rreo01_receitas(fx.itens_rreo01(fx.RREO01_2026_4_RECEITAS))}
    e = ind.extrair_rgf_pessoal(fx.itens(fx.RGF01_2026_2_EXECUTIVO))
    leg = ind.extrair_rgf_pessoal(fx.itens(fx.RGF01_2026_2_LEGISLATIVO))
    pontos = alertas.pontos_fiscais(r, e, leg, False, "até agosto/2026", "RGF até agosto/2026", 8, 2026,
                                    investimentos=(287.7e6, 25.8e6))
    titulos = [p.titulo for p in pontos]
    assert titulos[0] == "Gasto com pessoal da Prefeitura: acima do limite de alerta" and pontos[0].nivel == "alerta"
    assert "Receitas de capital muito abaixo do previsto" in titulos  # 12,4 mi de 223,8 mi (5,5%)
    assert "Investimentos com execução baixa" in titulos
    assert not any("Câmara" in t or "Educação" in t or "Saúde" in t for t in titulos)  # dentro do limite / acima do mínimo


def test_minimo_descumprido_em_ano_fechado_e_critico():
    r = {"educacao_pct": 24.1, "educacao_minimo_pct": 25.0}
    pontos = alertas.pontos_fiscais(r, None, None, True, "até dezembro/2025", "–", 12, 2025)
    assert pontos[0].nivel == "critico" and pontos[0].titulo.startswith("Educação: abaixo do mínimo")
    parcial = alertas.pontos_fiscais(r, None, None, False, "até abril/2026", "–", 4, 2026)
    assert parcial[0].nivel == "info"


def _contratacao(id_, modalidade, amparo, estimado, homologado, publicacao, encerramento, situacao=1):
    linha = {c: "" for c in COLS_CONTRATACOES}
    linha.update(id_pncp=id_, modalidade_id=modalidade, amparo_codigo=amparo, amparo_nome="", situacao_id=situacao,
                 valor_estimado=estimado, valor_homologado=homologado, data_publicacao=publicacao,
                 data_encerramento=encerramento, objeto="Objeto", orgao_cnpj="76178037000176", srp="False")
    return linha


def _contrato(id_, compra, cnpj, valor, assinatura):
    linha = {c: "" for c in COLS_CONTRATOS}
    linha.update(id_pncp=id_, id_compra=compra, fornecedor_doc=cnpj, fornecedor_nome=f"EMPRESA {cnpj[:3]}",
                 fornecedor_tipo="PJ", valor_global=valor, data_assinatura=assinatura, receita="False", objeto="Objeto")
    return linha


def test_regras_de_compras():
    c = pd.DataFrame([
        _contratacao("e1", 8, 38, 100.0, None, "2026-03-02T09:00", ""),                         # emergência
        _contratacao("d1", 8, 19, 10.0, None, "2026-03-03T09:00", ""),                          # dispensa por valor
        _contratacao("d2", 8, 19, 10.0, None, "2026-04-03T09:00", ""),
        _contratacao("d3", 8, 18, 10.0, None, "2026-05-04T09:00", ""),
        _contratacao("p1", 6, 1, 1000.0, 995.0, "2026-06-05T09:00", "2026-06-10T09:00"),       # 3 dias úteis, sem desconto
        _contratacao("p2", 6, 1, 1000.0, 800.0, "2026-06-05T09:00", "2026-06-22T09:00"),       # 11 dias úteis
        _contratacao("x1", 6, 1, 500.0, None, "2026-06-05T09:00", "2026-06-08T09:00", situacao=2),  # revogada: ignorada
        _contratacao("v1", 8, 38, 99.0, None, "2025-12-30T09:00", ""),                          # outro ano
    ]).astype(str).replace({"None": ""})
    k = pd.DataFrame([_contrato(f"k{i}", f"d{i}", "10111222000105", 10.0, f"2026-0{2 + i}-10") for i in (1, 2, 3)]
                     + [_contrato("k9", "p2", "20333444000106", 800.0, "2026-07-01")]).astype(str)
    a = alertas.analisar_compras(tipar_contratacoes(c), tipar_contratos(k), 2026)
    assert a.emergenciais["id_pncp"].tolist() == ["e1"]
    assert a.prazo_curto["id_pncp"].tolist() == ["p1"] and a.prazo_curto["dias_uteis"].iloc[0] == 3
    assert a.sem_desconto["id_pncp"].tolist() == ["p1"]
    assert a.recorrentes["fornecedor_doc"].tolist() == ["10111222000105"] and a.recorrentes["contratos"].iloc[0] == 3
    assert len(a.canceladas) == 1
    assert round(a.direta_valor / a.total_valor, 4) == round(130 / 2130, 4)
    chaves = [p.chave for p in alertas.pontos_compras(a)]
    assert chaves[:3] == ["emergencia", "recorrentes", "prazo"] and "direta" in chaves and "desconto" in chaves
    assert "concentracao" in chaves and "contratos_incompletos" not in chaves

    # contratos de algum órgão ainda em coleta: as regras sobre fornecedores ficam suspensas e o motivo aparece
    incompleta = alertas.analisar_compras(tipar_contratacoes(c), tipar_contratos(k), 2026, orgaos_pendentes=["Prefeitura"])
    pontos = alertas.pontos_compras(incompleta)
    chaves = [p.chave for p in pontos]
    assert "recorrentes" not in chaves and "concentracao" not in chaves
    assert chaves[-1] == "contratos_incompletos" and pontos[-1].nivel == "incompleto"
    assert "Prefeitura" in pontos[-1].detalhe and "emergencia" in chaves  # as demais regras continuam
