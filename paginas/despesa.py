"""Página "Despesas": execução da despesa por natureza, função e poder/órgão (MSC)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from despesas import config
from despesas.dicionarios import NOMES_MES, SIGLAS_MES
from despesas.formatacao import brl, brl_compacto, numero, pct, razao
from despesas.painel import (AZUL, AZUL_TRILHA, CINZA, assinatura, aviso_demonstracao, cabecalho, carregar_despesa,
                             coletado_em, estilo_grafico, ler_metadados, md, mes_extenso, mostrar,
                             pacote_dados_abertos, pasta_dados, sem_acento, sem_dados, seletor_ano, tabela)
from despesas.transformacao import COLUNAS_MEDIDAS

PASTA = pasta_dados()
arq_fato = PASTA / "fDespesa.parquet"
meta = ler_metadados(PASTA)
nome_ente = meta.get("nome_ente", config.NOME_ENTE)

if not arq_fato.exists():
    st.title("Despesas")
    sem_dados()
fato, conciliacao = carregar_despesa(str(PASTA), assinatura(arq_fato))
coletado = coletado_em(meta)
cabecalho("Despesas", "Quanto a prefeitura tem autorizado para gastar, quanto já empenhou, liquidou e pagou – por "
          "função de governo, tipo de despesa e órgão.")
st.caption(md(f"Fonte: Tesouro Nacional (SICONFI) – Matriz de Saldos Contábeis · valores acumulados no ano · dados até "
              f"{mes_extenso(meta.get('ultimo_mes', ''))} · atualizado em {coletado}"))
aviso_demonstracao(meta)

# --------------------------------------------------------------------------- filtros
anos = sorted(fato["ano"].unique().tolist(), reverse=True)
c1, c2, c3, c4 = st.columns([1, 1.2, 2.3, 2.5])
ano = seletor_ano(c1, anos, "Exercício")
meses = sorted(fato.loc[fato["ano"] == ano, "mes"].unique().tolist())
mes = c2.selectbox("Acumulado até", meses, index=len(meses) - 1, format_func=lambda x: NOMES_MES[x])
poderes = c3.multiselect("Poder / órgão", sorted(fato["poder_orgao_desc"].unique()), placeholder="Todos")
funcoes = c4.multiselect("Função", sorted(fato["funcao_desc"].unique()), placeholder="Todas")

filtro = pd.Series(True, index=fato.index)
if poderes:
    filtro &= fato["poder_orgao_desc"].isin(poderes)
if funcoes:
    filtro &= fato["funcao_desc"].isin(funcoes)
base = fato[filtro]
recorte = base[(base["ano"] == ano) & (base["mes"] == mes)]
anterior = base[(base["ano"] == ano - 1) & (base["mes"] == mes)]
if recorte.empty:
    st.info("Nenhuma despesa para os filtros escolhidos.")
    st.stop()

periodo = f"{SIGLAS_MES[mes].lower()}/{ano}"
periodo_ant = f"{SIGLAS_MES[mes].lower()}/{ano - 1}"

# ------------------------------------------------------------------------------ KPIs
tot = recorte[COLUNAS_MEDIDAS].sum()
tot_ant = anterior[COLUNAS_MEDIDAS].sum() if len(anterior) else None
execucao = razao(tot["liquidado"], tot["dotacao_atualizada"])

k = st.columns(5)
k[0].metric(
    "Dotação atualizada", brl_compacto(tot["dotacao_atualizada"]),
    delta=f"inicial {brl_compacto(tot['dotacao_inicial'])}", delta_color="off", delta_arrow="off", border=True,
    help=f"Orçamento autorizado com créditos adicionais e anulações: {brl(tot['dotacao_atualizada'])}",
)
k[1].metric(
    "Empenhado", brl_compacto(tot["empenhado"]),
    delta=f"{pct(razao(tot['empenhado'], tot['dotacao_atualizada']))} da dotação", delta_color="off",
    delta_arrow="off", border=True, help=f"Despesa reservada por empenho até {periodo}: {brl(tot['empenhado'])}",
)
if tot_ant is not None and tot_ant["liquidado"]:
    variacao = razao(tot["liquidado"], tot_ant["liquidado"]) - 1
    delta_liq = f"{'+' if variacao >= 0 else ''}{pct(variacao)} vs {periodo_ant}"
else:
    delta_liq = None
k[2].metric(
    "Liquidado", brl_compacto(tot["liquidado"]), delta=delta_liq, delta_color="off", border=True,
    help=f"Bens e serviços entregues e atestados até {periodo}: {brl(tot['liquidado'])}",
)
k[3].metric(
    "Pago", brl_compacto(tot["pago"]),
    delta=f"{pct(razao(tot['pago'], tot['liquidado']))} do liquidado", delta_color="off", delta_arrow="off",
    border=True, help=f"Valores efetivamente pagos até {periodo}: {brl(tot['pago'])}",
)
exec_ant = razao(tot_ant["liquidado"], tot_ant["dotacao_atualizada"]) if tot_ant is not None else float("nan")
k[4].metric(
    "Execução", pct(execucao),
    delta=f"{periodo_ant}: {pct(exec_ant)}" if tot_ant is not None else None, delta_color="off", delta_arrow="off",
    border=True, help="Liquidado ÷ dotação atualizada – mesmo percentual da página do portal da transparência",
)

aba_geral, aba_demo = st.tabs(["Visão geral", "Demonstrativo"])

# ----------------------------------------------------------------------- visão geral
with aba_geral:
    titulo, seletor = st.columns([3, 2], vertical_alignment="bottom")
    titulo.subheader("Liquidado ao longo do ano")
    modo = seletor.segmented_control(
        "Visualização", ["Acumulado no ano", "Mês a mês"], default="Acumulado no ano", label_visibility="collapsed",
        key="modo_serie",
    ) or "Acumulado no ano"

    serie = base[base["ano"].isin([ano, ano - 1])].groupby(["ano", "mes"])["liquidado"].sum().reset_index()
    serie = serie[(serie["ano"] == ano - 1) | (serie["mes"] <= mes)].sort_values(["ano", "mes"])
    serie["no_mes"] = serie.groupby("ano")["liquidado"].diff().fillna(serie["liquidado"])
    coluna = "liquidado" if modo == "Acumulado no ano" else "no_mes"
    fig = go.Figure()
    for a, cor in ((ano - 1, CINZA), (ano, AZUL)):
        s = serie[serie["ano"] == a]
        if s.empty:
            continue
        x = [SIGLAS_MES[m] for m in s["mes"]]
        valores = [brl(v) for v in s[coluna]]
        if modo == "Acumulado no ano":
            fig.add_scatter(
                x=x, y=s[coluna] / 1e6, name=str(a), mode="lines", customdata=valores,
                line=dict(color=cor, width=2, shape="linear"), hovertemplate="%{customdata}",
            )
            fig.add_scatter(  # ponto final da série (marca o último mês disponível)
                x=x[-1:], y=s[coluna].iloc[-1:] / 1e6, mode="markers", marker=dict(color=cor, size=9),
                showlegend=False, hoverinfo="skip",
            )
        else:
            fig.add_bar(x=x, y=s[coluna] / 1e6, name=str(a), marker=dict(color=cor, cornerradius=4),
                        customdata=valores, hovertemplate="%{customdata}")
    atual = serie[serie["ano"] == ano]
    if modo == "Acumulado no ano" and len(atual):
        fim = atual.iloc[-1]
        ref = serie[(serie["ano"] == ano - 1) & (serie["mes"] == fim["mes"])]["liquidado"]
        acima = ref.empty or fim["liquidado"] >= ref.iloc[0]  # rótulo do lado oposto à linha do ano anterior
        fig.add_annotation(x=SIGLAS_MES[int(fim["mes"])], y=fim["liquidado"] / 1e6, text=brl_compacto(fim["liquidado"]),
                           showarrow=False, xanchor="right", yanchor="bottom" if acima else "top",
                           yshift=10 if acima else -10, font=dict(size=13))
    fig.update_layout(hovermode="x unified", barmode="group", bargap=0.35, bargroupgap=0.1)
    fig.update_xaxes(categoryorder="array", categoryarray=list(SIGLAS_MES.values()), title=None)
    fig.update_yaxes(title="R$ milhões", rangemode="tozero", tickformat=",.0f")
    mostrar(estilo_grafico(fig, 360), alt=f"Liquidado {modo.lower()} em {ano} comparado com {ano - 1}")
    with st.expander("Ver dados em tabela"):
        t = serie.pivot(index="mes", columns="ano", values=coluna).reset_index()
        t["mes"] = t["mes"].map(NOMES_MES)
        t.columns = ["Mês"] + [str(c) for c in t.columns[1:]]
        tabela(t, monetarias=[c for c in t.columns if c != "Mês"])

    esq, dir_ = st.columns(2, gap="large")
    with esq:
        st.subheader("Execução por grupo de despesa")
        g = recorte.groupby("grupo_desc")[["dotacao_atualizada", "liquidado"]].sum()
        g = g[g["dotacao_atualizada"] > 0].sort_values("dotacao_atualizada")
        g["execucao"] = g["liquidado"] / g["dotacao_atualizada"]
        fig = go.Figure()
        fig.add_bar(
            y=g.index, x=g["dotacao_atualizada"] / 1e6, orientation="h", name="Dotação atualizada", width=0.55,
            marker=dict(color=AZUL_TRILHA, cornerradius=4), customdata=[brl(v) for v in g["dotacao_atualizada"]],
            text=[pct(v) for v in g["execucao"]], textposition="outside", cliponaxis=False,
            hovertemplate="%{customdata}",
        )
        fig.add_bar(
            y=g.index, x=g["liquidado"] / 1e6, orientation="h", name="Liquidado", width=0.55,
            marker=dict(color=AZUL, cornerradius=4), customdata=[brl(v) for v in g["liquidado"]],
            hovertemplate="%{customdata}",
        )
        fig.update_layout(barmode="overlay", hovermode="y unified")
        fig.update_xaxes(title="R$ milhões", tickformat=",.0f")
        fig.update_yaxes(title=None)
        mostrar(estilo_grafico(fig, 90 + 44 * len(g)),
                alt=f"Dotação atualizada e liquidado por grupo de despesa até {periodo}")
        st.caption("Faixa de fundo: dotação atualizada · barra azul: liquidado · % = liquidado ÷ dotação atualizada")
        with st.expander("Ver dados em tabela"):
            t = g.sort_values("dotacao_atualizada", ascending=False).reset_index()
            t.columns = ["Grupo", "Dotação atualizada", "Liquidado", "Execução"]
            tabela(t, monetarias=["Dotação atualizada", "Liquidado"], percentuais=["Execução"])

    with dir_:
        st.subheader("Liquidado por função")
        f = recorte.groupby("funcao_desc")["liquidado"].sum()
        f = f[f > 0].sort_values(ascending=False)
        if len(f) > 10:
            f = pd.concat([f.iloc[:9], pd.Series({"Outras funções": f.iloc[9:].sum()})])
        f = f.iloc[::-1]
        cores = [CINZA if nome == "Outras funções" else AZUL for nome in f.index]
        fig = go.Figure()
        fig.add_bar(
            y=f.index, x=f.values / 1e6, orientation="h", name="Liquidado", width=0.55,
            marker=dict(color=cores, cornerradius=4), text=[brl_compacto(v) for v in f.values],
            textposition="outside", cliponaxis=False,
            customdata=[[brl(v), pct(v / f.sum())] for v in f.values],
            hovertemplate="%{y}<br>%{customdata[0]} (%{customdata[1]} do total)<extra></extra>",
        )
        fig.update_xaxes(title="R$ milhões", tickformat=",.0f")
        fig.update_yaxes(title=None)
        mostrar(estilo_grafico(fig, 60 + 44 * len(f), legenda=False), alt=f"Liquidado por função até {periodo}")
        with st.expander("Ver dados em tabela"):
            t = f.iloc[::-1].rename("Liquidado").rename_axis("Função").reset_index()
            t["Participação"] = t["Liquidado"] / t["Liquidado"].sum()
            tabela(t, monetarias=["Liquidado"], percentuais=["Participação"])

# ---------------------------------------------------------------------- demonstrativo
with aba_demo:
    st.subheader(f"Demonstrativo da despesa até {periodo}")
    st.caption(
        "Mesmo recorte da página “Demonstrativo das Despesas” do portal da transparência: dotação e liquidado "
        "acumulados até o mês, por natureza da despesa."
    )
    d1, d2 = st.columns([1.2, 2], vertical_alignment="bottom")
    nivel = d1.segmented_control("Detalhar até", ["Grupo", "Modalidade", "Elemento"], default="Elemento",
                                 key="nivel_demo") or "Elemento"
    busca = d2.text_input("Buscar", placeholder="Código ou descrição – ex.: 3.3.90.39 ou consultoria",
                          label_visibility="collapsed")

    niveis = {
        "Grupo": (["categoria", "grupo"], ["categoria_desc", "grupo_desc"]),
        "Modalidade": (["categoria", "grupo", "modalidade"], ["categoria_desc", "grupo_desc", "modalidade_desc"]),
        "Elemento": (["categoria", "grupo", "modalidade", "elemento"],
                     ["categoria_desc", "grupo_desc", "modalidade_desc", "elemento_desc"]),
    }
    codigos, descricoes = niveis[nivel]
    chaves = ["poder_orgao_desc", *codigos, *descricoes]
    dem = recorte.groupby(chaves)[["dotacao_atualizada", "empenhado", "liquidado", "pago"]].sum().reset_index()
    dem["codigo"] = dem[codigos].agg(".".join, axis=1)
    dem["execucao"] = dem["liquidado"] / dem["dotacao_atualizada"].where(dem["dotacao_atualizada"] != 0)
    dem = dem.sort_values(["poder_orgao_desc", "codigo"])
    if busca:
        termo = sem_acento(busca).replace(".", "")
        alvo = (dem["codigo"].str.replace(".", "", regex=False) + " " + dem[descricoes].agg(" ".join, axis=1)).map(sem_acento)
        dem = dem[alvo.str.contains(termo, regex=False)]

    # Valores logo depois da descrição do nível escolhido; níveis superiores ficam no fim, como contexto.
    nomes = {"poder_orgao_desc": "Poder / órgão", "codigo": "Natureza", descricoes[-1]: "Descrição",
             "dotacao_atualizada": "Dotação atualizada", "empenhado": "Empenhado", "liquidado": "Liquidado até o mês",
             "pago": "Pago", "execucao": "% execução", "categoria_desc": "Categoria econômica",
             "grupo_desc": "Grupo", "modalidade_desc": "Modalidade"}
    colunas = ["poder_orgao_desc", "codigo", descricoes[-1], "dotacao_atualizada", "empenhado", "liquidado", "pago",
               "execucao", *descricoes[:-1]]
    exibir = dem[colunas].rename(columns=nomes)
    tabela(exibir, monetarias=["Dotação atualizada", "Empenhado", "Liquidado até o mês", "Pago"],
           percentuais=["% execução"], altura=520,
           colunas={"Poder / órgão": st.column_config.Column(width="medium"),
                    "Natureza": st.column_config.Column(pinned=True),
                    "Descrição": st.column_config.Column(width="large", pinned=True)})
    st.caption(md(f"{numero(len(exibir), 0)} {'linha' if len(exibir) == 1 else 'linhas'} · "
                  f"liquidado no recorte: {brl(exibir['Liquidado até o mês'].sum())}"))

    b1, b2, _ = st.columns([1, 1, 2])
    csv = exibir.to_csv(sep=";", decimal=",", index=False).encode("utf-8-sig")
    b1.download_button("Baixar este demonstrativo (CSV)", csv, file_name=f"demonstrativo_{ano}_{mes:02d}.csv",
                       mime="text/csv", icon=":material/download:")
    b2.download_button("Baixar a base completa (ZIP)", pacote_dados_abertos(str(PASTA), assinatura(arq_fato)),
                       file_name="dados_abertos_despesa.zip", mime="application/zip", icon=":material/folder_zip:")

st.divider()
st.caption(
    f"Dados abertos: Tesouro Nacional/SICONFI · [Portal da Transparência de {nome_ente}]"
    f"({config.URL_PORTAL_TRANSPARENCIA}) · base completa na aba Demonstrativo"
)
st.page_link("paginas/sobre.py", label="Como os dados são conferidos (MSC × RREO) e a origem de cada número",
             icon=":material/fact_check:")
