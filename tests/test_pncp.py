"""Compras no PNCP: padronização, proteção de dados pessoais e coleta (API simulada no formato do manual)."""

import datetime as dt

from despesas import pncp
from despesas.api import ClientePNCP
from tests import servidor_simulado


def test_cpf_em_texto_livre_e_mascarado():
    texto = "Pagamento a Fulano, CPF 529.982.247-25, e a 52998224725; empresa 12.345.678/0001-90 (12345678000190)"
    saida = pncp.mascarar_cpf(texto)
    assert "529.982.247-25" not in saida and "52998224725" not in saida
    assert "12.345.678/0001-90" in saida and "12345678000190" in saida  # CNPJ não é dado pessoal


def test_fornecedor_pessoa_fisica_e_mei_sem_identificacao():
    assert pncp.fornecedor_publico("PF", "529.982.247-25", "FULANO DE TAL") == ("PF", "", "Pessoa física (dado protegido)")
    assert pncp.fornecedor_publico("PJ", "52998224725", "SEM TIPO CERTO")[0:2] == ("PF", "")  # documento de 11 dígitos
    assert pncp.fornecedor_publico("PJ", "60123456000110", "JOAO EXEMPLO 52998224725") == \
        ("PJ", "", "Microempreendedor individual (dado protegido)")
    assert pncp.fornecedor_publico("PJ", "10.111.222/0001-05", "COMERCIAL EXEMPLO LTDA") == \
        ("PJ", "10111222000105", "COMERCIAL EXEMPLO LTDA")


def test_campos_com_variacao_de_maiusculas():
    # o manual escreve "razaosocial" e "numeroControlePNCPCompra"; a API pode devolver outra grafia
    c = pncp.normalizar_contratacao({"numeroControlePNCP": "1-1-000001/2026", "modalidadeId": 8,
                                     "orgaoEntidade": {"cnpj": "76.178.037/0001-76", "razaosocial": "MUNICIPIO", "esferaId": "M"},
                                     "amparoLegal": {"codigo": 38, "nome": "Lei 14.133/2021, Art. 75, VIII"},
                                     "valorTotalEstimado": "1500.5", "dataPublicacaoPncp": "2026-10-05T09:30:00"})
    assert (c["orgao_cnpj"], c["orgao_nome"], c["modalidade"], c["valor_estimado"]) == \
        ("76178037000176", "MUNICIPIO", "Dispensa", 1500.5)
    for chave in ("numeroControlePNCPCompra", "numeroControlePncpCompra"):
        k = pncp.normalizar_contrato({"numeroControlePNCP": "x", chave: "1-1-000001/2026", "tipoPessoa": "PJ",
                                      "niFornecedor": "10111222000105", "nomeRazaoSocialFornecedor": "EMPRESA"})
        assert k["id_compra"] == "1-1-000001/2026"


def test_janelas_trimestrais_ate_hoje():
    j = pncp.janelas(dt.date(2024, 1, 1), dt.date(2026, 10, 30))
    assert [x.rotulo for x in j][:2] == ["2024T1", "2024T2"] and len(j) == 12
    assert (j[0].inicio, j[0].fim) == (dt.date(2024, 1, 1), dt.date(2024, 3, 31))
    assert (j[-1].inicio, j[-1].fim) == (dt.date(2026, 10, 1), dt.date(2026, 10, 30))
    assert [m.rotulo for m in pncp._meses(j[0])] == ["2024-01", "2024-02", "2024-03"]


def _coletar(pasta, limite_dias=None, recusar=None):
    with servidor_simulado.servidor(limite_dias_pncp=limite_dias, recusar_modalidades=recusar) as (url, contador):
        cliente = ClientePNCP(base_url=servidor_simulado.url_pncp(url), pausa=0)
        resultado = pncp.coletar_pncp(cliente, pasta, dt.date(2026, 10, 30), "4109401", "76178037000176",
                                      dt.date(2024, 1, 1), {})
    return resultado, contador


def test_coleta_filtra_orgaos_municipais_e_protege_dados(tmp_path):
    (contratacoes, contratos, controle), _ = _coletar(tmp_path)
    assert controle["status"] == "ok" and not controle["pendentes"]
    assert set(contratacoes["esfera"]) == {"M"}  # a universidade estadual simulada fica de fora
    assert "UNIVERSIDADE ESTADUAL (SIMULADA)" not in set(contratacoes["orgao_nome"])
    assert set(controle["orgaos"]) == {"76178037000176", "11222333000181"}
    texto = contratos.to_csv(sep=";")
    assert "52998224725" not in texto and "FULANO" not in texto and "JOAO EXEMPLO" not in texto
    assert (contratos["fornecedor_tipo"] == "PF").any()
    assert contratacoes["valor_estimado"].dtype.kind == "f"


def test_periodo_recusado_vira_consulta_mes_a_mes(tmp_path):
    (normal, _, _), cont_normal = _coletar(tmp_path / "a")
    (mensal, _, controle), cont_mensal = _coletar(tmp_path / "b", limite_dias=40)
    assert controle["status"] == "ok"
    assert len(mensal) == len(normal)
    assert cont_mensal["publicacao"] > cont_normal["publicacao"]


def test_modalidade_recusada_nao_derruba_a_coleta(tmp_path):
    (contratacoes, _, controle), _ = _coletar(tmp_path, recusar={15})
    assert controle["status"] == "ok" and controle["modalidades_recusadas"] == [15]
    assert len(contratacoes) > 0
