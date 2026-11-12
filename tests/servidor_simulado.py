"""APIs do SICONFI e do PNCP simuladas, para testar o coletor sem acesso à internet.

Reproduz o formato real das respostas (campos, tipos e paginação, conferidos em 30/10/2026 e
12/11/2026; PNCP conforme o Manual das APIs de Consultas 1.0). OS VALORES SÃO FICTÍCIOS – servem
só para testes e para demonstrar o portal. Uso manual:

    python -m tests.servidor_simulado            # sobe em http://127.0.0.1:8765/
    python coletar.py --url http://127.0.0.1:8765/ords/siconfi/tt/ \
        --pncp-url http://127.0.0.1:8765/api/consulta/ --anos 2025 2026 --pausa 0 --pasta data_demo
"""

from __future__ import annotations

import contextlib
import datetime as dt
import json
import random
import threading
from collections import Counter
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HOJE = dt.date(2026, 10, 30)  # MSC publicada até set/2026; RREO até o 4º bimestre/2026
TAMANHO_PAGINA = 300  # a API real usa 5.000; menor aqui para exercitar a paginação

# (poder/órgão, função, subfunção, natureza 6 dígitos, fonte, dotação inicial em 2026) – fictícios
COMBINACOES = [
    ("10131", "12", "361", "319011", "1540", 150e6), ("10131", "12", "361", "319013", "1540", 28e6),
    ("10131", "12", "365", "339030", "1500", 17e6), ("10131", "12", "361", "339039", "1550", 24e6),
    ("10131", "12", "361", "449051", "1500", 30e6), ("10131", "12", "361", "449052", "1500", 8e6),
    ("10131", "10", "301", "319011", "1500", 105e6), ("10131", "10", "302", "339039", "1600", 66e6),
    ("10131", "10", "301", "339030", "1600", 21e6), ("10131", "10", "302", "335043", "1600", 14e6),
    ("10131", "10", "305", "319004", "1600", 11e6), ("10131", "10", "302", "337170", "1600", 20e6),
    ("10131", "15", "451", "449051", "1500", 75e6), ("10131", "15", "452", "339039", "1500", 33e6),
    ("10131", "04", "122", "319011", "1500", 42e6), ("10131", "04", "122", "339040", "1500", 7e6),
    ("10131", "04", "122", "319113", "1500", 19e6), ("10131", "04", "122", "339197", "1500", 26e6),
    ("10131", "18", "542", "339039", "1500", 37e6), ("10131", "08", "244", "339039", "1660", 19e6),
    ("10131", "08", "244", "339048", "1660", 5e6), ("10131", "06", "181", "339030", "1500", 8e6),
    ("10131", "06", "182", "319011", "1500", 7e6), ("10131", "26", "782", "449051", "1500", 13e6),
    ("10131", "20", "606", "339030", "1500", 6e6), ("10131", "27", "812", "339039", "1500", 7e6),
    ("10131", "28", "843", "469071", "1500", 16e6), ("10131", "28", "843", "329021", "1500", 5e6),
    ("10131", "13", "392", "339039", "1500", 4e6), ("10131", "16", "482", "449051", "1500", 5e6),
    ("10131", "99", "999", "999999", "1500", 6e6),
    ("10132", "09", "272", "319001", "1800", 85e6), ("10132", "09", "272", "319003", "1800", 15e6),
    ("10132", "04", "122", "319011", "1802", 0.6e6), ("10132", "04", "122", "339039", "1802", 0.4e6),
    ("10132", "99", "999", "999999", "1800", 3e6),
    ("20231", "01", "031", "319011", "1500", 23e6), ("20231", "01", "031", "319013", "1500", 2.7e6),
    ("20231", "01", "031", "339039", "1500", 1.2e6), ("20231", "01", "031", "449052", "1500", 0.9e6),
]
DESDOBRAMENTOS = (("01", 0.6), ("02", 0.3), ("99", 0.1))
DIFERENCA_DOTACAO_RREO = 1_469.54  # imita a diferença real observada entre MSC e RREO


def _disponivel(ano: int, mes: int) -> bool:
    return (ano, mes) < (HOJE.year, HOJE.month)


def _execucao(natureza6: str, mes: int) -> tuple[float, float, float]:
    """Frações acumuladas (empenhado/dotação, liquidado/empenhado, pago/liquidado)."""
    t = mes / 12
    if natureza6.startswith("9"):
        return 0.0, 0.0, 0.0
    if natureza6[:2] in ("44", "46"):
        return min(0.95, 0.15 + 0.7 * t ** 1.3), 0.55 + 0.35 * t, 0.9
    if natureza6[:2] == "33":
        return min(0.97, 0.30 + 0.65 * t), 0.80 + 0.15 * t, 0.94
    return 0.985 * t, 0.99, 0.97


def gerar_msc(ano: int, mes: int, classe: int, id_ente: str) -> list[dict]:
    if not _disponivel(ano, mes) or ano < 2019:
        return []
    fator_ano = 1.0 / (1.07 ** (2026 - ano))
    linhas = []
    for poder, funcao, subfuncao, nat6, fonte, base in COMBINACOES:
        dot_ini = base * fator_ano
        reforco = 0.0 if nat6.startswith("9") else (0.30 if nat6[:2] in ("44", "46") else 0.12)
        dot_atu = dot_ini * (1 + reforco * min(1.0, mes / 9)) - (dot_ini * 0.5 * min(1.0, mes / 6) if nat6.startswith("9") else 0)
        f_emp, f_liq, f_pag = _execucao(nat6, mes)
        for desd, peso in DESDOBRAMENTOS:
            d_ini, d_atu = dot_ini * peso, dot_atu * peso
            emp = d_atu * f_emp
            liq = emp * f_liq
            pag = liq * f_pag
            indisp = d_atu * 0.02 if nat6[:2] == "33" else 0.0
            em_liq = (emp - liq) * 0.01
            if classe == 6:
                saldos = [
                    ("622110000", d_atu - emp - indisp), ("622120200", indisp),
                    ("622130100", emp - liq - em_liq), ("622130200", em_liq),
                    ("622130300", liq - pag), ("622130400", pag),
                    ("631100000", d_ini * 0.01),  # restos a pagar: não entra nas medidas do ano
                ]
                natureza_normal = "C"
            else:
                saldos = [
                    ("522110100", d_ini), ("522120100", max(0.0, d_atu - d_ini)),
                    ("522190400", max(0.0, d_ini - d_atu)), ("522130100", max(0.0, d_atu - d_ini)),
                ]
                natureza_normal = "D"
            for conta, valor in saldos:
                if abs(valor) < 0.005:
                    continue
                natureza_conta = natureza_normal
                if conta == "522190400":
                    natureza_conta = "C"
                if valor < 0:
                    natureza_conta = "D" if natureza_normal == "C" else "C"
                linhas.append({
                    "tipo_matriz": "MSCC", "cod_ibge": int(id_ente), "classe_conta": classe,
                    "conta_contabil": conta, "poder_orgao": poder, "ano_fonte_recursos": 1,
                    "fonte_recursos": fonte, "funcao": funcao, "subfuncao": subfuncao, "exercicio": ano,
                    "mes_referencia": mes, "educacao_saude": None,
                    "data_referencia": f"{ano}-{mes:02d}-28T00:00:00Z", "entrada_msc": 1,
                    "natureza_despesa": nat6 + desd, "ano_inscricao": None, "natureza_receita": None,
                    "valor": round(abs(valor), 2), "natureza_conta": natureza_conta,
                    "tipo_valor": "ending_balance", "complemento_fonte": None,
                })
    return linhas


def _base(ano, periodo, id_ente, demonstrativo, anexo, periodicidade, **extra):
    return {"exercicio": ano, "demonstrativo": demonstrativo, "periodo": periodo, "periodicidade": periodicidade,
            "instituicao": "Prefeitura Municipal (simulada)", "cod_ibge": int(id_ente), "uf": "PR",
            "populacao": 189630 if str(id_ente) == "4109401" else 0, "anexo": anexo, "esfera": "M",
            "rotulo": "Padrão", **extra}


def _totais_msc(ano: int, mes: int, id_ente: str):
    from despesas.transformacao import msc_para_fato  # import tardio: só para calcular os totais

    return msc_para_fato(gerar_msc(ano, mes, 6, id_ente), gerar_msc(ano, mes, 5, id_ente)).sum(numeric_only=True)


# Receitas fictícias: (cod_conta, conta, previsão anual em 2026)
RECEITAS = [
    ("ReceitaTributaria", "IMPOSTOS, TAXAS E CONTRIBUIÇÕES DE MELHORIA", 230e6),
    ("ReceitaDeContribuicoes", "CONTRIBUIÇÕES", 40e6),
    ("ReceitaPatrimonial", "RECEITA PATRIMONIAL", 14e6),
    ("TransferenciasCorrentesDaUniaoEDeSuasEntidades", "Transferências da União e de suas Entidades", 230e6),
    ("TransferenciasCorrentesDosEstadosEDoDistritoFederalEDeSuasEntidades",
     "Transferências dos Estados e do Distrito Federal e de suas Entidades", 215e6),
    ("TransferenciasCorrentesDeOutrasInstituicoesPublicas", "Transferências de Outras Instituições Públicas", 140e6),
    ("OutrasReceitasCorrentes", "OUTRAS RECEITAS CORRENTES", 15e6),
    ("ReceitasDeCapital", "RECEITAS DE CAPITAL", 180e6),
]


def gerar_rreo(ano: int, bimestre: int, id_ente: str, anexo: str = "RREO-Anexo 01") -> list[dict]:
    mes = bimestre * 2
    if not _disponivel(ano, mes) or ano < 2019:
        return []
    tot = _totais_msc(ano, mes, id_ente)
    fator_ano = 1.0 / (1.07 ** (2026 - ano))
    fracao = mes / 12
    if anexo == "RREO-Anexo 01":
        base = _base(ano, bimestre, id_ente, "RREO", anexo, "B")
        colunas = [
            ("DOTAÇÃO INICIAL (d)", tot["dotacao_inicial"] - DIFERENCA_DOTACAO_RREO),
            ("DOTAÇÃO ATUALIZADA (e)", tot["dotacao_atualizada"] - DIFERENCA_DOTACAO_RREO),
            ("DESPESAS EMPENHADAS NO BIMESTRE", 0.0),
            ("DESPESAS EMPENHADAS ATÉ O BIMESTRE (f)", tot["empenhado"]),
            ("DESPESAS LIQUIDADAS ATÉ O BIMESTRE (h)", tot["liquidado"]),
            ("DESPESAS PAGAS ATÉ O BIMESTRE (j)", tot["pago"]),
        ]
        itens = [{**base, "coluna": col, "cod_conta": "TotalDespesas", "conta": "TOTAL DAS DESPESAS (XII) = (X + XI)",
                  "valor": round(float(v), 2)} for col, v in colunas]
        prev = {c: v * fator_ano for c, _, v in RECEITAS}
        real = {c: v * fracao * (0.15 if c == "ReceitasDeCapital" else 1.02) for c, v in prev.items()}
        correntes = [c for c, _, _ in RECEITAS if c != "ReceitasDeCapital"]
        transf = [c for c in correntes if c.startswith("Transferencias")]
        linhas = [("ReceitasExcetoIntraOrcamentarias", "RECEITAS (EXCETO INTRA-ORÇAMENTÁRIAS) (I)",
                   sum(prev.values()), sum(real.values())),
                  ("ReceitasCorrentes", "RECEITAS CORRENTES", sum(prev[c] for c in correntes), sum(real[c] for c in correntes)),
                  ("TransferenciasCorrentes", "TRANSFERÊNCIAS CORRENTES", sum(prev[c] for c in transf), sum(real[c] for c in transf))]
        linhas += [(c, nome, prev[c], real[c]) for c, nome, _ in RECEITAS]
        for codigo, conta, p_, r_ in linhas:
            itens.append({**base, "coluna": "PREVISÃO ATUALIZADA (a)", "cod_conta": codigo, "conta": conta, "valor": round(p_, 2)})
            itens.append({**base, "coluna": "Até o Bimestre (c)", "cod_conta": codigo, "conta": conta, "valor": round(r_, 2)})
        return itens
    if anexo == "RREO-Anexo 14":
        from tests.fixtures_api import RREO14_2026_4

        base = _base(ano, bimestre, id_ente, "RREO", anexo, "B")
        receita_prevista = sum(v for _, _, v in RECEITAS) * fator_ano
        receita_realizada = receita_prevista * fracao * 0.97
        valores = {
            "PrevisaoInicial": receita_prevista * 0.82, "PrevisaoAtualizada": receita_prevista,
            "ReceitasRealizadas": receita_realizada, "SaldoDeExerciciosAnteriores": 0.1 * receita_prevista,
            "DotacaoInicial": tot["dotacao_inicial"] - DIFERENCA_DOTACAO_RREO,
            "DotacaoAtualizada": tot["dotacao_atualizada"] - DIFERENCA_DOTACAO_RREO,
            "DespesasEmpenhadasDemonstrativoSimplificadoBalanco": tot["empenhado"],
            "DespesasLiquidadasDemonstrativoSimplificadoBalanco": tot["liquidado"],
            "DespesasPagas": tot["pago"], "SuperavitOrcamentario": receita_realizada - tot["liquidado"],
            "ReceitaCorrenteLiquida": 0.78 * receita_prevista,
            "ResultadoPrevidenciario": 0.012 * receita_prevista * fracao,
        }
        itens = []
        for codigo, conta, coluna, valor in RREO14_2026_4:
            v = next((x for prefixo, x in valores.items() if codigo.startswith(prefixo)), valor * fator_ano * fracao / (8 / 12))
            if coluna.startswith("% Aplicado"):
                if "FUNDEB" in codigo:
                    v = 88.0 + (ano - 2024)
                elif codigo.startswith("Minimo"):
                    v = 25.4 + (ano - 2024) * 0.4
                else:
                    v = 21.0 + (ano - 2024) * 1.5
            elif coluna.startswith("% Mínimo"):
                v = valor
            if codigo.startswith("ResultadoPrimario") and ano <= 2024:  # formato antigo: sem meta, outro código
                if coluna.startswith("Meta"):
                    continue
                codigo, conta = "ResultadoPrimarioDemonstrativoSimplificado", "RESULTADO PRIMÁRIO"
            itens.append({**base, "cod_conta": codigo, "conta": conta, "coluna": coluna, "valor": round(float(v), 2)})
        return itens
    return []


# Despesa com pessoal fictícia (% da RCL ajustada): sobe até passar o limite de alerta.
PESSOAL_PCT = {2024: (46.8, 47.4, 47.9), 2025: (48.4, 49.1, 49.8), 2026: (50.4, 51.07, 51.2)}


def gerar_rgf(ano: int, quadrimestre: int, id_ente: str, anexo: str, poder: str) -> list[dict]:
    if not _disponivel(ano, quadrimestre * 4) or ano not in PESSOAL_PCT:
        return []
    from tests.fixtures_api import RGF01_2026_2_EXECUTIVO, RGF01_2026_2_LEGISLATIVO, RGF02_2026

    base = _base(ano, quadrimestre, id_ente, "RGF", anexo, "Q", co_poder=poder)
    if anexo == "RGF-Anexo 01":
        pct = PESSOAL_PCT[ano][quadrimestre - 1] if poder == "E" else 2.9 + 0.05 * quadrimestre
        modelo = RGF01_2026_2_EXECUTIVO if poder == "E" else RGF01_2026_2_LEGISLATIVO
        itens = []
        for codigo, conta, coluna, valor in modelo:
            v = valor
            if codigo == "DespesaComPessoalTotal":
                v = pct if coluna.startswith("%") else valor * pct / 51.07
            itens.append({**base, "cod_conta": codigo, "conta": conta, "coluna": coluna, "valor": round(float(v), 2)})
        return itens
    if anexo == "RGF-Anexo 02" and poder == "E":
        itens = []
        colunas = ["SALDO DO EXERCÍCIO ANTERIOR"] + [f"Até o {q}º Quadrimestre" for q in range(1, quadrimestre + 1)]
        for codigo, conta, coluna, valor in RGF02_2026:
            if coluna != "SALDO DO EXERCÍCIO ANTERIOR":
                continue
            for i, col in enumerate(colunas):
                v = valor * (1 - 0.06 * i) if not codigo.startswith("Limite") else valor
                itens.append({**base, "cod_conta": codigo, "conta": conta, "coluna": col, "valor": round(float(v), 2)})
        return itens
    return []


# =====================================================================================
# Comparativo entre municípios (todos os municípios do PR, a partir da malha do IBGE)
# =====================================================================================
ID_PRINCIPAL = "4109401"
_MALHA = Path(__file__).resolve().parent.parent / "despesas" / "recursos" / "malha_pr.geojson"
POPULACAO_CONHECIDA = {"4109401": 189630, "4106902": 1829225, "4113700": 580870, "4115200": 436472,
                       "4119905": 371718, "4104808": 360366, "4125506": 344573, "4108304": 290466,
                       "4105805": 245063, "4100103": 7321}


def municipios_pr() -> list[tuple[str, str, int]]:
    """(código IBGE, nome, população fictícia) dos 399 municípios do PR."""
    g = json.loads(_MALHA.read_text(encoding="utf-8"))
    saida = []
    for f in g["features"]:
        cod, nome = f["properties"]["id"], f["properties"]["name"]
        rnd = random.Random(int(cod))
        pop = POPULACAO_CONHECIDA.get(cod) or int(2500 + rnd.paretovariate(1.25) * 4000)
        saida.append((cod, nome, min(pop, 250000)))
    return sorted(saida)


def _perfil(cod: str) -> dict:
    """Características fictícias e estáveis de cada município."""
    rnd = random.Random(int(cod) * 7 + 3)
    pop = dict((c, p) for c, _, p in municipios_pr()).get(cod, 20000)
    simplificado = pop < 50000 and int(cod) % 2 == 0
    return {
        "pop": pop, "simplificado": simplificado,
        "rcl_hab": rnd.uniform(3800, 6500) * (1.25 if pop < 10000 else 1.0),
        "educacao_pct": round(rnd.uniform(23.5, 33.0), 2), "saude_pct": round(rnd.uniform(17.0, 31.0), 2),
        "fundeb_pct": round(rnd.uniform(70.5, 99.0), 2), "pessoal_pct": round(rnd.uniform(38.0, 55.5), 2),
        "f_educ": rnd.uniform(0.24, 0.33), "f_saude": rnd.uniform(0.22, 0.34), "f_transp": rnd.uniform(0.0, 0.07),
        "f_urb": rnd.uniform(0.03, 0.14), "f_assist": rnd.uniform(0.02, 0.05), "f_invest": rnd.uniform(0.04, 0.16),
        "sem_dca": int(cod) % 41 == 0, "sem_rreo6": int(cod) % 97 == 0,
    }


def gerar_extrato(cod: str, ano: int) -> list[dict]:
    if cod not in {c for c, _, _ in municipios_pr()}:
        return []
    p = _perfil(cod)
    nome = dict((c, n) for c, n, _ in municipios_pr())[cod]
    pref, cam = f"Prefeitura Municipal de {nome} - PR", f"Câmara Municipal de {nome} - PR"
    rreo = "Relatório Resumido de Execução Orçamentária" + (" Simplificado" if p["simplificado"] else "")
    rgf = "Relatório de Gestão Fiscal" + (" Simplificado" if p["simplificado"] else "")
    periodicidade, n_rgf = ("S", 2) if p["simplificado"] else ("Q", 3)
    linhas = [(pref, rreo, b, "B") for b in range(1, 6 if p["sem_rreo6"] else 7)]
    linhas += [(i, rgf, q, periodicidade) for i in (pref, cam) for q in range(1, n_rgf + 1)]
    if not p["sem_dca"]:
        linhas.append((pref, "Balanço Anual (DCA)", 1, "A"))
    return [{"exercicio": ano, "cod_ibge": int(cod), "populacao": p["pop"], "instituicao": i, "entregavel": e,
             "periodo": per, "periodicidade": peri, "status_relatorio": "HO", "data_status": f"{ano + 1}-01-30T10:00:00Z",
             "forma_envio": "P", "tipo_relatorio": "S" if "Simplificado" in e else "P"} for i, e, per, peri in linhas]


def gerar_rreo14_municipio(cod: str, ano: int, tipo: str) -> list[dict]:
    p = _perfil(cod)
    if p["sem_rreo6"] or (tipo == "RREO Simplificado") != p["simplificado"]:
        return []
    from tests.fixtures_api import RREO14_2026_4

    rcl = p["rcl_hab"] * p["pop"]
    valores = {"ReceitaCorrenteLiquidaDemonstrativoSimplificado": rcl,
               "ReceitasRealizadas": rcl * 1.12, "DespesasLiquidadas": rcl * 1.07, "DotacaoAtualizada": rcl * 1.3}
    base = _base(ano, 6, cod, tipo, "RREO-Anexo 14", "B")
    base["populacao"] = p["pop"]
    itens = []
    for codigo, conta, coluna, valor in RREO14_2026_4:
        v = next((x for prefixo, x in valores.items() if codigo.startswith(prefixo)), valor * rcl / 929125228.65)
        if coluna.startswith("% Aplicado"):
            v = p["fundeb_pct"] if "FUNDEB" in codigo else p["educacao_pct"] if codigo.startswith("Minimo") else p["saude_pct"]
        elif coluna.startswith("% Mínimo"):
            v = valor
        itens.append({**base, "cod_conta": codigo, "conta": conta, "coluna": coluna, "valor": round(float(v), 2)})
    return itens


def gerar_rgf_municipio(cod: str, ano: int, periodo: int, periodicidade: str, tipo: str) -> list[dict]:
    p = _perfil(cod)
    esperado = ("S", 2, "RGF Simplificado") if p["simplificado"] else ("Q", 3, "RGF")
    if (periodicidade, periodo, tipo) != esperado:
        return []
    from tests.fixtures_api import RGF01_2026_2_EXECUTIVO

    rcl = p["rcl_hab"] * p["pop"]
    base = _base(ano, periodo, cod, tipo, "RGF-Anexo 01", periodicidade, co_poder="E")
    itens = []
    for codigo, conta, coluna, valor in RGF01_2026_2_EXECUTIVO:
        v = valor * rcl / 929125228.65
        if codigo == "DespesaComPessoalTotal":
            v = p["pessoal_pct"] if coluna.startswith("%") else rcl * p["pessoal_pct"] / 100
        elif coluna.startswith("%"):
            v = valor
        itens.append({**base, "cod_conta": codigo, "conta": conta, "coluna": coluna, "valor": round(float(v), 2)})
    return itens


def gerar_dca(cod: str, ano: int, anexo: str) -> list[dict]:
    p = _perfil(cod)
    if p["sem_dca"]:
        return []
    rcl = p["rcl_hab"] * p["pop"]
    base = {"exercicio": ano, "instituicao": "Prefeitura (simulada)", "cod_ibge": int(cod), "uf": "PR",
            "anexo": anexo, "rotulo": "Padrão", "populacao": p["pop"]}
    colunas = ("Despesas Empenhadas", "Despesas Liquidadas", "Despesas Pagas")
    fatores = (1.06, 1.0, 0.97)
    linhas = []
    if anexo == "DCA-Anexo I-E":
        funcoes = {"12 - Educação": p["f_educ"], "10 - Saúde": p["f_saude"], "26 - Transporte": p["f_transp"],
                   "15 - Urbanismo": p["f_urb"], "08 - Assistência Social": p["f_assist"], "04 - Administração": 0.12,
                   "01 - Legislativa": 0.03}
        total = sum(funcoes.values()) * rcl
        blocos = [("Despesas Exceto Intraorçamentárias", total, funcoes, 1.0),
                  ("Despesas Intraorçamentárias", total * 0.04, {"12 - Educação": 0.3, "10 - Saúde": 0.2}, 0.04)]
        for titulo, valor_total, fs, escala in blocos:
            linhas.append(("TotalDespesas", titulo, valor_total))
            for conta, frac in fs.items():
                linhas.append(("TotalDespesas", conta, frac * rcl * escala))
                linhas.append(("TotalDespesas", conta[:2] + ".122 - Administração Geral", frac * rcl * escala * 0.3))
    elif anexo == "DCA-Anexo I-D":
        linhas = [("DO3.1.00.00.00.00", "3.1.00.00.00 - Pessoal e Encargos Sociais", rcl * p["pessoal_pct"] / 100),
                  ("DO4.4.00.00.00.00", "4.4.00.00.00 - Investimentos", rcl * p["f_invest"]),
                  ("TotalDespesas", "Total Geral da Despesa", rcl * 1.07)]
    return [{**base, "cod_conta": c, "conta": n, "coluna": col, "valor": round(v * f, 2)}
            for c, n, v in linhas for col, f in zip(colunas, fatores)]


# Receita mês a mês (RREO Anexo 3): valores de 12 meses na ordem de grandeza de Guarapuava, sazonalidade fictícia.
RECEITA_12M = {
    "IPTULiquidoExcetoTransferenciasEFUNDEB": ("IPTU", 42.9e6), "ISSLiquidoExcetoTransferenciasEFUNDEB": ("ISS", 113.6e6),
    "ITBILiquidoExcetoTransferenciasEFUNDEB": ("ITBI", 22.9e6), "IRRFLiquidoExcetoTransferenciasEFUNDEB": ("IRRF", 64.9e6),
    "OutrasReceitasTributarias": ("Outros Impostos, Taxas e Contribuições de Melhoria", 28.4e6),
    "RREO3ReceitaDeContribuicoes": ("Contribuições", 62.7e6), "RendimentosDeAplicacaoFinanceira":
    ("Rendimentos de Aplicação Financeira", 60.0e6), "RREO3ReceitaDeServicos": ("Receita de Serviços", 0.33e6),
    "RREO3CotaParteDoFPM": ("Cota-Parte do FPM", 187.0e6), "RREO3CotaParteDoICMS": ("Cota-Parte do ICMS", 179.9e6),
    "RREO3CotaParteDoIPVA": ("Cota-Parte do IPVA", 49.2e6), "RREO3CotaParteDoITR": ("Cota-Parte do ITR", 8.7e6),
    "RREO3TransferenciasDaLC611989": ("Transferências da LC nº 61/1989", 2.8e6),
    "RREO3TransferenciasDoFUNDEB": ("Transferências do FUNDEB", 156.0e6),
    "RREO3OutrasTransferenciasCorrentes": ("Outras Transferências Correntes", 105.0e6),
    "RREO3OutrasReceitasCorrentes": ("Outras Receitas Correntes", 12.2e6),
}
SAZONALIDADE = {"IPTULiquidoExcetoTransferenciasEFUNDEB": [6, 2, 2.5, 1.5, 0.6, 0.6, 0.8, 0.8, 0.6, 0.5, 0.5, 0.6],
                "RREO3CotaParteDoIPVA": [3, 2.5, 2.2, 1.2, 1, 0.6, 0.5, 0.4, 0.4, 0.4, 0.4, 0.4]}


def gerar_rreo03(ano: int, bimestre: int, id_ente: str) -> list[dict]:
    mes = 2 * bimestre
    if not _disponivel(ano, mes) or ano < 2019:
        return []
    base = _base(ano, bimestre, id_ente, "RREO", "RREO-Anexo 03", "B")
    itens = []
    totais = {}
    for codigo, (conta, valor_12m) in RECEITA_12M.items():
        pesos = SAZONALIDADE.get(codigo, [1] * 12)
        soma = 0.0
        for k in range(11, -1, -1):
            indice = ano * 12 + (mes - 1) - k
            a, m = indice // 12, indice % 12 + 1
            v = valor_12m / sum(pesos) * pesos[m - 1] / (1.07 ** (2026 - a))
            soma += v
            itens.append({**base, "cod_conta": codigo, "conta": conta, "coluna": f"<MR-{k}>" if k else "<MR>",
                          "valor": round(v, 2)})
        itens.append({**base, "cod_conta": codigo, "conta": conta, "coluna": "TOTAL (ÚLTIMOS 12 MESES)", "valor": round(soma, 2)})
        itens.append({**base, "cod_conta": codigo, "conta": conta, "coluna": f"PREVISÃO ATUALIZADA {ano}",
                      "valor": round(valor_12m / (1.07 ** (2026 - ano)) * 0.97, 2)})
        totais[codigo] = soma
    tributos = [c for c in RECEITA_12M if "Liquido" in c or c == "OutrasReceitasTributarias"]
    transf = [c for c in RECEITA_12M if c.startswith("RREO3CotaParte") or c.startswith("RREO3Transferencias")
              or c == "RREO3OutrasTransferenciasCorrentes"]
    correntes = sum(totais.values())
    deducoes = correntes * 0.153
    for codigo, conta, valor in [
        ("ReceitaTributariaLiquidaExcetoTransferenciasEFUNDEB", "Impostos, Taxas e Contribuições de Melhoria",
         sum(totais[c] for c in tributos)),
        ("RREO3TransferenciasCorrentes", "Transferências Correntes", sum(totais[c] for c in transf)),
        ("ReceitasCorrentesLiquidasExcetoTransferenciasEFUNDEB", "RECEITAS CORRENTES (I)", correntes),
        ("DeducoesDaReceitaCorrenteLiquida", "DEDUÇÕES (II)", deducoes),
        ("DeducaoDeReceitaParaFormacaoDoFUNDEB", "Dedução de Receita para Formação do FUNDEB", deducoes * 0.49),
        ("RREO3ReceitaCorrenteLiquida", "RECEITA CORRENTE LÍQUIDA (III) = (I - II)", correntes - deducoes),
    ]:
        itens.append({**base, "cod_conta": codigo, "conta": conta, "coluna": "TOTAL (ÚLTIMOS 12 MESES)", "valor": round(valor, 2)})
    return itens


# =====================================================================================
# PNCP (contratações e contratos) – Manual das APIs de Consultas 1.0. Valores fictícios.
# =====================================================================================
ORGAOS_PNCP = [("76178037000176", "MUNICIPIO DE GUARAPUAVA", "M"),
               ("11222333000181", "CAMARA MUNICIPAL (SIMULADA)", "M"),
               ("44555666000181", "UNIVERSIDADE ESTADUAL (SIMULADA)", "E")]
FORNECEDORES = [("PJ", "10111222000105", "COMERCIAL EXEMPLO LTDA"), ("PJ", "20333444000106", "CONSTRUTORA MODELO S.A."),
                ("PJ", "30555666000107", "SERVICOS DEMONSTRATIVOS EIRELI"), ("PJ", "40777888000108", "DISTRIBUIDORA FICTICIA LTDA"),
                ("PJ", "50999000000109", "TECNOLOGIA SIMULADA LTDA"), ("PF", "52998224725", "FULANO DE TAL"),
                ("PJ", "60123456000110", "JOAO EXEMPLO 52998224725")]
AMPAROS = {1: "Lei 14.133/2021, Art. 28, I", 6: "Lei 14.133/2021, Art. 74, I", 18: "Lei 14.133/2021, Art. 75, I",
           19: "Lei 14.133/2021, Art. 75, II", 38: "Lei 14.133/2021, Art. 75, VIII", 50: "Lei 14.133/2021, Art. 74, caput"}
NOMES_MODALIDADE = {4: "Concorrência - Eletrônica", 6: "Pregão - Eletrônico", 8: "Dispensa", 9: "Inexigibilidade",
                    12: "Credenciamento"}


def _dados_pncp():
    """Gera (contratações, contratos) de jan/2024 até HOJE, de forma determinística."""
    if hasattr(_dados_pncp, "cache"):
        return _dados_pncp.cache
    compras, contratos = [], []
    seq = Counter()
    d = dt.date(2024, 1, 2)
    while d < HOJE:
        rnd = random.Random(d.toordinal())
        for _ in range(rnd.choice([0, 1, 1, 2])):
            cnpj, razao, esfera = ORGAOS_PNCP[0] if rnd.random() < 0.8 else rnd.choice(ORGAOS_PNCP[1:])
            mod = rnd.choices([6, 8, 9, 4, 12], weights=[40, 38, 9, 6, 7])[0]
            amparo = {6: 1, 4: 1, 12: 1, 9: rnd.choice([6, 50])}.get(mod) or rnd.choices([19, 18, 38], weights=[80, 14, 6])[0]
            seq[(cnpj, d.year)] += 1
            n = seq[(cnpj, d.year)]
            estimado = round(rnd.lognormvariate(11.5, 1.2) * (4 if mod == 4 else 1), 2)
            homologado = round(estimado * rnd.choice([0.78, 0.85, 0.9, 0.97, 0.995]), 2) if rnd.random() < 0.75 else None
            prazo = rnd.choice([5, 6, 9, 10, 12, 15, 20]) if mod in (4, 6) else 3
            situacao = rnd.choices([1, 2, 3], weights=[94, 4, 2])[0]
            pub = dt.datetime(d.year, d.month, d.day, 9, 30)
            registro = {
                "numeroControlePNCP": f"{cnpj}-1-{n:06d}/{d.year}", "numeroCompra": f"{n}/{d.year}", "anoCompra": d.year,
                "processo": f"{1000 + n}/{d.year}", "tipoInstrumentoConvocatorioId": 1 if mod in (4, 6) else 3,
                "tipoInstrumentoConvocatorioNome": "Edital" if mod in (4, 6) else "Ato que autoriza a Contratação Direta",
                "modalidadeId": mod, "modalidadeNome": NOMES_MODALIDADE[mod], "modoDisputaId": 1, "modoDisputaNome": "Aberto",
                "situacaoCompraId": situacao, "situacaoCompraNome": {1: "Divulgada no PNCP", 2: "Revogada", 3: "Anulada"}[situacao],
                "objetoCompra": rnd.choice(["Aquisição de material de expediente", "Contratação de serviços de manutenção predial",
                                            "Aquisição de medicamentos", "Pavimentação de vias urbanas", "Locação de veículos",
                                            "Serviços de limpeza", "Aquisição de merenda escolar"]),
                "informacaoComplementar": "", "srp": rnd.random() < 0.3,
                "amparoLegal": {"codigo": amparo, "nome": AMPAROS[amparo], "descricao": ""},
                "valorTotalEstimado": estimado, "valorTotalHomologado": homologado,
                "dataAberturaProposta": (pub + dt.timedelta(days=1)).isoformat(),
                "dataEncerramentoProposta": (pub + dt.timedelta(days=prazo)).isoformat(),
                "dataPublicacaoPncp": pub.isoformat(), "dataInclusao": pub.isoformat(),
                "dataAtualizacao": (pub + dt.timedelta(days=20)).isoformat(), "sequencialCompra": n,
                "orgaoEntidade": {"cnpj": cnpj, "razaoSocial": razao, "poderId": "N", "esferaId": esfera},
                "unidadeOrgao": {"codigoUnidade": "1", "nomeUnidade": razao, "codigoIbge": ID_PRINCIPAL,
                                 "municipioNome": "Guarapuava", "ufSigla": "PR", "ufNome": "Paraná"},
                "orgaoSubRogado": None, "unidadeSubRogada": None, "usuarioNome": "Sistema simulado",
                "linkSistemaOrigem": "", "justificativaPresencial": None,
            }
            compras.append(registro)
            if situacao == 1 and (homologado or mod in (8, 9)):
                tipo, doc, nome = FORNECEDORES[0] if mod == 8 and d.month in (3, 4, 5) else rnd.choice(FORNECEDORES)
                valor = homologado or estimado
                seq[(cnpj, "c", d.year)] += 1
                assinatura = d + dt.timedelta(days=rnd.randint(5, 25))
                contratos.append({
                    "numeroControlePNCP": f"{cnpj}-2-{seq[(cnpj, 'c', d.year)]:06d}/{d.year}",
                    "numeroControlePncpCompra": registro["numeroControlePNCP"],
                    "numeroContratoEmpenho": f"{seq[(cnpj, 'c', d.year)]}/{d.year}", "anoContrato": d.year,
                    "sequencialContrato": seq[(cnpj, "c", d.year)], "processo": registro["processo"],
                    "tipoContrato": {"id": 1 if mod != 8 else 7, "nome": "Contrato (termo inicial)" if mod != 8 else "Empenho"},
                    "categoriaProcesso": {"id": 2, "nome": "Compras"}, "receita": False,
                    "objetoContrato": registro["objetoCompra"], "informacaoComplementar": None,
                    "orgaoEntidade": registro["orgaoEntidade"], "unidadeOrgao": registro["unidadeOrgao"],
                    "orgaoSubRogado": None, "unidadeSubRogada": None,
                    "tipoPessoa": tipo, "niFornecedor": doc, "nomeRazaoSocialFornecedor": nome,
                    "tipoPessoaSubContratada": None, "niFornecedorSubContratado": None, "nomeFornecedorSubContratado": None,
                    "valorInicial": valor, "numeroParcelas": 1, "valorParcela": valor, "valorGlobal": valor,
                    "valorAcumulado": valor, "dataAssinatura": assinatura.isoformat(),
                    "dataVigenciaInicio": assinatura.isoformat(),
                    "dataVigenciaFim": (assinatura + dt.timedelta(days=365)).isoformat(), "numeroRetificacao": 0,
                    "usuarioNome": "Sistema simulado",
                    "dataPublicacaoPncp": (dt.datetime.combine(assinatura, dt.time(10)) + dt.timedelta(days=2)).isoformat(),
                    "dataAtualizacao": None, "identificadorCipi": None, "urlCipi": None,
                })
        d += dt.timedelta(days=1)
    _dados_pncp.cache = (compras, contratos)
    return _dados_pncp.cache


def responder_pncp(caminho: str, q: dict, limite_dias: int | None, recusar: set[int] = frozenset()):
    """Devolve (status, corpo) para as consultas do PNCP simulado."""
    if int(q.get("codigoModalidadeContratacao", 0)) in recusar:
        return 400, {"message": "Modalidade inválida"}
    ini = dt.datetime.strptime(q["dataInicial"], "%Y%m%d").date()
    fim = dt.datetime.strptime(q["dataFinal"], "%Y%m%d").date()
    if limite_dias is not None and (fim - ini).days > limite_dias:
        return 422, {"message": f"Período maior que {limite_dias} dias"}
    compras, contratos = _dados_pncp()
    if caminho.endswith("contratacoes/publicacao"):
        dados = [c for c in compras if c["modalidadeId"] == int(q["codigoModalidadeContratacao"])
                 and c["unidadeOrgao"]["codigoIbge"] == q.get("codigoMunicipioIbge", c["unidadeOrgao"]["codigoIbge"])
                 and ini <= dt.date.fromisoformat(c["dataPublicacaoPncp"][:10]) <= fim]
    elif caminho.endswith("v1/contratos"):
        dados = [c for c in contratos if c["orgaoEntidade"]["cnpj"] == q.get("cnpjOrgao")
                 and ini <= dt.date.fromisoformat(c["dataPublicacaoPncp"][:10]) <= fim]
    else:
        return 404, {}
    if not dados:
        return 204, None
    tamanho = int(q.get("tamanhoPagina", 50))
    pagina = int(q["pagina"])
    total_paginas = -(-len(dados) // tamanho)
    return 200, {"data": dados[(pagina - 1) * tamanho: pagina * tamanho], "totalRegistros": len(dados),
                 "totalPaginas": total_paginas, "numeroPagina": pagina,
                 "paginasRestantes": max(0, total_paginas - pagina), "empty": False}


class _Handler(BaseHTTPRequestHandler):
    contador: Counter = Counter()
    falhar_uma_vez: set[str] = set()
    falhar_sempre: set[str] = set()       # "endpoint:id_ente" que sempre devolvem HTTP 500
    municipios_limite: int | None = None  # quantos municípios do PR o endpoint `entes` devolve
    limite_dias_pncp: int | None = None   # simula a API do PNCP recusando períodos longos
    recusar_modalidades: set[int] = set()  # simula a API do PNCP recusando uma modalidade (HTTP 400)

    def log_message(self, *args):  # silencia o log padrão
        pass

    def _json(self, status: int, corpo) -> None:
        dados = b"" if corpo is None else json.dumps(corpo).encode()
        self.send_response(status)
        if corpo is not None:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        if dados:
            self.wfile.write(dados)

    def do_GET(self):
        url = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        endpoint = url.path.strip("/").split("/")[-1]
        _Handler.contador[endpoint] += 1
        chave = f"{endpoint}:{url.query}"
        if chave in _Handler.falhar_uma_vez:
            _Handler.falhar_uma_vez.discard(chave)
            self.send_response(503)
            self.end_headers()
            return
        if f"{endpoint}:{q.get('id_ente', '')}" in _Handler.falhar_sempre:
            self.send_response(500)
            self.end_headers()
            return
        if url.path.startswith("/api/consulta/"):
            status, corpo = responder_pncp(url.path, q, _Handler.limite_dias_pncp, _Handler.recusar_modalidades)
            self._json(status, corpo)
            return
        if endpoint == "entes":
            from tests.fixtures_api import ENTES

            pr = municipios_pr()[: _Handler.municipios_limite] if _Handler.municipios_limite else municipios_pr()
            if ID_PRINCIPAL not in {c for c, _, _ in pr}:
                pr = [m for m in municipios_pr() if m[0] == ID_PRINCIPAL] + pr
            itens = [e for e in ENTES if e["uf"] != "PR"] + [
                {"cod_ibge": int(c), "ente": n, "capital": "1 " if c == "4106902" else "0 ", "regiao": "S", "uf": "PR",
                 "esfera": "M", "exercicio": 2026, "populacao": pop, "cnpj": ""} for c, n, pop in pr]
            itens.append({"cod_ibge": 41, "ente": "Paraná", "capital": "0 ", "regiao": "S", "uf": "PR", "esfera": "E",
                          "exercicio": 2026, "populacao": 11800000, "cnpj": "76416940000128"})
        elif endpoint == "extrato_entregas":
            itens = gerar_extrato(q["id_ente"], int(q["an_referencia"]))
        elif endpoint == "dca":
            itens = gerar_dca(q["id_ente"], int(q["an_exercicio"]), q.get("no_anexo", ""))
        elif endpoint == "msc_orcamentaria":
            itens = gerar_msc(int(q["an_referencia"]), int(q["me_referencia"]), int(q["classe_conta"]), q["id_ente"])
        elif endpoint == "rreo":
            anexo, ano, per = q.get("no_anexo", ""), int(q["an_exercicio"]), int(q["nr_periodo"])
            if q.get("co_esfera") != "M":
                itens = []
            elif q["id_ente"] != ID_PRINCIPAL:
                itens = gerar_rreo14_municipio(q["id_ente"], ano, q.get("co_tipo_demonstrativo", "")) \
                    if anexo == "RREO-Anexo 14" and per == 6 else []
            elif q.get("co_tipo_demonstrativo") != "RREO":
                itens = []
            elif anexo == "RREO-Anexo 03":
                itens = gerar_rreo03(ano, per, q["id_ente"])
            else:
                itens = gerar_rreo(ano, per, q["id_ente"], anexo)
        elif endpoint == "rgf":
            if q.get("co_esfera") != "M":
                itens = []
            elif q["id_ente"] != ID_PRINCIPAL:
                itens = gerar_rgf_municipio(q["id_ente"], int(q["an_exercicio"]), int(q["nr_periodo"]),
                                            q.get("in_periodicidade", ""), q.get("co_tipo_demonstrativo", "")) \
                    if q.get("no_anexo") == "RGF-Anexo 01" and q.get("co_poder") == "E" else []
            elif q.get("in_periodicidade") != "Q":
                itens = []
            else:
                itens = gerar_rgf(int(q["an_exercicio"]), int(q["nr_periodo"]), q["id_ente"], q.get("no_anexo", ""),
                                  q.get("co_poder", ""))
        else:
            self.send_response(404)
            self.end_headers()
            return
        offset = int(q.get("offset", 0))
        pagina = itens[offset: offset + TAMANHO_PAGINA]
        corpo = json.dumps({
            "items": pagina, "hasMore": offset + TAMANHO_PAGINA < len(itens), "limit": TAMANHO_PAGINA,
            "offset": offset, "count": len(pagina), "links": [{"rel": "self", "href": self.path}],
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)


def url_pncp(url_siconfi: str) -> str:
    """URL do PNCP simulado no mesmo servidor do SICONFI simulado."""
    return url_siconfi.replace("/ords/siconfi/tt/", "/api/consulta/")


@contextlib.contextmanager
def servidor(porta: int = 0, falhar_uma_vez: set[str] | None = None, falhar_sempre: set[str] | None = None,
             municipios: int | None = 8, limite_dias_pncp: int | None = None,
             recusar_modalidades: set[int] | None = None):
    """Sobe as APIs simuladas numa thread. Devolve (url_base_siconfi, contador_de_requisicoes).

    `municipios`: quantos municípios do PR o comparativo enxerga (None = os 399).
    """
    _Handler.contador = Counter()
    _Handler.falhar_uma_vez = set(falhar_uma_vez or ())
    _Handler.falhar_sempre = set(falhar_sempre or ())
    _Handler.municipios_limite = municipios
    _Handler.limite_dias_pncp = limite_dias_pncp
    _Handler.recusar_modalidades = set(recusar_modalidades or ())
    srv = ThreadingHTTPServer(("127.0.0.1", porta), _Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}/ords/siconfi/tt/", _Handler.contador
    finally:
        srv.shutdown()
        srv.server_close()


if __name__ == "__main__":
    with servidor(8765, municipios=None) as (url, _):
        print(f"SICONFI simulado em {url}\nPNCP simulado em {url_pncp(url)} (Ctrl+C para sair)")
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
