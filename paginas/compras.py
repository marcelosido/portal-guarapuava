"""Página "Compras e contratos": licitações, dispensas e contratos dos órgãos municipais no PNCP.

Fonte: API de consultas do PNCP. Fornecedores pessoa física e MEI: nome nas tabelas, sem nenhum número de
documento; nos rankings e pontos de atenção aparecem agrupados (LGPD).
A coluna "Contratado" vem dos contratos ligados a cada contratação (número de controle da compra no PNCP).
"""

from __future__ import annotations

import datetime as dt

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from despesas import config
from despesas.alertas import (MIN_DISPENSAS_MESMO_FORNECEDOR, PRAZO_MINIMO_DIAS_UTEIS, analisar_compras, datas,
                              pontos_compras)
from despesas.dicionarios import SIGLAS_MES
from despesas.formatacao import brl, brl_compacto, numero, pct, razao
from despesas.painel import (assinatura, cabecalho, carregar_compras, estilo_grafico, ler_metadados, md, mostrar,
                             nome_curto, orgaos_sem_contratos, pasta_dados, sem_acento, selo_md, seletor_ano, tabela,
                             tema)
from despesas.pncp import contratados_por_compra, url_contratacao, url_contrato

PASTA = pasta_dados()
meta = ler_metadados(PASTA)
cidade = meta.get("nome_ente", config.NOME_ENTE).split(" - ")[0]
pncp = meta.get("pncp", {})
DESCRICAO = (f"Licitações, dispensas e contratos que a Prefeitura de {cidade} e os demais órgãos municipais publicam "
             "no Portal Nacional de Contratações Públicas (PNCP), com os pontos que merecem atenção.")

contratacoes, contratos = carregar_compras(str(PASTA), assinatura(PASTA / "fContratacoes.csv"))
if contratacoes.empty and contratos.empty:
    cabecalho("Compras e contratos", DESCRICAO)
    st.info("Os dados do PNCP ainda não foram coletados. Eles entram na próxima execução do robô de atualização.",
            icon=":material/schedule:")
    st.stop()

datas_c = datas(contratacoes["data_publicacao"])
datas_k = datas(contratos["data_assinatura"])
anos = sorted({int(a) for a in pd.concat([datas_c.dt.year, datas_k.dt.year]).dropna()}, reverse=True)
ano = cabecalho("Compras e contratos", DESCRICAO, seletor=lambda coluna: seletor_ano(coluna, anos, "Ano"))
inicio = pncp.get("inicio", config.PNCP_INICIO)
atualizado = pd.Timestamp(pncp["coletado_em"]).strftime("%d/%m/%Y") if pncp.get("coletado_em") else "–"
st.caption(md(f"Fonte: PNCP – publicações desde {pd.Timestamp(inicio):%m/%Y} · atualizado em {atualizado} · "
              f"{len(pncp.get('orgaos', [])) or contratacoes['orgao_cnpj'].nunique()} órgãos municipais"))
if pncp.get("url_api") and pncp["url_api"] != config.URL_PNCP_OFICIAL:
    st.warning(f"Estes dados vieram de `{pncp['url_api']}`, não da API oficial do PNCP. Servem só para "
               "demonstração.", icon=":material/science:")

orgaos = sorted((set(contratacoes["orgao_nome"]) | set(contratos["orgao_nome"])) - {""})
escolha = st.multiselect("Órgão", orgaos, placeholder="Todos os órgãos municipais") if len(orgaos) > 1 else []
faltam = orgaos_sem_contratos(pncp, ano, contratacoes, contratos, escolha or None)
if escolha:
    contratacoes = contratacoes[contratacoes["orgao_nome"].isin(escolha)]
    contratos = contratos[contratos["orgao_nome"].isin(escolha)]
if faltam:
    quais = ", ".join(faltam[:3]) + (f" e mais {len(faltam) - 3}" if len(faltam) > 3 else "")
    st.warning(f"**A coleta dos contratos de {ano} ainda não terminou** para {len(faltam)} "
               f"{'órgão' if len(faltam) == 1 else 'órgãos'} ({quais}). Até lá, os contratos, os maiores fornecedores "
               "e a coluna \"Contratado\" estão incompletos. A próxima execução do robô continua de onde parou.",
               icon=":material/hourglass_top:")

a = analisar_compras(contratacoes, contratos, ano, orgaos_pendentes=faltam)


def cnpj_formatado(doc: str) -> str:
    """14 dígitos -> 12.345.678/0001-90; vazio (pessoa física e MEI, LGPD) -> "–"."""
    d = "".join(ch for ch in str(doc) if ch.isdigit())
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}" if len(d) == 14 else "–"


def data_br(serie: pd.Series) -> pd.Series:
    return datas(serie).dt.strftime("%d/%m/%Y").fillna("–")


def com_link(df: pd.DataFrame, contrato: bool = False) -> pd.Series:
    funcao = url_contrato if contrato else url_contratacao
    return df.apply(funcao, axis=1) if len(df) else pd.Series(dtype=str)


AGRUPADOS = "Pessoas físicas e MEI (somados)"
LINK = st.column_config.LinkColumn("PNCP", display_text="Abrir", help="Abre a publicação no PNCP")
OBJETO = st.column_config.Column("Objeto", width="large")
CNPJ = st.column_config.Column("CNPJ", help="Pessoas físicas e microempreendedores individuais aparecem sem CPF ou "
                                            "CNPJ (LGPD).")
CONTRATADO = st.column_config.Column(
    "Contratado", width="medium",
    help="Empresa do contrato ligado a esta contratação no PNCP (\"e mais N\" quando há vários). Fica vazio "
         "enquanto não há contrato publicado: licitação em andamento, registro de preços (ata) ou contrato ainda "
         "não informado pelo órgão. Pessoas físicas e MEI aparecem sem CPF/CNPJ (LGPD).")

# ------------------------------------------------------------------------------ KPIs
validas = a.contratacoes[~a.contratacoes["situacao_id"].isin([2, 3]).fillna(False).astype(bool)]
k = st.columns(4)
k[0].metric("Contratações publicadas", numero(len(a.contratacoes), 0), border=True,
            delta=f"{len(a.canceladas)} revogadas ou anuladas" if len(a.canceladas) else None, delta_color="off",
            delta_arrow="off", help="Licitações, dispensas, inexigibilidades e outros procedimentos publicados no ano.")
k[1].metric("Valor estimado", brl_compacto(a.total_valor), border=True,
            help="Soma do valor estimado das contratações publicadas no ano, sem as revogadas e anuladas.")
k[2].metric("Contratação direta", pct(razao(a.direta_valor, a.total_valor)), border=True,
            delta=f"{a.direta_qtd} dispensas e inexigibilidades", delta_color="off", delta_arrow="off",
            help="Parte do valor estimado contratada sem disputa entre empresas, nos casos que a lei permite.")
total_contratos = float(a.contratos["valor_global"].fillna(0).sum())
k[3].metric("Contratos assinados", brl_compacto(total_contratos), border=True,
            delta=(f"{numero(len(a.contratos), 0)} contratos · coleta incompleta" if faltam
                   else f"{numero(len(a.contratos), 0)} contratos e empenhos"),
            delta_color="off", delta_arrow="off",
            help="Valor global dos contratos (e empenhos que os substituem) assinados no ano.")

# ------------------------------------------------------------------ pontos de atenção
pontos = pontos_compras(a)
with st.container(border=True):
    st.subheader("Pontos de atenção", anchor="pontos-de-atencao")
    st.caption("Situações que a lei manda observar com cuidado ou que fogem do padrão. Não são, por si só, "
               "irregularidades: cada caso tem um link para a publicação oficial no PNCP.")
    if not pontos:
        st.markdown(":green-badge[:material/check_circle: Em dia] Nenhum ponto de atenção nas compras deste ano.")
    for ponto in pontos:
        st.markdown(f"{selo_md(ponto.nivel)} **{md(ponto.titulo)}**  \n{md(ponto.detalhe)}")
        if ponto.chave == "emergencia":
            with st.expander(f"Ver as {len(a.emergenciais)} contratações emergenciais"):
                t = a.emergenciais
                tabela(pd.DataFrame({"Publicação": data_br(t["data_publicacao"]).values, "Órgão": t["orgao_nome"].values,
                                     "Objeto": t["objeto"].values, "Valor estimado": t["valor_estimado"].values,
                                     "Situação": t["situacao"].values, "PNCP": com_link(t).values}),
                       monetarias=["Valor estimado"], colunas={"PNCP": LINK, "Objeto": OBJETO})
        elif ponto.chave == "recorrentes":
            with st.expander(f"Ver os {len(a.recorrentes)} fornecedores"):
                t = a.recorrentes
                tabela(pd.DataFrame({"Fornecedor": t["fornecedor_nome"].values, "CNPJ": t["fornecedor_doc"].values,
                                     "Contratos de dispensa": t["contratos"].values, "Valor somado": t["valor"].values,
                                     "Objetos (amostra)": t["objetos"].values}),
                       monetarias=["Valor somado"], colunas={"Objetos (amostra)": st.column_config.Column(width="large")})
                st.caption(f"Fornecedores pessoa jurídica com {MIN_DISPENSAS_MESMO_FORNECEDOR} ou mais contratos "
                           "ligados a dispensas por valor (art. 75, I e II) no ano.")
        elif ponto.chave == "prazo":
            with st.expander(f"Ver as {len(a.prazo_curto)} licitações"):
                t = a.prazo_curto
                tabela(pd.DataFrame({"Publicação": data_br(t["data_publicacao"]).values,
                                     "Fim das propostas": data_br(t["data_encerramento"]).values,
                                     "Dias úteis": t["dias_uteis"].astype(int).values, "Modalidade": t["modalidade"].values,
                                     "Objeto": t["objeto"].values, "Valor estimado": t["valor_estimado"].values,
                                     "PNCP": com_link(t).values}),
                       monetarias=["Valor estimado"], colunas={"PNCP": LINK, "Objeto": OBJETO})
                st.caption(f"Dias de segunda a sexta entre a publicação e o fim das propostas; feriados não são "
                           f"descontados, então o prazo real pode ser ainda menor. Mínimo legal: {PRAZO_MINIMO_DIAS_UTEIS} "
                           "dias úteis (compras pelo menor preço) e mais para serviços e obras.")
        elif ponto.chave == "desconto":
            with st.expander(f"Ver as {len(a.sem_desconto)} licitações"):
                t = a.sem_desconto
                tabela(pd.DataFrame({"Publicação": data_br(t["data_publicacao"]).values, "Modalidade": t["modalidade"].values,
                                     "Objeto": t["objeto"].values, "Estimado": t["valor_estimado"].values,
                                     "Homologado": t["valor_homologado"].values, "Desconto": t["desconto"].values,
                                     "PNCP": com_link(t).values}),
                       monetarias=["Estimado", "Homologado"], percentuais=["Desconto"],
                       colunas={"PNCP": LINK, "Objeto": OBJETO})

if not a.contratos_ligados and len(a.contratos):
    st.caption("Os contratos deste ano não trazem o número da contratação de origem, por isso a regra dos "
               "fornecedores com várias dispensas não pôde ser aplicada.")

aba_geral, aba_proc, aba_contr, aba_abertas = st.tabs(
    ["Visão geral", "Licitações e contratações", "Contratos", "Propostas abertas"])
cor = tema()["serie"][0]

# ----------------------------------------------------------------------- visão geral
with aba_geral:
    esq, dir_ = st.columns(2, gap="large")
    with esq:
        st.subheader("Como os órgãos compram")
        por_mod = (validas.groupby("modalidade").agg(valor=("valor_estimado", "sum"), qtd=("id_pncp", "count"))
                   .sort_values("valor"))
        if len(por_mod):
            rotulos = [f"{m} ({q})" for m, q in zip(por_mod.index, por_mod["qtd"])]
            fig = go.Figure()
            fig.add_bar(y=rotulos, x=por_mod["valor"] / 1e6, orientation="h", width=0.55, name="Valor estimado",
                        marker=dict(color=cor, cornerradius=4), cliponaxis=False, textposition="outside",
                        text=[brl_compacto(v) for v in por_mod["valor"]],
                        customdata=[brl(v) for v in por_mod["valor"]], hovertemplate="%{y}: %{customdata}<extra></extra>")
            fig.update_xaxes(title="R$ milhões (valor estimado)", tickformat=",.1f",
                             range=[0, por_mod["valor"].max() / 1e6 * 1.3])
            fig.update_yaxes(title=None)
            mostrar(estilo_grafico(fig, 80 + 46 * len(por_mod), legenda=False), alt=f"Valor estimado por modalidade em {ano}")
            st.caption("Entre parênteses, o número de processos publicados.")
            with st.expander("Ver dados em tabela"):
                t = por_mod.iloc[::-1].reset_index()
                t.columns = ["Modalidade", "Valor estimado", "Processos"]
                tabela(t, monetarias=["Valor estimado"])
    with dir_:
        st.subheader("Publicações por mês")
        meses = datas(a.contratacoes["data_publicacao"]).dt.month.value_counts().sort_index()
        if len(meses):
            fig = go.Figure()
            fig.add_bar(x=[SIGLAS_MES[m] for m in meses.index], y=meses.values, width=0.55, name="Publicações",
                        marker=dict(color=cor, cornerradius=4), hovertemplate="%{x}: %{y} publicações<extra></extra>")
            fig.update_yaxes(title="Contratações publicadas", rangemode="tozero")
            fig.update_xaxes(title=None, categoryorder="array", categoryarray=list(SIGLAS_MES.values()))
            mostrar(estilo_grafico(fig, 300, legenda=False), alt=f"Contratações publicadas por mês em {ano}")

    st.subheader("Maiores fornecedores")
    st.caption("Valor global dos contratos assinados no ano. Pessoas físicas e microempreendedores individuais "
               "aparecem somados numa barra só (LGPD); o nome de cada um está nas tabelas de contratos."
               + (" **Incompleto: a coleta dos contratos ainda não terminou.**" if faltam else ""))
    if len(a.contratos):
        k_ = a.contratos.assign(rotulo=a.contratos["fornecedor_nome"].where(a.contratos["fornecedor_doc"] != "",
                                                                             AGRUPADOS))
        top = k_.groupby("rotulo")["valor_global"].sum().sort_values(ascending=False)
        protegidos = top.pop(AGRUPADOS) if AGRUPADOS in top else None
        top = top.head(10)
        if protegidos is not None:
            top = pd.concat([top, pd.Series({AGRUPADOS: protegidos})])
        top = top.iloc[::-1]
        fig = go.Figure()
        fig.add_bar(y=top.index, x=top.values / 1e6, orientation="h", width=0.55, name="Valor contratado",
                    marker=dict(color=[tema()["apagado"] if n == AGRUPADOS else cor for n in top.index], cornerradius=4),
                    text=[f"{brl_compacto(v)} ({pct(v / total_contratos)})" for v in top.values], textposition="outside",
                    cliponaxis=False, customdata=[brl(v) for v in top.values],
                    hovertemplate="%{y}: %{customdata}<extra></extra>")
        fig.update_xaxes(title="R$ milhões", tickformat=",.1f", range=[0, top.max() / 1e6 * 1.3])
        fig.update_yaxes(title=None)
        mostrar(estilo_grafico(fig, 80 + 40 * len(top), legenda=False), alt=f"Maiores fornecedores em {ano}")
        with st.expander("Ver dados em tabela"):
            t = top.iloc[::-1].rename("Valor contratado").rename_axis("Fornecedor").reset_index()
            t["Participação"] = t["Valor contratado"] / total_contratos
            tabela(t, monetarias=["Valor contratado"], percentuais=["Participação"])
    else:
        st.caption("Nenhum contrato assinado neste ano.")

# ------------------------------------------------------- licitações e contratações
with aba_proc:
    f1, f2 = st.columns([2, 3])
    modalidades = f1.multiselect("Modalidade", sorted(a.contratacoes["modalidade"].unique()), placeholder="Todas")
    busca = f2.text_input("Buscar no objeto", placeholder="ex.: merenda, pavimentação, medicamentos")
    t = a.contratacoes
    if modalidades:
        t = t[t["modalidade"].isin(modalidades)]
    if busca:
        t = t[t["objeto"].map(sem_acento).str.contains(sem_acento(busca), regex=False)]
    t = t.sort_values("data_publicacao", ascending=False)
    t = t.assign(contratado=t["id_pncp"].map(contratados_por_compra(contratos)).fillna(""))
    tabela(pd.DataFrame({"Publicação": data_br(t["data_publicacao"]).values, "Modalidade": t["modalidade"].values,
                         "Objeto": t["objeto"].values, "Órgão": t["orgao_nome"].map(nome_curto).values,
                         "Contratado": t["contratado"].replace("", "–").values, "Situação": t["situacao"].values,
                         "Valor estimado": t["valor_estimado"].values, "Valor homologado": t["valor_homologado"].values,
                         "PNCP": com_link(t).values}),
           monetarias=["Valor estimado", "Valor homologado"], altura=480,
           colunas={"PNCP": LINK, "Objeto": OBJETO, "Contratado": CONTRATADO})
    com_contrato = int((t["contratado"] != "").sum())
    st.caption(md(f"{numero(len(t), 0)} contratações · valor estimado {brl(t['valor_estimado'].fillna(0).sum())} · "
                  f"{numero(com_contrato, 0)} já com contrato publicado no PNCP"
                  + (" (coleta dos contratos incompleta)" if faltam else "")))
    st.download_button("Baixar esta lista (CSV)", t.drop(columns=["publicacao"], errors="ignore")
                       .to_csv(sep=";", decimal=",", index=False).encode("utf-8-sig"),
                       file_name=f"contratacoes_{ano}.csv", mime="text/csv", icon=":material/download:")

# --------------------------------------------------------------------------- contratos
with aba_contr:
    busca_c = st.text_input("Buscar por objeto ou fornecedor", key="busca_contratos",
                            placeholder="ex.: limpeza, construtora")
    t = a.contratos
    if busca_c:
        alvo = (t["objeto"] + " " + t["fornecedor_nome"]).map(sem_acento)
        t = t[alvo.str.contains(sem_acento(busca_c), regex=False)]
    t = t.sort_values("data_assinatura", ascending=False)
    tabela(pd.DataFrame({"Assinatura": data_br(t["data_assinatura"]).values, "Fornecedor": t["fornecedor_nome"].values,
                         "CNPJ": t["fornecedor_doc"].map(cnpj_formatado).values, "Objeto": t["objeto"].values,
                         "Tipo": t["tipo"].values,
                         "Valor global": t["valor_global"].values, "Fim da vigência": data_br(t["vigencia_fim"]).values,
                         "PNCP": com_link(t, contrato=True).values}),
           monetarias=["Valor global"], altura=480, colunas={"PNCP": LINK, "Objeto": OBJETO, "CNPJ": CNPJ})
    st.caption(md(f"{numero(len(t), 0)} contratos · valor global {brl(t['valor_global'].fillna(0).sum())}"))

# ---------------------------------------------------------------------- propostas abertas
with aba_abertas:
    hoje = pd.Timestamp(dt.date.today())
    enc = datas(contratacoes["data_encerramento"])
    abertas = contratacoes[(enc >= hoje) & (contratacoes["situacao_id"] == 1).fillna(False).astype(bool)]
    st.caption("Licitações e chamamentos com prazo de propostas ainda aberto, pela última atualização dos dados. "
               "Confira sempre o edital no PNCP: prazos podem ser alterados.")
    if abertas.empty:
        st.info("Nenhuma proposta com prazo aberto na última atualização.", icon=":material/event_busy:")
    else:
        t = abertas.sort_values("data_encerramento")
        tabela(pd.DataFrame({"Fim das propostas": data_br(t["data_encerramento"]).values,
                             "Modalidade": t["modalidade"].values, "Objeto": t["objeto"].values,
                             "Órgão": t["orgao_nome"].values, "Valor estimado": t["valor_estimado"].values,
                             "PNCP": com_link(t).values}),
               monetarias=["Valor estimado"], colunas={"PNCP": LINK, "Objeto": OBJETO})

with st.expander("Como ler estes números"):
    st.markdown(
        f"""
- **Licitação** (pregão, concorrência): empresas disputam; vence a melhor proposta. **Dispensa** e
  **inexigibilidade** são contratações diretas, sem disputa, permitidas pela Lei 14.133/2021 em casos específicos
  (valor pequeno, emergência, fornecedor exclusivo etc.).
- **Valor estimado** é o que o órgão calculou antes da compra; **homologado**, o resultado da licitação.
- Os dados são os que cada órgão publica no PNCP. Compras publicadas só no portal da transparência ou no
  Diário Oficial podem não aparecer aqui.
- **Contratado** é a empresa do contrato ligado à contratação. A publicação de uma licitação ou dispensa no PNCP
  não traz o vencedor: ele aparece quando o órgão publica o contrato (ou, no registro de preços, a ata, que fica
  no link do PNCP). Por isso parte das linhas fica sem nome.
- Fornecedores pessoa física e microempreendedores individuais (MEI) aparecem com o nome nas tabelas, mas
  sem CPF ou CNPJ, e somados num grupo só nos rankings e nos pontos de atenção, em respeito à Lei Geral de
  Proteção de Dados. A publicação completa continua no PNCP.
- Contratações de órgãos estaduais e federais com sede em {cidade} (universidades, por exemplo) não entram.
"""
    )
st.page_link("paginas/sobre.py", label="Critérios de cada ponto de atenção", icon=":material/info:")
