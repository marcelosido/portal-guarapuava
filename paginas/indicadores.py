"""Página inicial: pontos de atenção, orçamento previsto × realizado, limites da LRF e mínimos da Constituição.

Fonte: RREO (Anexos 1 e 14) e RGF (Anexos 1 e 2) publicados pelo município no SICONFI; compras no PNCP.
"""

from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from despesas import config
from despesas.alertas import analisar_compras, pontos_compras, pontos_fiscais
from despesas.dicionarios import NOMES_MES
from despesas.formatacao import brl, brl_compacto, numero, pct
from despesas.indicadores import status_divida, status_limite, status_meta, status_minimo
from despesas.painel import (AZUL, CINZA, assinatura, aviso_demonstracao, cabecalho, carregar_compras,
                             carregar_despesa, carregar_indicadores, coletado_em, estilo_grafico, ler_metadados,
                             lista_pontos, md, medidor, mostrar, pasta_dados, selo, sem_dados, seletor_ano, tabela)

PASTA = pasta_dados()
meta = ler_metadados(PASTA)
QUADRIMESTRES = {1: "jan–abr", 2: "mai–ago", 3: "set–dez"}

ind = carregar_indicadores(str(PASTA), assinatura(PASTA / "fIndicadores.csv"))
if ind.empty or not (ind["relatorio"] == "RREO").any():
    st.title("Visão geral")
    sem_dados()


def tabela_larga(df: pd.DataFrame, chaves: list[str]) -> pd.DataFrame:
    return df.pivot_table(index=chaves, columns="chave", values="valor", aggfunc="first")


rreo = tabela_larga(ind[ind["relatorio"] == "RREO"], ["ano", "periodo"])
rgf = tabela_larga(ind[ind["relatorio"] == "RGF"], ["ano", "periodo", "poder"]) if (ind["relatorio"] == "RGF").any() else None


def valor(linha: pd.Series | None, chave: str) -> float | None:
    if linha is None or chave not in linha.index:
        return None
    v = linha[chave]
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)


def pp(v: float | None, casas: int = 2) -> str:
    """Valor que já está em %: 51.07 -> '51,07%'."""
    return "–" if v is None else f"{numero(v, casas)}%"


# ---------------------------------------------------------------- filtro e período
anos = sorted(rreo.index.get_level_values("ano").unique().tolist(), reverse=True)
ano = cabecalho("Visão geral",
                "Como a prefeitura arrecada e gasta, segundo os relatórios oficiais que ela mesma envia ao "
                "Tesouro Nacional, e o que merece atenção.",
                seletor=lambda coluna: seletor_ano(coluna, anos, "Exercício"))

bim = int(max(p for a, p in rreo.index if a == ano))
r = rreo.loc[(ano, bim)]
mes_rreo = 2 * bim
fechado_rreo = bim == 6

quad, e, leg = None, None, None
if rgf is not None and ano in rgf.index.get_level_values("ano"):
    quad = int(max(p for a, p, _ in rgf.index if a == ano))
    e = rgf.loc[(ano, quad, "E")] if (ano, quad, "E") in rgf.index else None
    leg = rgf.loc[(ano, quad, "L")] if (ano, quad, "L") in rgf.index else None

ate_rreo = f"até {NOMES_MES[mes_rreo].lower()}/{ano}"
ate_rgf = f"até {NOMES_MES[4 * quad].lower()}/{ano}" if quad else "–"
st.caption(md(f"Fonte: Tesouro Nacional (SICONFI) · RREO {ate_rreo} · RGF {ate_rgf} · atualizado em "
              f"{coletado_em(meta)}"))
aviso_demonstracao(meta)

# ------------------------------------------------------------- pontos de atenção
arq_fato = PASTA / "fDespesa.parquet"
investimento = dotacao_investimento = None
if arq_fato.exists():
    fato, _ = carregar_despesa(str(PASTA), assinatura(arq_fato))
    inv = fato[(fato["ano"] == ano) & (fato["mes"] == mes_rreo) & (fato["natureza_despesa"].str[:2] == "44")]
    if len(inv):
        investimento = float(inv["liquidado"].sum())
        dotacao_investimento = float(inv["dotacao_atualizada"].sum())

pontos = pontos_fiscais(r.to_dict(), None if e is None else e.to_dict(), None if leg is None else leg.to_dict(),
                        fechado_rreo, ate_rreo, f"RGF {ate_rgf}", mes_rreo, ano,
                        investimentos=(dotacao_investimento, investimento) if dotacao_investimento else None)
contratacoes, contratos = carregar_compras(str(PASTA), assinatura(PASTA / "fContratacoes.csv"))
analise_compras = analisar_compras(contratacoes, contratos, ano) if len(contratacoes) else None
pontos_pncp = pontos_compras(analise_compras) if analise_compras is not None else None

with st.container(border=True):
    st.subheader("Pontos de atenção", anchor="pontos-de-atencao")
    st.caption("Números que passam de um limite da lei ou que merecem acompanhamento. Não são, por si só, "
               "irregularidades: são o ponto de partida para perguntar e conferir na fonte.")
    esq, dir_ = st.columns(2, gap="large")
    with esq:
        st.markdown("**Contas públicas**")
        lista_pontos(pontos, "Nenhum limite ultrapassado e nenhum mínimo descumprido nos relatórios.")
    with dir_:
        st.markdown(f"**Compras e contratos em {ano}**")
        if pontos_pncp is None:
            st.caption("Os dados de compras (PNCP) ainda não foram coletados.")
        elif analise_compras.contratacoes.empty and analise_compras.contratos.empty:
            st.caption(f"Nenhuma compra publicada no PNCP em {ano}. O portal acompanha as compras a partir de "
                       f"{config.PNCP_INICIO[:4]}.")
        else:
            lista_pontos([p_ for p_ in pontos_pncp if p_.nivel != "info"][:3] or pontos_pncp[:2],
                         "Nenhum ponto de atenção nas compras publicadas.")
            st.page_link("paginas/compras.py", label="Ver compras e contratos", icon=":material/arrow_forward:")
    st.page_link("paginas/sobre.py", label="Como cada ponto é calculado", icon=":material/info:")

# ------------------------------------------------------ previsto x realizado no ano
st.subheader(f"Previsto × realizado em {ano}")
st.caption(f"Acumulado {ate_rreo}. A linha pontilhada marca a parte do ano já decorrida: {mes_rreo} de 12 meses "
           f"({pct(mes_rreo / 12, 0)}).")

rec_prev, rec_real = valor(r, "receita_prevista_atualizada"), valor(r, "receita_realizada")
desp_aut, desp_liq = valor(r, "despesa_dotacao_atualizada"), valor(r, "despesa_liquidada")
linhas = [(nome, feito, total, verbo) for nome, feito, total, verbo in [
    ("Receita arrecadada", rec_real, rec_prev, "previstos"),
    ("Despesa liquidada", desp_liq, desp_aut, "autorizados"),
] if feito is not None and total]
if linhas:
    medidor([(f"{nome}: {pct(feito / total)}", f"{brl_compacto(feito)} de {brl_compacto(total)} {verbo}", total, feito)
             for nome, feito, total, verbo in linhas],
            "Previsto / autorizado", "Realizado", alt=f"Receita arrecadada e despesa liquidada em {ano}",
            percentual=True, marca=100 * mes_rreo / 12)

k = st.columns(4)
resultado = valor(r, "resultado_orcamentario")
k[0].metric("Superávit orçamentário" if (resultado or 0) >= 0 else "Déficit orçamentário",
            brl_compacto(abs(resultado)) if resultado is not None else "–", border=True,
            help="Receita arrecadada menos despesa liquidada no período (RREO, demonstrativo simplificado).")
k[1].metric("Receita corrente líquida", brl_compacto(valor(r, "rcl")), border=True,
            help="Receita dos últimos 12 meses, já descontados repasses obrigatórios. É a base dos limites da LRF.")
k[2].metric("Investimentos liquidados", brl_compacto(investimento) if investimento is not None else "–", border=True,
            help="Obras, equipamentos e material permanente (grupo 4.4 da despesa), pela Matriz de Saldos Contábeis.")
k[3].metric("Restos a pagar em aberto", brl_compacto(valor(r, "restos_a_pagar_saldo")), border=True,
            help="Despesas de anos anteriores que ainda não foram pagas.")

# ------------------------------------------------------------- limites e mínimos
st.subheader("Limites da LRF e mínimos da Constituição")
st.caption(f"Pessoal e dívida: RGF {ate_rgf}. Educação, saúde, meta e previdência: RREO {ate_rreo}.")


def cartao(coluna, titulo: str, texto_valor: str, status: tuple[str, str], explicacao: str, ajuda: str) -> None:
    with coluna.container(border=True):
        st.metric(titulo, texto_valor, help=ajuda)
        selo(*status)
        st.caption(md(explicacao))


def cartao_pessoal(coluna, titulo: str, linha: pd.Series | None, ajuda: str) -> None:
    v = valor(linha, "pessoal_pct")
    al, pr, mx = (valor(linha, c) for c in ("pessoal_limite_alerta_pct", "pessoal_limite_prudencial_pct",
                                            "pessoal_limite_maximo_pct"))
    cartao(coluna, titulo, f"{pp(v)} da RCL", status_limite(v, al, pr, mx),
           f"Alerta {pp(al, 1)} · prudencial {pp(pr, 1)} · máximo {pp(mx, 1)}", ajuda)


linha1 = st.columns(4)
cartao_pessoal(linha1[0], "Gasto com pessoal – Prefeitura", e,
               "Despesa total com pessoal do Executivo sobre a receita corrente líquida ajustada (LRF, art. 19 e 20).")
cartao_pessoal(linha1[1], "Gasto com pessoal – Câmara", leg,
               "Despesa total com pessoal do Legislativo sobre a receita corrente líquida ajustada (limite de 6%).")
dcl = valor(e, "divida_liquida_pct")
cartao(linha1[2], "Dívida consolidada líquida", f"{pp(dcl)} da RCL", status_divida(dcl),
       f"Limite 120% da RCL. Dívida bruta: {pp(valor(e, 'divida_consolidada_pct'))} da RCL.",
       "Dívida consolidada menos o dinheiro em caixa. Negativa quando o caixa é maior que a dívida.")
cartao(linha1[3], "Meta de resultado primário", brl_compacto(valor(r, "primario_apurado")),
       status_meta(valor(r, "primario_apurado"), valor(r, "primario_meta"), fechado_rreo),
       f"Meta do ano na LDO: {brl_compacto(valor(r, 'primario_meta'))}" if valor(r, "primario_meta") is not None
       else "Meta não informada neste relatório",
       "Receitas menos despesas, sem juros e sem a previdência. A meta é fixada na Lei de Diretrizes Orçamentárias.")

linha2 = st.columns(4)
for coluna, titulo, chave, ajuda in [
    (linha2[0], "Educação", "educacao", "Aplicação em manutenção e desenvolvimento do ensino sobre a receita de impostos."),
    (linha2[1], "FUNDEB nos salários", "fundeb", "Parte do FUNDEB paga aos profissionais da educação básica."),
    (linha2[2], "Saúde", "saude", "Aplicação em ações e serviços públicos de saúde sobre a receita de impostos."),
]:
    v, minimo = valor(r, f"{chave}_pct"), valor(r, f"{chave}_minimo_pct")
    apuracao = "apuração do ano" if fechado_rreo else f"apuração parcial, {ate_rreo}"
    cartao(coluna, titulo, pp(v), status_minimo(v, minimo, fechado_rreo), f"Mínimo {pp(minimo, 0)} · {apuracao}", ajuda)
rpps = valor(r, "rpps_resultado")
cartao(linha2[3], "Previdência dos servidores", brl_compacto(rpps),
       ("sem_dado", "Sem dado") if rpps is None else (("ok", "Receitas cobrem as despesas") if rpps >= 0
                                                      else ("alerta", "Despesas maiores que as receitas")),
       f"Receitas {brl_compacto(valor(r, 'rpps_receitas'))} · despesas {brl_compacto(valor(r, 'rpps_despesas'))}",
       "Resultado do regime próprio de previdência (RPPS) no período: receitas previdenciárias menos despesas.")

# ------------------------------------------------------------------------- evolução
st.subheader("Evolução")

if rgf is not None:
    serie = rgf.xs("E", level="poder")["pessoal_pct"].dropna().reset_index() if "pessoal_pct" in rgf.columns else pd.DataFrame()
    if len(serie) >= 2:
        serie = serie.sort_values(["ano", "periodo"])
        serie["rotulo"] = [f"{QUADRIMESTRES[p]} {a % 100:02d}" for a, p in zip(serie["ano"], serie["periodo"])]
        ultimo_e = rgf.xs("E", level="poder").sort_index().iloc[-1]
        fig = go.Figure()
        fig.add_scatter(x=serie["rotulo"], y=serie["pessoal_pct"], mode="lines", name="Pessoal – Prefeitura",
                        line=dict(color=AZUL, width=2), customdata=[pp(v) for v in serie["pessoal_pct"]],
                        hovertemplate="%{customdata} da RCL<extra></extra>")
        fig.add_scatter(x=serie["rotulo"].iloc[-1:], y=serie["pessoal_pct"].iloc[-1:], mode="markers+text",
                        marker=dict(color=AZUL, size=9), text=[pp(serie["pessoal_pct"].iloc[-1])],
                        textposition="bottom right", cliponaxis=False, showlegend=False, hoverinfo="skip")
        for chave, nome in [("pessoal_limite_maximo_pct", "Máximo"), ("pessoal_limite_prudencial_pct", "Prudencial"),
                            ("pessoal_limite_alerta_pct", "Alerta")]:
            limite = valor(ultimo_e, chave)
            if limite is not None:
                fig.add_hline(y=limite, line_dash="dash", line_width=1, line_color=CINZA,
                              annotation_text=f"{nome} {pp(limite, 1)}", annotation_position="top left",
                              annotation_font_size=11)
        piso = min(serie["pessoal_pct"].min(), 46) - 1
        fig.update_yaxes(range=[piso, 55.5], ticksuffix="%", title=None)
        fig.update_xaxes(title=None)
        fig.update_layout(hovermode="x unified")
        st.markdown("**Gasto com pessoal da Prefeitura, em % da receita corrente líquida**")
        mostrar(estilo_grafico(fig, 320, legenda=False), alt="Gasto com pessoal da Prefeitura por quadrimestre")
        with st.expander("Ver dados em tabela"):
            t = serie[["ano", "periodo", "pessoal_pct"]].rename(
                columns={"ano": "Ano", "periodo": "Quadrimestre", "pessoal_pct": "Pessoal (% da RCL)"})
            tabela(t.iloc[::-1], pontos_percentuais=["Pessoal (% da RCL)"])

# por ano: último período disponível de cada exercício (6º bimestre nos anos fechados)
fim_de_ano = rreo.reset_index().sort_values(["ano", "periodo"]).groupby("ano").tail(1).set_index("ano")
fim_de_ano["rotulo"] = [str(a) if p == 6 else f"{a}*" for a, p in zip(fim_de_ano.index, fim_de_ano["periodo"])]
parcial = fim_de_ano[fim_de_ano["periodo"] < 6]
nota_parcial = (f"\\* {', '.join(f'{a} até {NOMES_MES[2 * int(p)].lower()}' for a, p in parcial['periodo'].items())}: "
                "ano em andamento, comparado com o previsto para o ano inteiro.") if len(parcial) else ""

esq, dir_ = st.columns(2, gap="large")
for coluna, titulo, previsto, realizado, nome_prev, nome_real in [
    (esq, "Receita: prevista × arrecadada", "receita_prevista_atualizada", "receita_realizada", "Prevista", "Arrecadada"),
    (dir_, "Despesa: autorizada × liquidada", "despesa_dotacao_atualizada", "despesa_liquidada", "Autorizada", "Liquidada"),
]:
    with coluna:
        st.markdown(f"**{titulo}, por ano (R$ milhões)**")
        dados = fim_de_ano[[previsto, realizado, "rotulo"]].dropna()
        fig = go.Figure()
        fig.add_bar(x=dados["rotulo"], y=dados[previsto] / 1e6, name=nome_prev, marker=dict(color=CINZA, cornerradius=4),
                    customdata=[brl(v) for v in dados[previsto]], hovertemplate="%{customdata}")
        fig.add_bar(x=dados["rotulo"], y=dados[realizado] / 1e6, name=nome_real, marker=dict(color=AZUL, cornerradius=4),
                    customdata=[brl(v) for v in dados[realizado]], hovertemplate="%{customdata}")
        espaco = 0.7 if len(dados) <= 3 else 0.55 if len(dados) <= 5 else 0.35  # barras finas mesmo com poucos anos
        fig.update_layout(barmode="group", bargap=espaco, bargroupgap=0.12, hovermode="x unified")
        fig.update_yaxes(tickformat=",.0f", title=None)
        fig.update_xaxes(title=None, type="category")
        mostrar(estilo_grafico(fig, 300), alt=titulo)
        with st.expander("Ver dados em tabela"):
            t = dados.reset_index()[["rotulo", previsto, realizado]]
            t.columns = ["Ano", nome_prev, nome_real]
            t["% realizado"] = t[nome_real] / t[nome_prev]
            tabela(t.iloc[::-1], monetarias=[nome_prev, nome_real], percentuais=["% realizado"])
if nota_parcial:
    st.caption(nota_parcial)

esq, dir_ = st.columns(2, gap="large")
for coluna, titulo, chave in [(esq, "Educação: % aplicado", "educacao"), (dir_, "Saúde: % aplicado", "saude")]:
    with coluna:
        st.markdown(f"**{titulo} da receita de impostos**")
        dados = fim_de_ano[[f"{chave}_pct", f"{chave}_minimo_pct", "rotulo"]].dropna(subset=[f"{chave}_pct"])
        if dados.empty:
            st.caption("Sem dado.")
            continue
        fig = go.Figure()
        fig.add_scatter(x=dados["rotulo"], y=dados[f"{chave}_pct"], mode="lines+markers", name="Aplicado",
                        line=dict(color=AZUL, width=2), marker=dict(color=AZUL, size=8),
                        customdata=[pp(v) for v in dados[f"{chave}_pct"]], hovertemplate="%{customdata}<extra></extra>")
        minimo = dados[f"{chave}_minimo_pct"].dropna()
        if len(minimo):
            fig.add_hline(y=float(minimo.iloc[-1]), line_dash="dash", line_width=1, line_color=CINZA,
                          annotation_text=f"Mínimo {pp(float(minimo.iloc[-1]), 0)}", annotation_position="bottom left",
                          annotation_font_size=11)
        topo = max(dados[f"{chave}_pct"].max(), float(minimo.max()) if len(minimo) else 0) * 1.15
        fig.update_yaxes(range=[0, topo], ticksuffix="%", title=None)
        fig.update_xaxes(title=None, type="category")
        mostrar(estilo_grafico(fig, 260, legenda=False), alt=titulo)
        with st.expander("Ver dados em tabela"):
            t = dados.reset_index()[["rotulo", f"{chave}_pct", f"{chave}_minimo_pct"]]
            t.columns = ["Ano", "Aplicado (%)", "Mínimo (%)"]
            tabela(t.iloc[::-1], pontos_percentuais=["Aplicado (%)", "Mínimo (%)"])

# ------------------------------------------------------------------- como ler
with st.expander("Como ler estes números"):
    st.markdown(
        f"""
- **Previsto e autorizado**: o que o orçamento do ano estimou arrecadar e autorizou gastar, já com as alterações
  feitas durante o ano. **Liquidado** é a despesa com o serviço prestado ou o bem entregue.
- **Receita corrente líquida (RCL)**: receita dos últimos 12 meses, sem repasses obrigatórios. É a base dos limites
  da Lei de Responsabilidade Fiscal (LRF).
- **Gasto com pessoal**: a LRF limita a 54% da RCL no Executivo e 6% no Legislativo. Acima de 90% do limite, o
  Tribunal de Contas emite alerta; acima de 95% (limite prudencial), a lei proíbe aumentos e contratações.
- **Dívida consolidada líquida**: dívida menos o dinheiro em caixa; o limite do Senado é 120% da RCL.
- **Educação e saúde**: a Constituição exige aplicar ao menos 25% (educação) e 15% (saúde) da receita de impostos;
  70% do FUNDEB deve ir para a remuneração dos profissionais. A apuração vale para o ano inteiro.
- **Meta de resultado primário**: definida na Lei de Diretrizes Orçamentárias; só pode ser avaliada no fim do ano.

Fontes: Relatório Resumido da Execução Orçamentária (RREO, bimestral) e Relatório de Gestão Fiscal (RGF,
quadrimestral) publicados pelo município no SICONFI, do Tesouro Nacional. Valores como publicados, sem ajustes.
Veja também o [portal da transparência]({config.URL_PORTAL_TRANSPARENCIA}).
"""
    )

st.subheader("Explore")
atalhos = [
    ("paginas/receitas.py", "Receitas", ":material/payments:", "Impostos e repasses mês a mês, previsto × arrecadado."),
    ("paginas/despesa.py", "Despesas", ":material/receipt_long:", "Por função, natureza e órgão, com o demonstrativo."),
    ("paginas/compras.py", "Compras e contratos", ":material/gavel:", "Licitações, dispensas e contratos no PNCP."),
    ("paginas/comparar.py", "Comparar cidades", ":material/map:", "Sua cidade ao lado de outra do Paraná, no mapa."),
]
for coluna, (pagina, rotulo, icone, texto) in zip(st.columns(4), atalhos):
    with coluna.container(border=True):
        st.page_link(pagina, label=rotulo, icon=icone)
        st.caption(texto)
