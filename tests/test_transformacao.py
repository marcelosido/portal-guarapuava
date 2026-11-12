"""Testes da regra contábil (MSC -> medidas) e da conferência com o RREO."""

import pandas as pd
import pytest

from despesas.transformacao import (
    COLUNAS_MEDIDAS,
    conciliar_com_rreo,
    dimensao_natureza,
    msc_para_fato,
    totais_rreo,
)


def linha(conta, valor, natureza_conta, classe=6, natureza="31901101", poder="10131", funcao="12", mes=8):
    """Linha no mesmo formato devolvido pela API (campos e tipos conferidos em 30/10/2026)."""
    return {
        "tipo_matriz": "MSCC", "cod_ibge": 4109401, "classe_conta": classe, "conta_contabil": conta,
        "poder_orgao": poder, "ano_fonte_recursos": 1, "fonte_recursos": "1500", "funcao": funcao,
        "subfuncao": "361", "exercicio": 2026, "mes_referencia": mes, "educacao_saude": None,
        "data_referencia": "2026-08-31T00:00:00Z", "entrada_msc": 421, "natureza_despesa": natureza,
        "ano_inscricao": None, "natureza_receita": None, "valor": valor, "natureza_conta": natureza_conta,
        "tipo_valor": "ending_balance", "complemento_fonte": None,
    }


# Saldos reais de Guarapuava, ago/2026, somados por conta (API consultada em 30/10/2026).
SALDOS_AGO_2026_CLASSE6 = [
    ("622110000", 507_646_108.72, "C"),
    ("622110000", 2_359_365.20, "D"),
    ("622120200", 57_188_571.29, "C"),
    ("622130100", 63_035_750.07, "C"),
    ("622130200", 863_720.71, "C"),
    ("622130300", 36_207_196.06, "C"),
    ("622130400", 639_837_248.19, "C"),
]
SALDOS_AGO_2026_CLASSE5 = [("522110100", 925_500_000.00, "D")]

# RREO Anexo 1, 4º bimestre/2026, linha "TOTAL DAS DESPESAS (XII)".
RREO_4BIM_2026 = {
    "dotacao_inicial": 925_498_530.46,
    "dotacao_atualizada": 1_302_417_760.30,
    "empenhado": 739_943_915.03,
    "liquidado": 676_044_444.25,
    "pago": 639_837_248.19,
}


def fato_ago_2026():
    c6 = [linha(c, v, n) for c, v, n in SALDOS_AGO_2026_CLASSE6]
    c5 = [linha(c, v, n, classe=5) for c, v, n in SALDOS_AGO_2026_CLASSE5]
    return msc_para_fato(c6, c5)


def test_medidas_batem_com_valores_reais_de_agosto_2026():
    tot = fato_ago_2026()[COLUNAS_MEDIDAS].sum().round(2)
    assert tot["empenhado"] == pytest.approx(RREO_4BIM_2026["empenhado"], abs=0.01)
    assert tot["liquidado"] == pytest.approx(RREO_4BIM_2026["liquidado"], abs=0.01)
    assert tot["pago"] == pytest.approx(RREO_4BIM_2026["pago"], abs=0.01)
    # Saldo devedor em conta credora entra negativo: 1.302.419.229,84 (e não 1.307.137.960,24)
    assert tot["dotacao_atualizada"] == pytest.approx(1_302_419_229.84, abs=0.01)
    assert tot["dotacao_inicial"] == pytest.approx(925_500_000.00, abs=0.01)


def test_chaves_e_tipos_da_tabela_fato():
    fato = msc_para_fato(
        [linha("622130400", 100.0, "C", natureza="33903999", funcao="10"),
         linha("622130400", 50.0, "C", natureza="33903999", funcao="10"),
         linha("622130300", 25.0, "C", natureza="31901101", funcao="12", poder="20231")]
    )
    assert len(fato) == 2
    assert fato["ano"].dtype == "int64" and fato["mes"].dtype == "int64"
    saude = fato[fato["funcao"] == "10"].iloc[0]
    assert saude["pago"] == 150.0 and saude["liquidado"] == 150.0 and saude["empenhado"] == 150.0
    camara = fato[fato["poder_orgao"] == "20231"].iloc[0]
    assert camara["pago"] == 0.0 and camara["liquidado"] == 25.0


def test_ignora_contas_que_nao_sao_da_despesa_e_entrada_vazia():
    assert msc_para_fato([]).empty
    fato = msc_para_fato([linha("631100000", 999.0, "C"), linha("611100000", 1.0, "C")])
    assert fato.empty


def test_campos_faltando_geram_erro_claro():
    with pytest.raises(ValueError, match="campos esperados"):
        msc_para_fato([{"valor": 1}])


def test_totais_rreo_e_conciliacao():
    itens = [
        {"cod_conta": "TotalDespesas", "conta": "TOTAL DAS DESPESAS (XII) = (X + XI)", "rotulo": "Padrão",
         "coluna": col, "valor": valor}
        for col, valor in [
            ("DOTAÇÃO INICIAL (d)", RREO_4BIM_2026["dotacao_inicial"]),
            ("DOTAÇÃO ATUALIZADA (e)", RREO_4BIM_2026["dotacao_atualizada"]),
            ("DESPESAS EMPENHADAS NO BIMESTRE", 1.0),
            ("DESPESAS EMPENHADAS ATÉ O BIMESTRE (f)", RREO_4BIM_2026["empenhado"]),
            ("DESPESAS LIQUIDADAS NO BIMESTRE", 1.0),
            ("DESPESAS LIQUIDADAS ATÉ O BIMESTRE (h)", RREO_4BIM_2026["liquidado"]),
            ("DESPESAS PAGAS ATÉ O BIMESTRE (j)", RREO_4BIM_2026["pago"]),
        ]
    ]
    itens.append({"cod_conta": "ReceitasCorrentes", "conta": "RECEITAS CORRENTES", "coluna": "DOTAÇÃO INICIAL (d)", "valor": 5.0})
    totais = totais_rreo(itens)
    assert totais == RREO_4BIM_2026

    rreo = pd.DataFrame([{"ano": 2026, "bimestre": 4, "medida": m, "valor_rreo": v} for m, v in totais.items()])
    conc = conciliar_com_rreo(fato_ago_2026(), rreo, tolerancia=1.0).set_index("medida")
    assert conc.loc["liquidado", "status"] == "Conciliado"
    assert conc.loc["empenhado", "status"] == "Conciliado"
    assert conc.loc["pago", "status"] == "Conciliado"
    assert conc.loc["dotacao_atualizada", "status"] == "Divergente"
    assert conc.loc["dotacao_atualizada", "diferenca"] == pytest.approx(1_469.54, abs=0.01)
    assert conc.loc["dotacao_inicial", "diferenca"] == pytest.approx(1_469.54, abs=0.01)


def test_conciliacao_sem_rreo_fica_pendente():
    conc = conciliar_com_rreo(fato_ago_2026(), pd.DataFrame(columns=["ano", "bimestre", "medida", "valor_rreo"]), 1.0)
    assert set(conc["status"]) == {"RREO indisponível"}


def test_dimensao_natureza():
    dim = dimensao_natureza(["31901101", "44905200", "99999999"]).set_index("natureza_despesa")
    assert dim.loc["31901101", "natureza_formatada"] == "3.1.90.11.01"
    assert dim.loc["31901101", "elemento_desc"] == "Vencimentos e Vantagens Fixas - Pessoal Civil"
    assert dim.loc["44905200", "grupo_desc"] == "Investimentos"
    assert dim.loc["44905200", "natureza6"] == "449052"
    assert dim.loc["99999999", "categoria_desc"] == "Reserva de Contingência"
