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


def test_fornecedor_pessoa_fisica_e_mei_com_nome_e_sem_documento():
    assert pncp.fornecedor_publico("PF", "529.982.247-25", "FULANO DE TAL") == ("PF", "", "FULANO DE TAL")
    assert pncp.fornecedor_publico("PJ", "52998224725", "SEM TIPO CERTO")[0:2] == ("PF", "")  # documento de 11 dígitos
    assert pncp.fornecedor_publico("PF", "", "JOSE - CPF 529.982.247-25") == ("PF", "", "JOSE")
    # MEI antigo (CPF no fim do nome) e novo (CNPJ básico no começo): nome sem nenhum número
    assert pncp.fornecedor_publico("PJ", "60123456000110", "JOAO EXEMPLO 52998224725") == ("MEI", "", "JOAO EXEMPLO")
    assert pncp.fornecedor_publico("PJ", "45678901000112", "45.678.901 MARIA SOUZA") == ("MEI", "", "MARIA SOUZA")
    assert pncp.fornecedor_publico("PJ", "10.111.222/0001-05", "COMERCIAL EXEMPLO LTDA") == \
        ("PJ", "10111222000105", "COMERCIAL EXEMPLO LTDA")
    assert pncp.fornecedor_publico("PJ", "10111222000105", "3M DO BRASIL LTDA")[0] == "PJ"  # número curto não é MEI


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
    assert "52998224725" not in texto and "529.982.247-25" not in texto  # nenhum CPF gravado
    pessoas = contratos[contratos["fornecedor_tipo"].isin(["PF", "MEI"])]
    assert len(pessoas) and (pessoas["fornecedor_doc"] == "").all()   # pessoa física e MEI sem documento
    assert {"FULANO DE TAL", "JOAO EXEMPLO"} & set(pessoas["fornecedor_nome"])  # mas com o nome
    assert controle["politica_fornecedor"] == pncp.POLITICA_FORNECEDOR and controle["renovar_contratos"] == []
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


class ClienteComLimite:
    """Cliente do PNCP que "esgota o tempo" depois de N consultas, como acontece no robô do GitHub."""

    def __init__(self, cliente, limite: int):
        self.cliente, self.limite, self.chamadas = cliente, limite, []

    def _contar(self, chamada):
        if len(self.chamadas) >= self.limite:
            raise pncp.TempoEsgotado("tempo da coleta esgotado (teste)")
        self.chamadas.append(chamada)

    def contratacoes(self, inicio, fim, modalidade, municipio):
        self._contar(("contratações", inicio))
        return self.cliente.contratacoes(inicio, fim, modalidade, municipio)

    def contratos(self, inicio, fim, cnpj):
        self._contar(("contratos", inicio, cnpj))
        return self.cliente.contratos(inicio, fim, cnpj)


def test_tempo_curto_coleta_primeiro_o_trimestre_mais_recente_e_a_prefeitura(tmp_path):
    principal = "76178037000176"
    with servidor_simulado.servidor() as (url, _):
        cliente = ClienteComLimite(ClientePNCP(base_url=servidor_simulado.url_pncp(url), pausa=0),
                                   limite=len(pncp.MODALIDADES) + 1)
        contratacoes, contratos, controle = pncp.coletar_pncp(cliente, tmp_path, dt.date(2026, 10, 30), "4109401",
                                                              principal, dt.date(2024, 1, 1), {})
    assert cliente.chamadas[0] == ("contratações", "20261001")       # começa pelo trimestre mais recente
    assert cliente.chamadas[-1] == ("contratos", "20261001", principal)  # e logo busca os contratos da Prefeitura
    assert controle["status"] == "parcial"
    assert controle["janelas_ok"] == ["2026T4"] and controle["contratos_ok"] == {principal: ["2026T4"]}
    assert f"{principal} 2024T1" in controle["contratos_pendentes"]
    assert pncp.contratos_em_falta(controle, 2026) and len(contratacoes) > 0


def test_coleta_seguinte_completa_o_que_faltou(tmp_path):
    principal = "76178037000176"
    with servidor_simulado.servidor() as (url, _):
        base = ClientePNCP(base_url=servidor_simulado.url_pncp(url), pausa=0)
        _, _, controle = pncp.coletar_pncp(ClienteComLimite(base, limite=25), tmp_path, dt.date(2026, 10, 30),
                                           "4109401", principal, dt.date(2024, 1, 1), {})
        contratacoes, contratos, controle = pncp.coletar_pncp(base, tmp_path, dt.date(2026, 10, 30), "4109401",
                                                              principal, dt.date(2024, 1, 1), controle)
    assert controle["status"] == "ok" and not controle["contratos_pendentes"] and not controle["pendentes"]
    assert controle["orgaos"][0] == principal
    assert pncp.contratos_em_falta(controle) == []
    assert contratos["id_compra"].isin(contratacoes["id_pncp"]).mean() > 0.9


def test_orgaos_com_contratos_em_falta_nos_metadados_novos_e_antigos():
    novo = {"contratos_pendentes": ["76178037000176 2026T3", "11222333000181 2024T1"]}
    assert pncp.contratos_em_falta(novo) == ["11222333000181", "76178037000176"]
    assert pncp.contratos_em_falta(novo, 2026) == ["76178037000176"]
    antigo = {"pendentes": ["2024T1", "79262341000195 2025T2"]}  # coletor 1.2.0/1.2.1: sem contratos_pendentes
    assert pncp.contratos_em_falta(antigo) == ["79262341000195"]
    assert pncp.contratos_em_falta(antigo, 2026) == [] and pncp.contratos_em_falta({}) == []


def test_contratado_vem_do_contrato_ligado_a_compra():
    contratos = pncp.tipar_contratos(pncp._tabela([
        {"id_pncp": "c1", "id_compra": "compra-1", "fornecedor_nome": "MENOR LTDA", "valor_global": "100"},
        {"id_pncp": "c2", "id_compra": "compra-1", "fornecedor_nome": "MAIOR S.A.", "valor_global": "900"},
        {"id_pncp": "c3", "id_compra": "compra-1", "fornecedor_nome": "MAIOR S.A.", "valor_global": "50"},
        {"id_pncp": "c4", "id_compra": "compra-2", "fornecedor_nome": "FULANO DE TAL", "valor_global": "10"},
        {"id_pncp": "c5", "id_compra": "", "fornecedor_nome": "SEM LIGACAO LTDA", "valor_global": "10"},
    ], pncp.COLS_CONTRATOS, pncp.tipar_contratos))
    nomes = pncp.contratados_por_compra(contratos)
    assert nomes["compra-1"] == "MAIOR S.A. e mais 1"
    assert nomes["compra-2"] == "FULANO DE TAL"
    assert "" not in nomes.index


def test_regra_nova_de_fornecedores_renova_uma_vez_os_contratos_gravados(tmp_path):
    """Dados coletados pela 1.2.2 (pessoa física sem nome): a 1.2.3 busca de novo os contratos já gravados."""
    principal = "76178037000176"
    with servidor_simulado.servidor() as (url, _):
        base = ClientePNCP(base_url=servidor_simulado.url_pncp(url), pausa=0)
        _, contratos, controle = pncp.coletar_pncp(base, tmp_path, dt.date(2026, 10, 30), "4109401", principal,
                                                   dt.date(2024, 1, 1), {})
        # simula os arquivos e o controle gravados pela versão anterior
        antigos = contratos.copy()
        pf = antigos["fornecedor_tipo"].isin(["PF", "MEI"])
        antigos.loc[pf, "fornecedor_nome"] = "Pessoa física (dado protegido)"
        antigos.to_csv(tmp_path / "fContratos.csv", sep=";", index=False, encoding="utf-8-sig")
        velho = {k: v for k, v in controle.items() if k not in ("politica_fornecedor", "renovar_contratos")}

        # pouco tempo: a renovação começa e o que falta fica para a próxima execução (sem "contratos em falta")
        limitado = ClienteComLimite(base, limite=len(pncp.MODALIDADES) * 2 + 4)
        _, _, meio = pncp.coletar_pncp(limitado, tmp_path, dt.date(2026, 10, 30), "4109401", principal,
                                       dt.date(2024, 1, 1), velho)
        assert meio["renovar_contratos"] and meio["status"] == "parcial"
        assert pncp.contratos_em_falta(meio) == []

        _, contratos2, fim = pncp.coletar_pncp(base, tmp_path, dt.date(2026, 10, 30), "4109401", principal,
                                               dt.date(2024, 1, 1), meio)
    assert fim["renovar_contratos"] == [] and fim["status"] == "ok"
    assert "Pessoa física (dado protegido)" not in set(contratos2["fornecedor_nome"])
    assert len(contratos2) == len(contratos)
