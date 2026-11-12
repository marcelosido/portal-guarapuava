"""Página "Comparar cidades": mapa do estado e comparação entre dois municípios no último ano fechado.

Fonte: SICONFI – RREO Anexo 14 (6º bimestre), RGF Anexo 1 (Executivo) e Balanço Anual (DCA Anexos I-D e I-E)
enviados por cada prefeitura. Malha municipal: IBGE (via geodata-br, domínio público), simplificada.
"""

from __future__ import annotations

import math

import altair as alt
import pandas as pd
import streamlit as st

from despesas import config
from despesas.comparativo import INDICADORES, INDICADORES_POR_CHAVE, tabela_indicadores
from despesas.formatacao import numero
from despesas.painel import (assinatura, cabecalho, carregar_comparativo, carregar_malha, ler_metadados, md,
                             pasta_dados, tema)

PASTA = pasta_dados()
meta = ler_metadados(PASTA)
comp = meta.get("comparativo", {})
cidade_padrao = config.ID_ENTE
DESCRICAO = ("Escolha duas cidades do Paraná e compare quanto cada prefeitura gastou por habitante em educação, "
             "saúde, transporte e salários, e como ficou nos limites e mínimos da lei. Clique no mapa para "
             "trocar a cidade comparada.")

dados, lista = carregar_comparativo(str(PASTA), assinatura(PASTA / "fComparativo.csv"))
if dados.empty or lista.empty:
    cabecalho("Comparar cidades", DESCRICAO)
    st.info("A comparação entre cidades ainda não foi coletada. Na primeira vez, o robô precisa de uma ou duas "
            "execuções para buscar os relatórios dos 399 municípios.", icon=":material/schedule:")
    st.stop()

anos = sorted({int(a) for a in dados["ano"].unique()}, reverse=True)
if len(anos) > 1:
    ano = cabecalho("Comparar cidades", DESCRICAO, seletor=lambda c: c.selectbox("Ano", anos, help="Ano fechado"))
else:
    cabecalho("Comparar cidades", DESCRICAO)
    ano = anos[0]

tab = tabela_indicadores(dados, lista, ano)
chaves = [i["chave"] for i in INDICADORES]
tab = tab.set_index("cod_ibge")
com_dado = tab[tab[chaves].notna().any(axis=1)]
atualizado = pd.Timestamp(comp["coletado_em"]).strftime("%d/%m/%Y") if comp.get("coletado_em") else "–"
st.caption(md(f"Fonte: Tesouro Nacional (SICONFI) – RREO, RGF e Balanço Anual (DCA) de {ano} enviados por cada "
              f"prefeitura · {len(com_dado)} de {len(tab)} municípios com dados · atualizado em {atualizado}"))
if comp.get("url_api") and comp["url_api"] != config.URL_OFICIAL:
    st.warning(f"Estes dados vieram de `{comp['url_api']}`, não da API oficial do SICONFI. Servem só para "
               "demonstração.", icon=":material/science:")
if comp.get("status") == "parcial" and len(com_dado) < len(tab):
    st.info(f"A coleta ainda está em andamento: {len(tab) - len(com_dado)} municípios entram nas próximas "
            "atualizações.", icon=":material/hourglass_top:")

T = tema()
COR_A, COR_B = T["serie"][0], T["serie"][1]
nomes = tab["municipio"].to_dict()
codigos = com_dado.index.tolist() or tab.index.tolist()
codigos = sorted(codigos, key=lambda c: nomes.get(c, ""))


def fmt(valor: float | None, unidade: str) -> str:
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "sem dado"
    return f"R$ {numero(valor, 0)}" if unidade == "R$/hab" else f"{numero(valor, 1)}%"


def posicao(serie: pd.Series, cod: str) -> str:
    validos = serie.dropna()
    if cod not in validos.index:
        return "–"
    return f"{int(validos.rank(ascending=False, method='min')[cod])}º de {len(validos)}"


# ---- clique no mapa: troca a cidade comparada (antes de desenhar os seletores)
clique = st.session_state.get("mapa_pr")
try:
    selecionados = clique["selection"]["cidade"] if clique else []
except (KeyError, TypeError):
    selecionados = []
if selecionados:
    cod_clicado = str(selecionados[0].get("cod", ""))
    if cod_clicado and cod_clicado != st.session_state.get("_ultimo_clique") and cod_clicado in codigos:
        st.session_state["cmp_outra"] = cod_clicado
    st.session_state["_ultimo_clique"] = cod_clicado

if st.session_state.get("cmp_minha") not in codigos:
    st.session_state["cmp_minha"] = cidade_padrao if cidade_padrao in codigos else codigos[0]
if st.session_state.get("cmp_outra") not in codigos:
    pop = pd.to_numeric(tab["populacao"], errors="coerce")
    alvo = pop.get(st.session_state["cmp_minha"], float("nan"))
    candidatos = (pop.loc[codigos].drop(st.session_state["cmp_minha"], errors="ignore") - alvo).abs().dropna()
    st.session_state["cmp_outra"] = candidatos.idxmin() if len(candidatos) else codigos[-1]

c1, c2, c3 = st.columns(3)
minha = c1.selectbox("Sua cidade", codigos, format_func=lambda c: nomes.get(c, c), key="cmp_minha")
outra = c2.selectbox("Comparar com", codigos, format_func=lambda c: nomes.get(c, c), key="cmp_outra",
                     help="Também dá para escolher clicando no mapa.")
opcoes = [i["chave"] for i in INDICADORES if tab[i["chave"]].notna().any()] or chaves
indicador = c3.selectbox("Colorir o mapa por", opcoes, key="cmp_indicador",
                         format_func=lambda k: INDICADORES_POR_CHAVE[k]["nome"])
info = INDICADORES_POR_CHAVE[indicador]
nome_a, nome_b = nomes.get(minha, minha), nomes.get(outra, outra)

# ---------------------------------------------------------------------------------- mapa
serie = pd.to_numeric(tab[indicador], errors="coerce")
validos = serie.dropna()
faixas: list[str] = []
classe = pd.Series(index=tab.index, dtype=object)
if len(validos) >= 5:
    quantis = pd.qcut(validos.rank(method="first"), 5, labels=False)
    limites = [validos[quantis == q].agg(["min", "max"]) for q in range(5)]
    faixas = [f"{fmt(lim['min'], info['unidade'])} a {fmt(lim['max'], info['unidade'])}" for lim in limites]
    classe.loc[validos.index] = [faixas[int(q)] for q in quantis]
elif len(validos):
    faixas = ["Com dado"]
    classe.loc[validos.index] = "Com dado"


def centro(geometria: dict) -> tuple[float, float]:
    anel = geometria["coordinates"][0] if geometria["type"] == "Polygon" else geometria["coordinates"][0][0]
    xs, ys = zip(*anel[:-1])
    return sum(xs) / len(xs), sum(ys) / len(ys)


malha = carregar_malha()
feicoes, centros = [], {}
for f in malha["features"]:
    cod = f["properties"]["id"]
    centros[cod] = centro(f["geometry"])
    v = serie.get(cod, float("nan"))
    feicoes.append({"type": "Feature", "geometry": f["geometry"], "properties": {
        "cod": cod, "nome": f["properties"]["name"], "faixa": classe.get(cod) if isinstance(classe.get(cod), str) else "Sem dado",
        "valor": fmt(v, info["unidade"]), "posicao": posicao(serie, cod)}})

ordem_faixas = faixas + ["Sem dado"]
cores_faixas = (T["sequencial"][: len(faixas)] if len(faixas) == 5 else [T["serie"][0]] * len(faixas)) + [T["sem_dado"]]
clicavel = alt.selection_point(fields=["cod"], name="cidade", on="click", clear=False)
base = alt.Chart(alt.Data(values=feicoes)).transform_calculate(
    cod="datum.properties.cod", nome="datum.properties.nome", faixa="datum.properties.faixa",
    valor="datum.properties.valor", posicao="datum.properties.posicao")
poligonos = base.mark_geoshape(stroke=T["superficie"], strokeWidth=0.4).encode(
    color=alt.Color("faixa:N", scale=alt.Scale(domain=ordem_faixas, range=cores_faixas),
                    legend=alt.Legend(title=info["nome"], orient="bottom", direction="vertical", columns=2,
                                      labelLimit=260, titleLimit=420, symbolType="square")),
    tooltip=[alt.Tooltip("nome:N", title="Município"), alt.Tooltip("valor:N", title=info["unidade"]),
             alt.Tooltip("posicao:N", title="Posição")],
).add_params(clicavel)
destaque = base.mark_geoshape(fill=None, stroke=T["tinta"], strokeWidth=1.6).transform_filter(
    alt.FieldOneOfPredicate(field="cod", oneOf=[minha, outra]))
marcas = pd.DataFrame([{"lon": centros[c][0], "lat": centros[c][1], "nome": nomes.get(c, c), "quem": q}
                       for c, q in ((minha, "Sua cidade"), (outra, "Comparada")) if c in centros])
pontos = alt.Chart(marcas).mark_circle(size=110, stroke=T["superficie"], strokeWidth=2, opacity=1).encode(
    longitude="lon:Q", latitude="lat:Q",
    color=alt.Color("quem:N", scale=alt.Scale(domain=["Sua cidade", "Comparada"], range=[COR_A, COR_B]), legend=None),
    tooltip=[alt.Tooltip("nome:N", title="Município")])
rotulos = alt.Chart(marcas).mark_text(dy=-13, fontSize=12, fontWeight="bold", color=T["tinta"]).encode(
    longitude="lon:Q", latitude="lat:Q", text="nome:N")
mapa = (alt.layer(poligonos, destaque, pontos, rotulos)
        .project(type="mercator")
        .properties(height=470)
        .resolve_scale(color="independent"))

esq, dir_ = st.columns([3, 2], gap="large")
with esq:
    st.altair_chart(mapa, on_select="rerun", selection_mode="cidade", key="mapa_pr", width="stretch")
    st.caption(md(f"Cores em cinco faixas com o mesmo número de municípios. Contorno: {nome_a} e {nome_b}. "
                  "Clique numa cidade para compará-la."))

with dir_:
    st.subheader(f"{nome_a} × {nome_b}")
    pop_a, pop_b = (pd.to_numeric(tab.loc[c, "populacao"], errors="coerce") if c in tab.index else None
                    for c in (minha, outra))
    st.markdown(f":blue-badge[:material/location_on: {nome_a}] {numero(pop_a, 0) if pop_a == pop_a else '–'} habitantes  \n"
                f":orange-badge[:material/location_on: {nome_b}] {numero(pop_b, 0) if pop_b == pop_b else '–'} habitantes")
    linhas = []
    for item in INDICADORES:
        s = pd.to_numeric(tab[item["chave"]], errors="coerce")
        linhas.append({"Indicador": item["curto"],
                       nome_a: fmt(s.get(minha), item["unidade"]),
                       nome_b: fmt(s.get(outra), item["unidade"]),
                       "Mediana do PR": fmt(s.median() if s.notna().any() else None, item["unidade"])})
    resumo = pd.DataFrame(linhas)
    if nome_a == nome_b:
        resumo = resumo.loc[:, ~resumo.columns.duplicated()]
    st.dataframe(resumo, hide_index=True, height=35 * (len(resumo) + 1) + 3)
    st.caption("Mediana: metade dos municípios do Paraná fica abaixo desse valor e metade acima.")

# ------------------------------------------------------- régua: onde cada cidade fica
st.subheader("Onde cada cidade fica entre os municípios do Paraná")
st.caption("Cada ponto cinza é um município. A linha tracejada marca a mediana do estado: metade dos municípios "
           "fica abaixo dela e metade acima. Posição: 1º é o maior valor do estado.")


def regua(item: dict) -> alt.Chart | None:
    """Faixa com todos os municípios (pontos cinza), a mediana e as duas cidades escolhidas."""
    s = pd.to_numeric(tab[item["chave"]], errors="coerce").dropna()
    if s.empty:
        return None
    df = pd.DataFrame({"cod": s.index, "valor": s.values, "nome": [nomes.get(c, c) for c in s.index]})
    df["y"] = [0.15 + 0.7 * (int(c) * 7919 % 1000) / 1000 for c in df["cod"]]  # espalha os pontos na vertical
    df["texto"] = [fmt(v, item["unidade"]) for v in df["valor"]]
    reais = item["unidade"] == "R$/hab"
    eixo = alt.Axis(title=None, grid=False, tickCount=5, labelExpr=(
        "'R$ ' + replace(format(datum.value, ',.0f'), /,/g, '.')" if reais else "format(datum.value, '.0f') + '%'"))
    x = alt.X("valor:Q", axis=eixo, scale=alt.Scale(zero=False, nice=True))
    y = alt.Y("y:Q", axis=None, scale=alt.Scale(domain=[0, 1]))
    dica = [alt.Tooltip("nome:N", title="Município"), alt.Tooltip("texto:N", title=item["unidade"])]
    camadas = [alt.Chart(df).mark_circle(size=20, color=T["apagado"], opacity=0.4).encode(x=x, y=y, tooltip=dica)]
    camadas.append(alt.Chart(pd.DataFrame({"valor": [s.median()]}))
                   .mark_rule(strokeDash=[4, 3], color=T["tinta2"], strokeWidth=1).encode(x=x))
    if item.get("referencia"):
        ref = pd.DataFrame({"valor": [item["referencia"][0]], "rotulo": [item["referencia"][1]], "y": [1.0]})
        camadas.append(alt.Chart(ref).mark_rule(color=T["apagado"], strokeWidth=1).encode(x=x))
        camadas.append(alt.Chart(ref).mark_text(align="left", baseline="top", dx=3, fontSize=10, color=T["tinta2"])
                       .encode(x=x, y=y, text="rotulo:N"))
    escolhidos = df[df["cod"].isin([minha, outra])].assign(
        quem=lambda d: d["cod"].map({minha: "Sua cidade", outra: "Comparada"}), y=0.5)
    if len(escolhidos):
        cor = alt.Color("quem:N", scale=alt.Scale(domain=["Sua cidade", "Comparada"], range=[COR_A, COR_B]), legend=None)
        camadas.append(alt.Chart(escolhidos).mark_circle(size=170, opacity=1, stroke=T["superficie"], strokeWidth=2)
                       .encode(x=x, y=y, color=cor, tooltip=dica))
    return alt.layer(*camadas).properties(height=80)


itens = [i for i in INDICADORES if tab[i["chave"]].notna().any()]
for par in range(0, len(itens), 2):
    colunas = st.columns(2, gap="large")
    for coluna, item in zip(colunas, itens[par: par + 2]):
        with coluna.container(border=True):
            s = pd.to_numeric(tab[item["chave"]], errors="coerce")
            st.markdown(f"**{item['nome']}**")
            st.markdown(md(f":blue-badge[{nome_a}] {fmt(s.get(minha), item['unidade'])} · {posicao(s, minha)}  \n"
                           f":orange-badge[{nome_b}] {fmt(s.get(outra), item['unidade'])} · {posicao(s, outra)}"))
            grafico = regua(item)
            if grafico is not None:
                st.altair_chart(grafico, width="stretch")

with st.expander("Como comparar com cuidado"):
    st.markdown(
        f"""
- **Por habitante** divide a despesa liquidada no ano pela população que o próprio município informou no
  relatório (estimativa do IBGE). Cidades pequenas costumam ter gasto por habitante maior: há custos fixos.
- **Funções de governo** (educação, saúde, transporte...) seguem a classificação de cada prefeitura. Um mesmo
  gasto pode estar em funções diferentes: transporte escolar, por exemplo, às vezes fica em Educação.
- **% da receita de impostos** são os mínimos da Constituição (25% em educação e 15% em saúde), apurados pelo
  próprio município no RREO. **Salários e encargos** é a despesa total com pessoal da prefeitura (sem a
  Câmara), em % da receita corrente líquida, como na Lei de Responsabilidade Fiscal (limite de 54%).
- Valores do ano de {ano}, como publicados, sem correção pela inflação. Municípios que não entregaram algum
  relatório aparecem em cinza.
"""
    )
