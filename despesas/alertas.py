"""Pontos de atenção: números que merecem acompanhamento, com regras explícitas e conferíveis.

Um ponto de atenção NÃO é indício de irregularidade. É um resultado que passa de um limite legal,
foge do padrão ou que a lei manda observar com cuidado – e por isso vale a pena conferir na fonte.
Cada regra abaixo está descrita na página "Sobre os dados".
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .formatacao import brl_compacto, contagem, numero, pct
from .indicadores import normalizar, status_divida, status_limite, status_meta, status_minimo
from .pncp import CONTRATACAO_DIRETA, LICITACOES

# nível -> ordem de exibição (mais grave primeiro)
ORDEM = {"critico": 0, "grave": 1, "alerta": 2, "info": 3, "incompleto": 4}

# ------------------------------------------------------------------ regras (compras)
PRAZO_MINIMO_DIAS_UTEIS = 8        # Lei 14.133/2021, art. 55, I, a: menor prazo para propostas (bens, menor preço)
DESCONTO_MINIMO = 0.01             # homologado a menos de 1% do estimado
MIN_DISPENSAS_MESMO_FORNECEDOR = 3 # contratos de dispensa por valor com o mesmo fornecedor no ano
AMPARO_EMERGENCIA = {38}           # Lei 14.133/2021, art. 75, VIII (emergência ou calamidade)
AMPARO_DISPENSA_VALOR = {18, 19}   # Lei 14.133/2021, art. 75, I e II (dispensa por valor)
FRACAO_DO_ANO = 2 / 3              # receitas de capital e investimentos: avaliados depois de 2/3 do ano
EXECUCAO_BAIXA = 0.25


@dataclass
class Ponto:
    nivel: str
    area: str
    titulo: str
    detalhe: str
    pagina: str | None = None
    quantidade: int | None = None
    regra: str = ""
    chave: str = ""


def ordenar(pontos: list[Ponto]) -> list[Ponto]:
    return sorted(pontos, key=lambda p: ORDEM.get(p.nivel, 9))


def _pp(v: float | None, casas: int = 2) -> str:
    return "–" if v is None else f"{numero(v, casas)}%"


# ------------------------------------------------------------------ contas públicas
def pontos_fiscais(r: dict, e: dict | None, leg: dict | None, fechado: bool, ate_rreo: str, ate_rgf: str,
                   mes_rreo: int, ano: int, investimentos: tuple[float, float] | None = None) -> list[Ponto]:
    """`r`, `e` e `leg`: indicadores do RREO e do RGF (Executivo e Legislativo) como dicionários."""
    g = lambda d, k: None if not d or d.get(k) is None or pd.isna(d.get(k)) else float(d[k])  # noqa: E731
    pontos: list[Ponto] = []

    for linha, quem in ((e, "da Prefeitura"), (leg, "da Câmara")):
        v = g(linha, "pessoal_pct")
        al, pr, mx = (g(linha, c) for c in ("pessoal_limite_alerta_pct", "pessoal_limite_prudencial_pct",
                                            "pessoal_limite_maximo_pct"))
        nivel, rotulo = status_limite(v, al, pr, mx)
        if nivel in ("alerta", "grave", "critico"):
            consequencia = {
                "alerta": "Passado o limite de alerta, o Tribunal de Contas avisa o município (LRF, art. 59).",
                "grave": "Acima do limite prudencial, a LRF (art. 22) proíbe, com exceções, reajustes e novas contratações.",
                "critico": "Acima do limite máximo, o excesso precisa ser eliminado nos dois quadrimestres seguintes (LRF, art. 23).",
            }[nivel]
            pontos.append(Ponto(nivel, "Contas públicas", f"Gasto com pessoal {quem}: {rotulo.lower()}",
                                f"{_pp(v)} da receita corrente líquida ({ate_rgf}). Limites: alerta {_pp(al, 1)}, "
                                f"prudencial {_pp(pr, 1)}, máximo {_pp(mx, 1)}. {consequencia}",
                                regra="Limites da LRF para a despesa total com pessoal (RGF Anexo 1)."))

    dcl = g(e, "divida_liquida_pct")
    nivel, rotulo = status_divida(dcl)
    if nivel in ("alerta", "critico"):
        pontos.append(Ponto(nivel, "Contas públicas", f"Dívida consolidada líquida: {rotulo.lower()}",
                            f"{_pp(dcl)} da receita corrente líquida ({ate_rgf}); limite de 120%.",
                            regra="Resolução do Senado nº 40/2001 (RGF Anexo 2)."))

    nomes = {"educacao": ("Educação", 25), "fundeb": ("FUNDEB na remuneração dos profissionais", 70),
             "saude": ("Saúde", 15)}
    for chave, (nome, _) in nomes.items():
        v, minimo = g(r, f"{chave}_pct"), g(r, f"{chave}_minimo_pct")
        nivel, rotulo = status_minimo(v, minimo, fechado)
        if nivel == "critico":
            pontos.append(Ponto("critico", "Contas públicas", f"{nome}: abaixo do mínimo constitucional em {ano}",
                                f"Aplicado {_pp(v)}; mínimo {_pp(minimo, 0)}.", regra="RREO Anexo 14."))
        elif nivel == "alerta":
            pontos.append(Ponto("info", "Contas públicas", f"{nome}: abaixo do mínimo até agora",
                                f"Aplicado {_pp(v)} {ate_rreo}; o mínimo de {_pp(minimo, 0)} vale para o ano inteiro.",
                                regra="RREO Anexo 14 (apuração parcial)."))

    nivel, rotulo = status_meta(g(r, "primario_apurado"), g(r, "primario_meta"), fechado)
    if nivel == "alerta":
        pontos.append(Ponto("alerta", "Contas públicas", f"Meta de resultado primário não cumprida em {ano}",
                            f"Resultado {brl_compacto(g(r, 'primario_apurado'))}; meta da LDO "
                            f"{brl_compacto(g(r, 'primario_meta'))}.", regra="RREO Anexo 14."))

    resultado = g(r, "resultado_orcamentario")
    if fechado and resultado is not None and resultado < 0:
        pontos.append(Ponto("alerta", "Contas públicas", f"Déficit orçamentário em {ano}",
                            f"As despesas liquidadas superaram as receitas arrecadadas em {brl_compacto(-resultado)}. "
                            "Pode ter sido coberto com saldo de anos anteriores.", regra="RREO Anexo 14."))

    rpps = g(r, "rpps_resultado")
    if rpps is not None and rpps < 0:
        pontos.append(Ponto("info", "Contas públicas", "Previdência dos servidores com resultado negativo",
                            f"Despesas previdenciárias maiores que as receitas em {brl_compacto(-rpps)} ({ate_rreo}).",
                            regra="RREO Anexo 14."))

    passou = mes_rreo / 12 >= FRACAO_DO_ANO
    prev_cap, real_cap = g(r, "receita_capital_prevista"), g(r, "receita_capital_realizada")
    if passou and prev_cap and real_cap is not None and real_cap / prev_cap < EXECUCAO_BAIXA:
        pontos.append(Ponto("info", "Contas públicas", "Receitas de capital muito abaixo do previsto",
                            f"Arrecadados {brl_compacto(real_cap)} de {brl_compacto(prev_cap)} previstos "
                            f"({pct(real_cap / prev_cap)}) {ate_rreo}. São empréstimos, convênios e vendas de bens, "
                            "que costumam financiar obras.", pagina="paginas/receitas.py",
                            regra="RREO Anexo 1: menos de 25% do previsto com 2/3 do ano decorridos."))
    if passou and investimentos and investimentos[0]:
        dotacao, liquidado = investimentos
        if liquidado / dotacao < EXECUCAO_BAIXA:
            pontos.append(Ponto("info", "Contas públicas", "Investimentos com execução baixa",
                                f"Liquidados {brl_compacto(liquidado)} de {brl_compacto(dotacao)} autorizados "
                                f"({pct(liquidado / dotacao)}) {ate_rreo}.", pagina="paginas/despesa.py",
                                regra="MSC (grupo 4.4): menos de 25% do autorizado com 2/3 do ano decorridos."))
    return ordenar(pontos)


# ------------------------------------------------------------------ compras públicas
def datas(serie: pd.Series) -> pd.Series:
    """Datas ISO 8601 com ou sem hora ('2026-10-05' ou '2026-10-05T08:00:00'); vazio vira NaT.

    O formato é explícito: sem ele, o pandas deduz o formato pelo primeiro valor e descarta os demais.
    """
    texto = serie.astype("string").str.slice(0, 19).replace({"": pd.NA, "None": pd.NA, "nan": pd.NA})
    return pd.to_datetime(texto, format="ISO8601", errors="coerce")


def dias_uteis(inicio: pd.Series, fim: pd.Series) -> pd.Series:
    """Dias de segunda a sexta depois de `inicio` até `fim`, inclusive (feriados não são descontados)."""
    validos = inicio.notna() & fim.notna() & (fim >= inicio)
    saida = pd.Series(np.nan, index=inicio.index)
    if validos.any():
        um_dia = np.timedelta64(1, "D")
        a = inicio[validos].values.astype("datetime64[D]") + um_dia
        b = fim[validos].values.astype("datetime64[D]") + um_dia
        saida.loc[validos] = np.busday_count(a, b)
    return saida


def eh_emergencia(df: pd.DataFrame) -> pd.Series:
    codigo = df["amparo_codigo"].isin(AMPARO_EMERGENCIA).fillna(False).astype(bool)
    texto = df["amparo_nome"].map(normalizar).str.contains(r"art\.?\s*75,?\s*viii\b", regex=True, na=False)
    return codigo | texto


def eh_dispensa_por_valor(df: pd.DataFrame) -> pd.Series:
    codigo = df["amparo_codigo"].isin(AMPARO_DISPENSA_VALOR).fillna(False).astype(bool)
    texto = df["amparo_nome"].map(normalizar).str.contains(r"art\.?\s*75,?\s*(?:i|ii)$", regex=True, na=False)
    return codigo | texto


@dataclass
class AnaliseCompras:
    ano: int
    contratacoes: pd.DataFrame
    contratos: pd.DataFrame
    emergenciais: pd.DataFrame = field(default_factory=pd.DataFrame)
    prazo_curto: pd.DataFrame = field(default_factory=pd.DataFrame)
    sem_desconto: pd.DataFrame = field(default_factory=pd.DataFrame)
    recorrentes: pd.DataFrame = field(default_factory=pd.DataFrame)
    canceladas: pd.DataFrame = field(default_factory=pd.DataFrame)
    direta_valor: float = 0.0
    total_valor: float = 0.0
    direta_qtd: int = 0
    top5_participacao: float | None = None
    contratos_ligados: bool = False
    orgaos_pendentes: list[str] = field(default_factory=list)  # órgãos com contratos do ano ainda não coletados


def analisar_compras(contratacoes: pd.DataFrame, contratos: pd.DataFrame, ano: int,
                     orgaos_pendentes: list[str] = ()) -> AnaliseCompras:
    """Aplica as regras de atenção às compras publicadas no ano (data de publicação no PNCP).

    `orgaos_pendentes`: nomes dos órgãos cujos contratos do ano ainda não foram coletados. Enquanto houver algum,
    as regras que dependem de contratos (fornecedores) ficam suspensas, para não mostrar um retrato incompleto.
    """
    c = contratacoes.copy()
    c["publicacao"] = datas(c["data_publicacao"])
    c = c[c["publicacao"].dt.year == ano]
    k = contratos.copy()
    k["assinatura"] = datas(k["data_assinatura"]).fillna(datas(k["data_publicacao"]))
    k = k[(k["assinatura"].dt.year == ano) & ~k["receita"]]
    a = AnaliseCompras(ano=ano, contratacoes=c, contratos=k, orgaos_pendentes=list(orgaos_pendentes))
    if c.empty and k.empty:
        return a

    validas = c[~c["situacao_id"].isin([2, 3]).fillna(False).astype(bool)]  # sem revogadas e anuladas
    a.canceladas = c[c["situacao_id"].isin([2, 3]).fillna(False).astype(bool)]
    a.total_valor = float(validas["valor_estimado"].fillna(0).sum())
    diretas = validas[validas["modalidade_id"].isin(CONTRATACAO_DIRETA).fillna(False).astype(bool)]
    a.direta_valor = float(diretas["valor_estimado"].fillna(0).sum())
    a.direta_qtd = int(len(diretas))

    a.emergenciais = validas[eh_emergencia(validas)].sort_values("valor_estimado", ascending=False)

    lic = validas[validas["modalidade_id"].isin(LICITACOES).fillna(False).astype(bool)].copy()
    lic["dias_uteis"] = dias_uteis(lic["publicacao"], datas(lic["data_encerramento"]))
    a.prazo_curto = lic[lic["dias_uteis"] < PRAZO_MINIMO_DIAS_UTEIS].sort_values("dias_uteis")

    hom = lic[(lic["valor_estimado"] > 0) & (lic["valor_homologado"] > 0)].copy()
    hom["desconto"] = 1 - hom["valor_homologado"] / hom["valor_estimado"]
    a.sem_desconto = hom[hom["desconto"] < DESCONTO_MINIMO].sort_values("valor_homologado", ascending=False)

    # contratos de dispensa por valor com o mesmo fornecedor (só pessoa jurídica identificável)
    base = contratacoes[["id_pncp", "modalidade_id", "amparo_codigo", "amparo_nome"]].rename(columns={"id_pncp": "id_compra"})
    ligados = k[k["id_compra"].astype(str) != ""].merge(base, on="id_compra", how="inner")
    a.contratos_ligados = not ligados.empty
    if not ligados.empty:
        disp = ligados[(ligados["modalidade_id"] == 8).fillna(False).astype(bool) & eh_dispensa_por_valor(ligados)]
        disp = disp[disp["fornecedor_doc"] != ""]
        grupos = (disp.groupby(["fornecedor_doc", "fornecedor_nome"])
                  .agg(contratos=("id_pncp", "count"), valor=("valor_global", "sum"),
                       objetos=("objeto", lambda s: " | ".join(s.astype(str).str[:80].head(3))))
                  .reset_index())
        a.recorrentes = grupos[grupos["contratos"] >= MIN_DISPENSAS_MESMO_FORNECEDOR].sort_values("valor", ascending=False)

    pj = k[k["fornecedor_doc"] != ""]
    if len(pj) and pj["valor_global"].fillna(0).sum() > 0:
        por_fornecedor = pj.groupby("fornecedor_doc")["valor_global"].sum().sort_values(ascending=False)
        a.top5_participacao = float(por_fornecedor.head(5).sum() / k["valor_global"].fillna(0).sum())
    return a


def pontos_compras(a: AnaliseCompras) -> list[Ponto]:
    pontos: list[Ponto] = []
    pagina = "paginas/compras.py"
    if len(a.emergenciais):
        emergenciais = contagem(len(a.emergenciais), "contratação emergencial", "contratações emergenciais")
        pontos.append(Ponto("alerta", "Compras", f"{emergenciais} em {a.ano}",
                            f"Somam {brl_compacto(a.emergenciais['valor_estimado'].fillna(0).sum())} estimados. A dispensa por "
                            "emergência (art. 75, VIII, da Lei 14.133) exige justificativa e vale por até um ano.",
                            pagina, len(a.emergenciais), "Amparo legal: art. 75, VIII.", "emergencia"))
    if len(a.recorrentes) and not a.orgaos_pendentes:
        pontos.append(Ponto("alerta", "Compras",
                            f"{contagem(len(a.recorrentes), 'fornecedor', 'fornecedores')} com "
                            f"{MIN_DISPENSAS_MESMO_FORNECEDOR} ou mais dispensas por valor",
                            "Várias contratações diretas com a mesma empresa no ano podem ser legítimas, mas merecem "
                            "conferência: a lei proíbe dividir uma compra para caber no limite da dispensa (art. 75, § 1º).",
                            pagina, len(a.recorrentes), "Contratos ligados a dispensas do art. 75, I e II.",
                            "recorrentes"))
    if len(a.prazo_curto):
        pontos.append(Ponto("alerta", "Compras",
                            f"{contagem(len(a.prazo_curto), 'licitação', 'licitações')} com prazo curto para propostas",
                            f"Menos de {PRAZO_MINIMO_DIAS_UTEIS} dias úteis entre a publicação no PNCP e o fim das propostas, "
                            "o menor prazo da lei (art. 55). Prazo curto reduz a concorrência; confira o edital.",
                            pagina, len(a.prazo_curto), "Pregões e concorrências; feriados não descontados.",
                            "prazo"))
    if a.total_valor > 0:
        participacao = a.direta_valor / a.total_valor
        pontos.append(Ponto("info", "Compras", f"Contratação direta: {pct(participacao)} do valor estimado em {a.ano}",
                            f"{a.direta_qtd} dispensas e inexigibilidades, somando {brl_compacto(a.direta_valor)} de "
                            f"{brl_compacto(a.total_valor)}. São legais em casos previstos na lei, sem disputa entre empresas.",
                            pagina, a.direta_qtd, "Modalidades 8 (dispensa) e 9 (inexigibilidade).", "direta"))
    if len(a.sem_desconto):
        homologadas = contagem(len(a.sem_desconto), "licitação homologada", "licitações homologadas")
        pontos.append(Ponto("info", "Compras", f"{homologadas} sem desconto",
                            "O valor final ficou a menos de 1% do estimado, o que pode indicar pouca disputa.",
                            pagina, len(a.sem_desconto), "Homologado ≥ 99% do estimado.", "desconto"))
    if a.top5_participacao is not None and a.top5_participacao >= 0.5 and not a.orgaos_pendentes:
        pontos.append(Ponto("info", "Compras", f"Cinco fornecedores concentram {pct(a.top5_participacao)} dos contratos",
                            f"Participação dos 5 maiores no valor dos contratos assinados em {a.ano}.", pagina,
                            regra="Valor global dos contratos por CNPJ.", chave="concentracao"))
    if a.orgaos_pendentes:
        n = len(a.orgaos_pendentes)
        quais = ", ".join(a.orgaos_pendentes[:3]) + (f" e mais {n - 3}" if n > 3 else "")
        pontos.append(Ponto("incompleto", "Compras", f"Contratos de {a.ano} ainda em coleta",
                            f"Faltam os contratos de {n} {'órgão' if n == 1 else 'órgãos'} ({quais}). Os pontos sobre "
                            "fornecedores (várias dispensas com a mesma empresa e concentração) voltam quando a coleta "
                            "terminar, na próxima execução do robô.", pagina, chave="contratos_incompletos"))
    return ordenar(pontos)

