"""Indicadores fiscais a partir do RREO (Anexos 1, 3 e 14), do RGF (Anexos 1 e 2) e da DCA.

Os códigos `cod_conta` e os nomes de coluna usados aqui foram conferidos na API em
30/10/2026 (Guarapuava: RREO 4º bim/2026 e 6º bim/2021; RGF 2º quadr/2026 e 3º quadr/2021) e em
12/11/2026 (Guarapuava: RREO Anexo 3 4º bim/2026 e 6º bim/2019, DCA 2025; Abatiá: RREO e RGF
simplificados e DCA 2025). Quando um código não aparece, o indicador fica em branco – nada é estimado.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable


def normalizar(texto: object) -> str:
    """Minúsculas, sem acento, º -> o, espaços simples."""
    sem_acento = "".join(c for c in unicodedata.normalize("NFKD", str(texto)) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sem_acento.lower()).strip()


def _padrao(itens: Iterable[dict]) -> list[dict]:
    itens = list(itens)
    padrao = [i for i in itens if i.get("rotulo") == "Padrão"]
    return padrao or itens


def _primeiro(itens: list[dict], prefixo: str, coluna: str) -> float | None:
    regex = re.compile(coluna)
    for item in itens:
        if str(item.get("cod_conta", "")).startswith(prefixo) and regex.search(normalizar(item.get("coluna", ""))):
            try:
                return round(float(item["valor"]), 2)
            except (TypeError, ValueError, KeyError):
                return None
    return None


# ---------------------------------------------------------------- RREO Anexo 14
_ATE_BIM = r"^ate o bimestre"
REGRAS_RREO14 = [
    ("receita_prevista_inicial", "PrevisaoInicialDemonstrativoSimplificado", _ATE_BIM),
    ("receita_prevista_atualizada", "PrevisaoAtualizadaDemonstrativoSimplificado", _ATE_BIM),
    ("receita_realizada", "ReceitasRealizadasDemonstrativoSimplificado", _ATE_BIM),
    ("despesa_dotacao_inicial", "DotacaoInicialDemonstrativoSimplificado", _ATE_BIM),
    ("despesa_dotacao_atualizada", "DotacaoAtualizadaDemonstrativoSimplificado", _ATE_BIM),
    ("despesa_empenhada", "DespesasEmpenhadasDemonstrativoSimplificadoBalancoOrcamentario", _ATE_BIM),
    ("despesa_liquidada", "DespesasLiquidadasDemonstrativoSimplificadoBalancoOrcamentario", _ATE_BIM),
    ("despesa_paga", "DespesasPagasDemonstrativoSimplificado", _ATE_BIM),
    ("rcl", "ReceitaCorrenteLiquidaDemonstrativoSimplificado", _ATE_BIM),
    ("rpps_receitas", "ReceitasPrevidenciariasRealizadas", _ATE_BIM),
    ("rpps_despesas", "DespesasPrevidenciariasLiquidadas", _ATE_BIM),
    ("rpps_resultado", "ResultadoPrevidenciario", _ATE_BIM),
    ("primario_meta", "ResultadoPrimario", r"^meta"),
    ("primario_apurado", "ResultadoPrimario", r"^resultado apurado"),
    ("nominal_meta", "ResultadoNominal", r"^meta"),
    ("nominal_apurado", "ResultadoNominal", r"^resultado apurado"),
    ("restos_a_pagar_saldo", "TotalRestosAPagar", r"^saldo a pagar"),
    ("educacao_pct", "MinimoAnualDasReceitasDeImpostosNaManutencaoEDesenvolvimentoDoEnsino", r"^% aplicado"),
    ("educacao_minimo_pct", "MinimoAnualDasReceitasDeImpostosNaManutencaoEDesenvolvimentoDoEnsino", r"^% minimo"),
    ("fundeb_pct", "MinimoAnualDoFUNDEB", r"^% aplicado"),
    ("fundeb_minimo_pct", "MinimoAnualDoFUNDEB", r"^% minimo"),
    ("saude_pct", "AplicacaoTotalDasDespesasComAcoesEServicosPublicosDeSaude", r"^% aplicado"),
    ("saude_minimo_pct", "AplicacaoTotalDasDespesasComAcoesEServicosPublicosDeSaude", r"^% minimo"),
]


def extrair_rreo14(itens: Iterable[dict]) -> dict[str, float]:
    """Demonstrativo simplificado do RREO: orçamento, RCL, previdência, metas, educação e saúde."""
    itens = _padrao(itens)
    valores = {chave: v for chave, prefixo, coluna in REGRAS_RREO14
               if (v := _primeiro(itens, prefixo, coluna)) is not None}
    superavit = _primeiro(itens, "SuperavitOrcamentario", _ATE_BIM)
    deficit = _primeiro(itens, "DeficitOrcamentario", _ATE_BIM)
    if superavit is not None:
        valores["resultado_orcamentario"] = superavit
    elif deficit is not None:
        valores["resultado_orcamentario"] = -abs(deficit)
    elif {"receita_realizada", "despesa_liquidada"} <= valores.keys():
        # Mesma conta do relatório (receita realizada - despesa liquidada), conferida em 2021 e 2026.
        valores["resultado_orcamentario"] = round(valores["receita_realizada"] - valores["despesa_liquidada"], 2)
    return valores


# ---------------------------------------------------------------- RREO Anexo 1
ORIGENS_RECEITA = {
    # chave: (cod_conta, nome exibido no portal)
    "tributaria": ("ReceitaTributaria", "Impostos, taxas e contribuição de melhoria"),
    "uniao": ("TransferenciasCorrentesDaUniaoEDeSuasEntidades", "Transferências da União"),
    "estado": ("TransferenciasCorrentesDosEstadosEDoDistritoFederalEDeSuasEntidades", "Transferências do Estado"),
    "outras_publicas": ("TransferenciasCorrentesDeOutrasInstituicoesPublicas", "Transferências de outras instituições públicas (inclui o FUNDEB)"),
    "contribuicoes": ("ReceitaDeContribuicoes", "Contribuições (inclui a de iluminação pública)"),
    "patrimonial": ("ReceitaPatrimonial", "Rendimentos e patrimônio"),
    "capital": ("ReceitasDeCapital", "Receitas de capital (empréstimos, convênios, venda de bens)"),
    "correntes": ("ReceitasCorrentes", "Receitas correntes"),
    "total": ("ReceitasExcetoIntraOrcamentarias", "Total (sem receitas intraorçamentárias)"),
}


def extrair_rreo01_receitas(itens: Iterable[dict]) -> dict[str, float]:
    """Receita prevista (atualizada) e arrecadada até o bimestre, por origem."""
    itens = _padrao(itens)
    valores = {}
    for chave, (codigo, _) in ORIGENS_RECEITA.items():
        exatos = [i for i in itens if i.get("cod_conta") == codigo]
        prevista = _primeiro(exatos, codigo, r"^previsao atualizada")
        realizada = _primeiro(exatos, codigo, _ATE_BIM)
        if prevista is not None:
            valores[f"receita_{chave}_prevista"] = prevista
        if realizada is not None:
            valores[f"receita_{chave}_realizada"] = realizada
    return valores


# ---------------------------------------------------------------- RREO Anexo 3
# Demonstrativo da Receita Corrente Líquida: arrecadação mês a mês dos últimos 12 meses,
# por imposto e transferência. chave: (cod_conta, nome exibido no portal, grupo)
RECEITAS_RCL = {
    "iptu": ("IPTULiquidoExcetoTransferenciasEFUNDEB", "IPTU", "Impostos municipais"),
    "iss": ("ISSLiquidoExcetoTransferenciasEFUNDEB", "ISS", "Impostos municipais"),
    "itbi": ("ITBILiquidoExcetoTransferenciasEFUNDEB", "ITBI", "Impostos municipais"),
    "irrf": ("IRRFLiquidoExcetoTransferenciasEFUNDEB", "Imposto de renda retido (IRRF)", "Impostos municipais"),
    "outros_tributos": ("OutrasReceitasTributarias", "Taxas e outros tributos", "Impostos municipais"),
    "fpm": ("RREO3CotaParteDoFPM", "FPM – Fundo de Participação dos Municípios", "Transferências"),
    "icms": ("RREO3CotaParteDoICMS", "Cota-parte do ICMS", "Transferências"),
    "ipva": ("RREO3CotaParteDoIPVA", "Cota-parte do IPVA", "Transferências"),
    "itr": ("RREO3CotaParteDoITR", "Cota-parte do ITR", "Transferências"),
    "lc61": ("RREO3TransferenciasDaLC611989", "IPI-exportação (LC 61/1989)", "Transferências"),
    "fundeb": ("RREO3TransferenciasDoFUNDEB", "FUNDEB", "Transferências"),
    "outras_transferencias": ("RREO3OutrasTransferenciasCorrentes", "Outras transferências correntes", "Transferências"),
    "contribuicoes": ("RREO3ReceitaDeContribuicoes", "Contribuições", "Outras receitas"),
    "rendimentos": ("RendimentosDeAplicacaoFinanceira", "Rendimentos de aplicações financeiras", "Outras receitas"),
    "outras_patrimoniais": ("OutrasReceitasPatrimoniais", "Outras receitas patrimoniais", "Outras receitas"),
    "agropecuaria": ("RREO3ReceitaAgropecuaria", "Receita agropecuária", "Outras receitas"),
    "servicos": ("RREO3ReceitaDeServicos", "Receita de serviços", "Outras receitas"),
    "outras_correntes": ("RREO3OutrasReceitasCorrentes", "Outras receitas correntes", "Outras receitas"),
    # totais e deduções (não entram na soma das linhas acima)
    "tributaria": ("ReceitaTributariaLiquidaExcetoTransferenciasEFUNDEB", "Impostos, taxas e contribuições de melhoria", "Total"),
    "transferencias": ("RREO3TransferenciasCorrentes", "Transferências correntes", "Total"),
    "correntes": ("ReceitasCorrentesLiquidasExcetoTransferenciasEFUNDEB", "Receitas correntes", "Total"),
    "deducao_fundeb": ("DeducaoDeReceitaParaFormacaoDoFUNDEB", "Dedução para formar o FUNDEB", "Total"),
    "deducoes": ("DeducoesDaReceitaCorrenteLiquida", "Deduções", "Total"),
    "rcl": ("RREO3ReceitaCorrenteLiquida", "Receita corrente líquida", "Total"),
}
_MR = re.compile(r"^<MR(?:-(\d{1,2}))?>$")


def mes_de_referencia(coluna: str, ano: int, ultimo_mes: int) -> str | None:
    """'<MR-2>' no período que termina em ago/2026 -> '2026-06'. Devolve None se não for coluna de mês."""
    m = _MR.match(str(coluna).strip())
    if not m:
        return None
    deslocamento = int(m.group(1) or 0)
    indice = ano * 12 + (ultimo_mes - 1) - deslocamento
    return f"{indice // 12}-{indice % 12 + 1:02d}"


def extrair_rreo03(itens: Iterable[dict], ano: int, ultimo_mes: int) -> list[dict]:
    """Linhas (chave, referencia, valor): referencia = 'AAAA-MM' (mês), '12m' (total) ou 'previsao' (ano)."""
    itens = _padrao(itens)
    por_codigo = {codigo: chave for chave, (codigo, _, _) in RECEITAS_RCL.items()}
    linhas, vistos = [], set()
    for item in itens:
        chave = por_codigo.get(str(item.get("cod_conta", "")))
        if chave is None:
            continue
        coluna = str(item.get("coluna", ""))
        col = normalizar(coluna)
        if col.startswith("total"):
            referencia = "12m"
        elif col.startswith("previsao atualizada"):
            referencia = "previsao"
        else:
            referencia = mes_de_referencia(coluna, ano, ultimo_mes)
        if referencia is None or (chave, referencia) in vistos:
            continue
        try:
            valor = round(float(item["valor"]), 2)
        except (TypeError, ValueError, KeyError):
            continue
        vistos.add((chave, referencia))
        linhas.append({"chave": chave, "referencia": referencia, "valor": valor})
    return linhas


# ----------------------------------------------------------------- DCA (balanço anual)
def extrair_dca_funcoes(itens: Iterable[dict]) -> dict[str, float]:
    """DCA Anexo I-E: despesa liquidada no ano por função ('12 - Educação' -> funcao_12), sem intraorçamentárias.

    O anexo traz primeiro o bloco "Despesas Exceto Intraorçamentárias" e depois o bloco
    "Despesas Intraorçamentárias", com as mesmas funções; só o primeiro bloco entra.
    """
    liquidadas = [i for i in itens if normalizar(i.get("coluna", "")) == "despesas liquidadas"]
    valores: dict[str, float] = {}
    for item in liquidadas:
        conta = str(item.get("conta", "")).strip()
        nconta = normalizar(conta)
        try:
            valor = round(float(item["valor"]), 2)
        except (TypeError, ValueError, KeyError):
            continue
        if nconta.startswith("despesas intraorcamentarias"):
            if any(k.startswith("funcao_") for k in valores):
                break  # começou o bloco intraorçamentário
            continue
        if nconta.startswith("despesas exceto intra"):
            valores.setdefault("despesa_total", valor)
            continue
        m = re.match(r"^(\d{2}) - ", conta)
        if m:
            valores.setdefault(f"funcao_{m.group(1)}", valor)
    return valores


def extrair_dca_natureza(itens: Iterable[dict]) -> dict[str, float]:
    """DCA Anexo I-D: despesa liquidada no ano com pessoal (3.1), investimentos (4.4) e total."""
    regras = {"pessoal_encargos": "DO3.1.00.00.00.00", "investimentos": "DO4.4.00.00.00.00",
              "despesa_total_natureza": "TotalDespesas"}
    valores: dict[str, float] = {}
    for item in itens:
        if normalizar(item.get("coluna", "")) != "despesas liquidadas":
            continue
        for chave, codigo in regras.items():
            if item.get("cod_conta") == codigo and chave not in valores:
                try:
                    valores[chave] = round(float(item["valor"]), 2)
                except (TypeError, ValueError, KeyError):
                    pass
    return valores


def resumir_extrato(itens: Iterable[dict]) -> dict:
    """Extrato de entregas do ano: que relatório a prefeitura entregou, em que periodicidade.

    Municípios com menos de 50 mil habitantes podem entregar o RREO e o RGF simplificados
    (o RGF passa a ser semestral). O extrato diz qual consulta fazer em cada caso.
    """
    info = {"populacao": None, "rreo_tipo": None, "rreo_ultimo": 0, "rgf_tipo": None,
            "rgf_periodicidade": None, "rgf_ultimo": 0, "dca": False}
    for item in itens:
        if info["populacao"] is None and item.get("populacao"):
            info["populacao"] = int(item["populacao"])
        entregavel = normalizar(item.get("entregavel", ""))
        instituicao = normalizar(item.get("instituicao", ""))
        try:
            periodo = int(item.get("periodo") or 0)
        except (TypeError, ValueError):
            periodo = 0
        if "camara" in instituicao:
            continue  # o comparativo usa os relatórios do Executivo (prefeitura)
        if entregavel.startswith("relatorio resumido"):
            if periodo >= info["rreo_ultimo"]:
                info["rreo_ultimo"] = periodo
                info["rreo_tipo"] = "RREO Simplificado" if "simplificado" in entregavel else "RREO"
        elif entregavel.startswith("relatorio de gestao fiscal"):
            periodicidade = str(item.get("periodicidade") or "").strip().upper() or "Q"
            if periodo >= info["rgf_ultimo"]:
                info["rgf_ultimo"] = periodo
                info["rgf_tipo"] = "RGF Simplificado" if "simplificado" in entregavel else "RGF"
                info["rgf_periodicidade"] = periodicidade
        elif "dca" in entregavel or entregavel.startswith("balanco anual"):
            info["dca"] = True
    if info["rgf_periodicidade"]:
        info["rgf_final"] = 2 if info["rgf_periodicidade"] == "S" else 3
    return info


# ----------------------------------------------------------------- RGF Anexo 1
def extrair_rgf_pessoal(itens: Iterable[dict]) -> dict[str, float]:
    """Despesa com pessoal e seus limites (% da RCL ajustada) de um poder."""
    itens = _padrao(itens)
    pct = r"^% sobre a rcl"
    regras = [
        ("pessoal_valor", "DespesaComPessoalTotal", r"^valor$"),
        ("pessoal_pct", "DespesaComPessoalTotal", pct),
        ("pessoal_limite_maximo_pct", "LimiteMaximoDespesaComPessoalTotal", pct),
        ("pessoal_limite_prudencial_pct", "LimitePrudencialDespesaComPessoalTotal", pct),
        ("pessoal_limite_alerta_pct", "LimiteDeAlertaDespesaComPessoalTotal", pct),
    ]
    return {chave: v for chave, prefixo, coluna in regras if (v := _primeiro(itens, prefixo, coluna)) is not None}


# ----------------------------------------------------------------- RGF Anexo 2
def extrair_rgf_divida(itens: Iterable[dict], quadrimestre: int) -> dict[str, float]:
    """Dívida consolidada (bruta e líquida) no fim do quadrimestre e o limite do Senado."""
    itens = _padrao(itens)
    coluna = rf"^ate o {quadrimestre}"
    regras = [
        ("divida_consolidada", "DividaConsolidada", coluna),
        ("divida_liquida", "DividaConsolidadaLiquida", coluna),
        ("divida_consolidada_pct", "PercentualDaDCSobreARCL", coluna),
        ("divida_liquida_pct", "PercentualDaDCLSobreARCL", coluna),
        ("divida_limite_senado", "LimiteDefinidoPorResolucaoDoSenadoFederal", coluna),
    ]
    valores = {}
    for chave, codigo, col in regras:
        exatos = [i for i in itens if i.get("cod_conta") == codigo]
        v = _primeiro(exatos, codigo, col)
        if v is not None:
            valores[chave] = v
    return valores


# ------------------------------------------------------- classificação (semáforo)
# nível -> usado pelo portal para escolher ícone e cor; o rótulo sempre acompanha a cor.
def status_limite(valor: float | None, alerta: float | None, prudencial: float | None,
                  maximo: float | None) -> tuple[str, str]:
    """Limite máximo da LRF (pessoal): alerta = 90% do máximo, prudencial = 95%."""
    if valor is None or maximo is None:
        return "sem_dado", "Sem dado"
    if valor > maximo:
        return "critico", "Acima do limite máximo"
    if prudencial is not None and valor > prudencial:
        return "grave", "Acima do limite prudencial"
    if alerta is not None and valor > alerta:
        return "alerta", "Acima do limite de alerta"
    return "ok", "Dentro do limite"


def status_minimo(valor: float | None, minimo: float | None, ano_fechado: bool) -> tuple[str, str]:
    """Mínimos constitucionais (educação 25%, FUNDEB 70%, saúde 15%): a apuração vale para o ano."""
    if valor is None or minimo is None:
        return "sem_dado", "Sem dado"
    if valor >= minimo:
        return "ok", "Acima do mínimo"
    if ano_fechado:
        return "critico", "Abaixo do mínimo no ano"
    return "alerta", "Abaixo do mínimo até agora"


def status_meta(apurado: float | None, meta: float | None, ano_fechado: bool) -> tuple[str, str]:
    """Meta de resultado primário da LDO: só dá para julgar com o ano fechado."""
    if apurado is None:
        return "sem_dado", "Sem dado"
    if meta is None:
        return "info", "Meta não informada no relatório"
    if not ano_fechado:
        return "info", "Em apuração (meta é anual)"
    return ("ok", "Meta cumprida") if apurado >= meta else ("alerta", "Meta não cumprida")


def status_divida(divida_liquida_pct: float | None, limite_pct: float = 120.0) -> tuple[str, str]:
    """Dívida consolidada líquida: limite de 120% da RCL (Senado); alerta a 90% dele (LRF, art. 59)."""
    if divida_liquida_pct is None:
        return "sem_dado", "Sem dado"
    if divida_liquida_pct > limite_pct:
        return "critico", "Acima do limite"
    if divida_liquida_pct > 0.9 * limite_pct:
        return "alerta", "Acima do limite de alerta"
    return "ok", "Dentro do limite"
