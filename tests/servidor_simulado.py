"""API do SICONFI simulada, para testar o coletor sem acesso à internet.

Reproduz o formato real das respostas (campos, tipos e paginação por hasMore/offset,
conferidos em 30/10/2026). OS VALORES SÃO FICTÍCIOS – servem só para testes e para
demonstrar o portal. Uso manual:

    python -m tests.servidor_simulado            # sobe em http://127.0.0.1:8765/
    python coletar.py --url http://127.0.0.1:8765/ --anos 2025 2026 --pausa 0 --pasta data_demo
"""

from __future__ import annotations

import contextlib
import datetime as dt
import json
import threading
from collections import Counter
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
            "populacao": 0, "anexo": anexo, "esfera": "M", "rotulo": "Padrão", **extra}


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


class _Handler(BaseHTTPRequestHandler):
    contador: Counter = Counter()
    falhar_uma_vez: set[str] = set()

    def log_message(self, *args):  # silencia o log padrão
        pass

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
        if endpoint == "msc_orcamentaria":
            itens = gerar_msc(int(q["an_referencia"]), int(q["me_referencia"]), int(q["classe_conta"]), q["id_ente"])
        elif endpoint == "rreo":
            if q.get("co_esfera") != "M":
                itens = []
            else:
                itens = gerar_rreo(int(q["an_exercicio"]), int(q["nr_periodo"]), q["id_ente"], q.get("no_anexo", ""))
        elif endpoint == "rgf":
            if q.get("co_esfera") != "M" or q.get("in_periodicidade") != "Q":
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


@contextlib.contextmanager
def servidor(porta: int = 0, falhar_uma_vez: set[str] | None = None):
    """Sobe a API simulada numa thread. Devolve (url_base, contador_de_requisicoes)."""
    _Handler.contador = Counter()
    _Handler.falhar_uma_vez = set(falhar_uma_vez or ())
    srv = ThreadingHTTPServer(("127.0.0.1", porta), _Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}/ords/siconfi/tt/", _Handler.contador
    finally:
        srv.shutdown()
        srv.server_close()


if __name__ == "__main__":
    with servidor(8765) as (url, _):
        print(f"API simulada em {url} (Ctrl+C para sair)")
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
