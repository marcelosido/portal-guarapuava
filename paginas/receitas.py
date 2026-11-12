"""Página "Receitas": de onde vem o dinheiro – impostos municipais e transferências.

Fontes: RREO Anexo 1 (previsto × arrecadado no ano, por origem) e RREO Anexo 3 (arrecadação mês a mês
dos últimos 12 meses, por imposto e transferência), publicados pelo município no SICONFI.
"""

from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from despesas import config
from despesas.dicionarios import NOMES_MES, SIGLAS_MES
from despesas.formatacao import brl, brl_compacto, pct, razao
from despesas.indicadores import ORIGENS_RECEITA, RECEITAS_RCL
from despesas.painel import (assinatura, aviso_demonstracao, cabecalho, carregar_indicadores, carregar_receita_corrente,
                             coletado_em, estilo_grafico, ler_metadados, md, medidor, mostrar, pasta_dados, sem_dados,
                             seletor_ano, tabela, tema)

PASTA = pasta_dados()
meta = ler_metadados(PASTA)
cidade = meta.get("nome_ente", config.NOME_ENTE).split(" - ")[0]

ind = carregar_indicadores(str(PASTA), assinatura(PASTA / "fIndicadores.csv"))
rcl = carregar_receita_corrente(str(PASTA), assinatura(PASTA / "fReceitaCorrente.csv"))
if ind.empty or not (ind["relatorio"] == "RREO").any():
    st.title("Receitas")
    sem_dados()

rreo = ind[ind["relatorio"] == "RREO"].pivot_table(index=["ano", "periodo"], columns="chave", values="valor",
                                                   aggfunc="first")
anos = sorted(rreo.index.get_level_values("ano").unique().tolist(), reverse=True)
ano = cabecalho("Receitas", f"De onde vem o dinheiro da prefeitura de {cidade}: os impostos que o município cobra "
                "e os repasses da União e do Estado.",
                seletor=lambda coluna: seletor_ano(coluna, anos, "Exercício"))
bim = int(max(p for a, p in rreo.index if a == ano))
r = rreo.loc[(ano, bim)]
mes = 2 * bim
ate = f"até {NOMES_MES[mes].lower()}/{ano}"
st.caption(md(f"Fonte: Tesouro Nacional (SICONFI) – RREO Anexos 1 e 3 · {ate} · atualizado em {coletado_em(meta)}"))
aviso_demonstracao(meta)


def valor(chave: str) -> float | None:
    v = r.get(chave)
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)


# ------------------------------------------------------------------------------ KPIs
total_prev, total_real = valor("receita_total_prevista"), valor("receita_total_realizada")
trib = valor("receita_tributaria_realizada")
transf = [valor(f"receita_{c}_realizada") for c in ("uniao", "estado", "outras_publicas")]
transferencias = sum(transf) if all(v is not None for v in transf) else None
correntes = valor("receita_correntes_realizada")
populacao = valor("populacao")

k = st.columns(4)
k[0].metric("Receita arrecadada", brl_compacto(total_real), border=True,
            delta=f"{pct(razao(total_real, total_prev))} do previsto para o ano" if total_real and total_prev else None,
            delta_color="off", delta_arrow="off",
            help=f"Tudo o que entrou {ate}, sem as receitas intraorçamentárias (repasses entre órgãos do município).")
k[1].metric("Impostos e taxas do município", brl_compacto(trib), border=True,
            delta=f"{pct(razao(trib, correntes))} das receitas correntes" if trib and correntes else None,
            delta_color="off", delta_arrow="off",
            help="IPTU, ISS, ITBI, imposto de renda retido, taxas e contribuição de melhoria: a receita própria.")
k[2].metric("Transferências recebidas", brl_compacto(transferencias), border=True,
            delta=f"{pct(razao(transferencias, correntes))} das receitas correntes" if transferencias and correntes else None,
            delta_color="off", delta_arrow="off",
            help="Repasses da União (FPM, SUS...), do Estado (ICMS, IPVA...) e de outras instituições (FUNDEB).")
k[3].metric("Arrecadação por habitante", brl(razao(total_real, populacao), 0) if total_real and populacao else "–",
            border=True, help=f"Receita arrecadada {ate} dividida pela população informada no RREO"
            + (f" ({populacao:,.0f} habitantes)".replace(",", ".") if populacao else "") + ".")

# ------------------------------------------- impostos e transferências (RREO Anexo 3)
cores = tema()["serie"]
GRUPOS = {"Impostos municipais": cores[0], "Transferências": cores[1], "Outras receitas": cores[2]}
recorte = rcl[(rcl["ano"] == ano)] if len(rcl) else rcl
if len(recorte):
    per_rcl = int(recorte["periodo"].max())
    recorte = recorte[recorte["periodo"] == per_rcl]
    fim_janela = f"{SIGLAS_MES[2 * per_rcl].lower()}/{ano}"
    inicio_mes = (ano * 12 + 2 * per_rcl - 12)
    inicio_janela = f"{SIGLAS_MES[inicio_mes % 12 + 1].lower()}/{inicio_mes // 12}"
    janela = "de janeiro a dezembro de " + str(ano) if per_rcl == 6 else f"de {inicio_janela} a {fim_janela}"

    st.subheader("Impostos e transferências nos últimos 12 meses")
    st.caption(f"Arrecadação {janela}, por fonte (RREO Anexo 3). Mostra o peso de cada imposto e de cada repasse.")
    tot = recorte[recorte["referencia"] == "12m"].set_index("chave")["valor"]
    prev = recorte[recorte["referencia"] == "previsao"].set_index("chave")["valor"]
    linhas = [(chave, nome, grupo, float(tot[chave]), float(prev[chave]) if chave in prev else None)
              for chave, (_, nome, grupo) in RECEITAS_RCL.items() if grupo != "Total" and chave in tot and tot[chave] > 0]
    df = pd.DataFrame(linhas, columns=["chave", "fonte", "grupo", "valor", "previsto"]).sort_values("valor")
    if len(df):
        fig = go.Figure()
        for grupo, cor in GRUPOS.items():
            parte = df[df["grupo"] == grupo]
            if parte.empty:
                continue
            fig.add_bar(y=parte["fonte"], x=parte["valor"] / 1e6, orientation="h", name=grupo, width=0.6,
                        marker=dict(color=cor, cornerradius=4), text=[brl_compacto(v) for v in parte["valor"]],
                        textposition="outside", cliponaxis=False, customdata=[brl(v) for v in parte["valor"]],
                        hovertemplate="%{y}: %{customdata}<extra></extra>")
        fig.update_yaxes(categoryorder="array", categoryarray=df["fonte"].tolist(), title=None)
        fig.update_xaxes(title="R$ milhões", tickformat=",.0f", range=[0, df["valor"].max() / 1e6 * 1.18])
        fig.update_layout(barmode="overlay")
        mostrar(estilo_grafico(fig, 90 + 30 * len(df)), alt=f"Arrecadação por fonte {janela}")
        correntes_12m = float(tot.get("correntes", float("nan")))
        propria = df.loc[df["grupo"] == "Impostos municipais", "valor"].sum()
        if correntes_12m == correntes_12m and correntes_12m > 0:
            st.caption(f"Impostos e taxas do município: {pct(propria / correntes_12m)} das receitas correntes nesses "
                       f"12 meses. Valores brutos, antes da dedução para o FUNDEB.")
        with st.expander("Ver dados em tabela"):
            t = df.sort_values("valor", ascending=False)[["fonte", "grupo", "valor", "previsto"]]
            t.columns = ["Fonte", "Grupo", "Arrecadado em 12 meses", f"Previsto para {ano}"]
            tabela(t, monetarias=["Arrecadado em 12 meses", f"Previsto para {ano}"])

        # mês a mês de uma fonte
        st.markdown("**Mês a mês**")
        opcoes = df.sort_values("valor", ascending=False)["chave"].tolist()
        nomes = dict(zip(df["chave"], df["fonte"]))
        escolha = st.selectbox("Fonte de receita", opcoes, index=opcoes.index("iptu") if "iptu" in opcoes else 0,
                               format_func=lambda c: nomes[c], key="fonte_mes")
        mensal = recorte[(recorte["chave"] == escolha) & recorte["referencia"].str.match(r"^\d{4}-\d{2}$")]
        mensal = mensal.sort_values("referencia")
        rotulos = [f"{SIGLAS_MES[int(m[5:])]}/{m[2:4]}" for m in mensal["referencia"]]
        fig = go.Figure()
        fig.add_bar(x=rotulos, y=mensal["valor"] / 1e6, name=nomes[escolha], width=0.55,
                    marker=dict(color=cores[0], cornerradius=4), customdata=[brl(v) for v in mensal["valor"]],
                    hovertemplate="%{x}: %{customdata}<extra></extra>")
        fig.update_yaxes(title="R$ milhões", tickformat=",.1f", rangemode="tozero")
        fig.update_xaxes(title=None, type="category")
        mostrar(estilo_grafico(fig, 280, legenda=False), alt=f"{nomes[escolha]} arrecadado mês a mês")
        with st.expander("Ver dados em tabela"):
            t = pd.DataFrame({"Mês": rotulos, "Arrecadado": mensal["valor"].values})
            tabela(t, monetarias=["Arrecadado"])
else:
    st.info("O detalhamento por imposto (RREO Anexo 3) ainda não foi coletado. Ele entra na próxima execução "
            "do robô de atualização.", icon=":material/schedule:")

# ------------------------------------------------ previsto × arrecadado (RREO Anexo 1)
st.subheader(f"Previsto × arrecadado em {ano}, por origem")
st.caption(f"Receita prevista para o ano inteiro × arrecadada {ate} (RREO Anexo 1), sem as receitas "
           "intraorçamentárias. Com o ano em andamento, o arrecadado tende a ficar abaixo do previsto.")
origens = []
for chave, (_, nome) in ORIGENS_RECEITA.items():
    if chave in ("correntes", "total"):
        continue
    prevista, arrecadada = valor(f"receita_{chave}_prevista"), valor(f"receita_{chave}_realizada")
    if prevista:
        origens.append((nome, prevista, arrecadada or 0.0))
componentes = ["tributaria", "uniao", "estado", "outras_publicas", "contribuicoes", "patrimonial"]
correntes_prev, correntes_real = valor("receita_correntes_prevista"), valor("receita_correntes_realizada")
if correntes_prev and all(valor(f"receita_{c}_prevista") is not None for c in componentes):
    resto_prev = correntes_prev - sum(valor(f"receita_{c}_prevista") for c in componentes)
    resto_real = (correntes_real or 0) - sum(valor(f"receita_{c}_realizada") or 0 for c in componentes)
    if resto_prev > 0:
        origens.append(("Outras receitas correntes (serviços, multas, etc.)", resto_prev, resto_real))
if origens:
    o = pd.DataFrame(origens, columns=["origem", "prevista", "arrecadada"]).sort_values("prevista", ascending=False)
    medidor([(nome, f"{brl_compacto(a)} arrecadados de {brl_compacto(p)} previstos ({pct(razao(a, p))})", p, a)
             for nome, p, a in o.itertuples(index=False)],
            "Previsto para o ano", "Arrecadado", alt=f"Receita prevista e arrecadada por origem em {ano}")
    with st.expander("Ver dados em tabela"):
        t = o.rename(columns={"origem": "Origem", "prevista": "Prevista", "arrecadada": "Arrecadada"})
        t["% arrecadado"] = t["Arrecadada"] / t["Prevista"]
        tabela(t, monetarias=["Prevista", "Arrecadada"], percentuais=["% arrecadado"])
else:
    st.caption("Sem detalhamento por origem neste relatório.")

# --------------------------------------------------------------- evolução por ano
anuais = rcl[(rcl["periodo"] == 6) & (rcl["referencia"] == "12m")] if len(rcl) else rcl
if len(anuais) and anuais["ano"].nunique() >= 2:
    st.subheader("Evolução por ano")
    st.caption("Arrecadação de janeiro a dezembro de cada ano fechado (RREO Anexo 3, 6º bimestre), em valores da "
               "época, sem correção pela inflação.")
    nomes = {c: n for c, (_, n, g) in RECEITAS_RCL.items() if g != "Total"}
    disponiveis = [c for c in nomes if c in set(anuais["chave"])]
    padrao = [c for c in ("iss", "iptu", "icms", "fpm") if c in disponiveis]
    escolhidas = st.multiselect("Fontes (até 4)", disponiveis, default=padrao, max_selections=4,
                                format_func=lambda c: nomes[c], key="fontes_evolucao")
    if escolhidas:
        cores_linha = tema()["serie"] + ["#eda100"]
        fig = go.Figure()
        for chave, cor in zip(escolhidas, cores_linha):
            serie = anuais[anuais["chave"] == chave].sort_values("ano")
            fig.add_scatter(x=serie["ano"].astype(str), y=serie["valor"] / 1e6, mode="lines+markers", name=nomes[chave],
                            line=dict(color=cor, width=2), marker=dict(color=cor, size=8),
                            customdata=[brl(v) for v in serie["valor"]], hovertemplate="%{customdata}")
        fig.update_layout(hovermode="x unified")
        fig.update_yaxes(title="R$ milhões", tickformat=",.0f", rangemode="tozero")
        fig.update_xaxes(title=None, type="category")
        mostrar(estilo_grafico(fig, 340), alt="Arrecadação anual por fonte")
        with st.expander("Ver dados em tabela"):
            t = anuais[anuais["chave"].isin(escolhidas)].pivot_table(index="ano", columns="chave", values="valor")
            t = t.rename(columns=nomes).reset_index().rename(columns={"ano": "Ano"}).sort_values("Ano", ascending=False)
            tabela(t, monetarias=[c for c in t.columns if c != "Ano"])

with st.expander("Como ler estes números"):
    st.markdown(
        """
- **Impostos municipais**: IPTU (imóveis), ISS (serviços), ITBI (venda de imóveis), o imposto de renda retido dos
  servidores municipais e as taxas. É a receita que o município arrecada por conta própria.
- **Transferências**: parte de impostos federais e estaduais que a Constituição manda repassar – FPM (União),
  cota-parte do ICMS e do IPVA (Estado) – e o FUNDEB, que redistribui recursos para a educação básica.
- **Receitas de capital**: empréstimos, convênios para obras e venda de bens. Costumam ser previstas no orçamento
  e só se realizar quando o contrato ou o convênio é assinado.
- O Anexo 3 mostra os valores **brutos**; a receita corrente líquida desconta, entre outros, a parte que vai
  para o FUNDEB e a contribuição dos servidores para a previdência.
"""
    )
