"""Extração dos indicadores com linhas reais da API (gabarito de 30/10/2026)."""

import pytest

from despesas import indicadores as ind
from tests import fixtures_api as fx


def test_rreo14_valores_reais_de_2026():
    v = ind.extrair_rreo14(fx.itens(fx.RREO14_2026_4))
    assert v["receita_prevista_atualizada"] == 1171101596.73
    assert v["receita_realizada"] == 726358549.65
    assert v["despesa_dotacao_atualizada"] == 1302417760.30
    assert v["despesa_liquidada"] == 676044444.25
    assert v["despesa_empenhada"] == 739943915.03  # e não a linha "por função", que vem depois
    assert v["resultado_orcamentario"] == 50314105.40
    assert v["rcl"] == 929125228.65  # e não as RCL ajustadas
    assert v["rpps_resultado"] == 15278641.99
    assert (v["primario_meta"], v["primario_apurado"]) == (19273424.92, 11137948.37)
    assert (v["nominal_meta"], v["nominal_apurado"]) == (-68071790.03, 41775665.93)
    assert v["restos_a_pagar_saldo"] == 15424266.87  # linha TOTAL
    assert (v["educacao_pct"], v["educacao_minimo_pct"]) == (25.71, 25)
    assert (v["fundeb_pct"], v["fundeb_minimo_pct"]) == (91.75, 70)
    assert (v["saude_pct"], v["saude_minimo_pct"]) == (25.71, 15)


def test_rreo14_formato_antigo_sem_meta():
    v = ind.extrair_rreo14(fx.itens(fx.RREO14_2021_6_DIFERENCAS))
    assert v["primario_apurado"] == 61047980.92 and "primario_meta" not in v
    assert v["nominal_apurado"] == 60255063.55
    assert v["resultado_orcamentario"] == 99596345.55
    assert (v["educacao_pct"], v["saude_pct"]) == (25.89, 28.21)


def test_resultado_orcamentario_deficit_e_calculado():
    deficit = [("DeficitOrcamentarioDemonstrativoSimplificadoBalancoOrcamentario", "Déficit Orçamentário", "Até o Bimestre", 1000.0)]
    assert ind.extrair_rreo14(fx.itens(deficit))["resultado_orcamentario"] == -1000.0
    sem_linha = [l for l in fx.RREO14_2026_4 if not l[0].startswith("Superavit")]
    assert ind.extrair_rreo14(fx.itens(sem_linha))["resultado_orcamentario"] == 50314105.40


def test_rreo01_receitas_por_origem():
    v = ind.extrair_rreo01_receitas(fx.itens_rreo01(fx.RREO01_2026_4_RECEITAS))
    assert v["receita_total_prevista"] == 1161336596.73 and v["receita_total_realizada"] == 679787384.21
    assert v["receita_tributaria_realizada"] == 182033924.85
    assert v["receita_capital_prevista"] == 223774495.03
    assert "receita_uniao_prevista" not in v  # ausente no gabarito: fica em branco, nada é estimado


def test_rgf_pessoal_executivo_e_legislativo():
    e = ind.extrair_rgf_pessoal(fx.itens(fx.RGF01_2026_2_EXECUTIVO))
    assert e == {"pessoal_valor": 461997742.46, "pessoal_pct": 51.07, "pessoal_limite_maximo_pct": 54,
                 "pessoal_limite_prudencial_pct": 51.3, "pessoal_limite_alerta_pct": 48.6}
    leg = ind.extrair_rgf_pessoal(fx.itens(fx.RGF01_2026_2_LEGISLATIVO))
    assert (leg["pessoal_pct"], leg["pessoal_limite_maximo_pct"]) == (2.91, 6)


def test_rgf_divida_usa_a_coluna_do_quadrimestre():
    q2 = ind.extrair_rgf_divida(fx.itens(fx.RGF02_2026), quadrimestre=2)
    assert q2 == {"divida_consolidada": 79304484.47, "divida_liquida": -20247361.79, "divida_consolidada_pct": 8.64,
                  "divida_liquida_pct": -2.21, "divida_limite_senado": 1101632683.98}
    assert ind.extrair_rgf_divida(fx.itens(fx.RGF02_2026), quadrimestre=1)["divida_liquida_pct"] == -0.72
    assert ind.extrair_rgf_divida(fx.itens(fx.RGF02_2026), quadrimestre=3) == {}


@pytest.mark.parametrize("valor,esperado", [
    (47.5, "ok"), (48.6, "ok"), (51.07, "alerta"), (51.31, "grave"), (54.01, "critico"), (None, "sem_dado"),
])
def test_status_limite_pessoal(valor, esperado):
    assert ind.status_limite(valor, 48.6, 51.3, 54)[0] == esperado


def test_status_minimo_meta_e_divida():
    assert ind.status_minimo(25.71, 25, ano_fechado=False) == ("ok", "Acima do mínimo")
    assert ind.status_minimo(24.0, 25, ano_fechado=False)[0] == "alerta"
    assert ind.status_minimo(24.0, 25, ano_fechado=True)[0] == "critico"
    assert ind.status_meta(11137948.37, 19273424.92, ano_fechado=False)[0] == "info"
    assert ind.status_meta(11137948.37, 19273424.92, ano_fechado=True)[0] == "alerta"
    assert ind.status_meta(61047980.92, None, ano_fechado=True)[1] == "Meta não informada no relatório"
    assert ind.status_divida(-2.21)[0] == "ok"
    assert ind.status_divida(110)[0] == "alerta"
    assert ind.status_divida(121)[0] == "critico"
