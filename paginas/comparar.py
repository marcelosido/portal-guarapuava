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


def com_posicao(serie: pd.Series, cod: str, unidade: str) -> str:
    """Valor e posição no estado, para a tabela resumo: "R$ 1.248 · 368º"."""
    validos = serie.dropna()
    if cod not in validos.index:
        return "sem dado"
    return f"{fmt(validos[cod], unidade)} · {int(validos.rank(ascending=False, method='min')[cod])}º"


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
                       nome_a: com_posicao(s, minha, item["unidade"]),
                       nome_b: com_posicao(s, outra, item["unidade"]),
                       "Mediana PR": fmt(s.median() if s.notna().any() else None, item["unidade"])})
    resumo = pd.DataFrame(linhas)
    if nome_a == nome_b:
        resumo = resumo.loc[:, ~resumo.columns.duplicated()]
    largura_cidade = st.column_config.Column(width=118)
    st.dataframe(resumo, hide_index=True, height=35 * (len(resumo) + 1) + 3,
                 column_config={"Indicador": st.column_config.Column(width=150, pinned=True),
                                nome_a: largura_cidade, nome_b: largura_cidade,
                                "Mediana PR": st.column_config.Column(width=84)})
    st.caption("Ao lado de cada valor, a posição no Paraná (1º é o maior). Mediana: metade dos municípios fica "
               "abaixo desse valor e metade acima.")

# ------------------------------------------------------- ranking: onde cada cidade fica
st.subheader("Onde cada cidade fica no ranking do Paraná")
st.caption("Cada faixa vai do 1º lugar (maior valor do estado, à esquerda) ao último (menor valor, à direita), "
           "dividida em cinco partes com o mesmo número de municípios, nas mesmas cores do mapa. A bolinha azul é a "
           "sua cidade (nome em cima) e a laranja, a comparada (nome embaixo); passe o mouse para ver os valores.")


def faixa_do_ranking(posicao_: int, total: int) -> str:
    """Frase curta sobre a posição: 1º, entre os 10%/25% maiores ou menores, acima ou abaixo da mediana."""
    if posicao_ == 1:
        return "maior valor do PR"
    if posicao_ == total:
        return "menor valor do PR"
    topo, base = posicao_ / total, (total - posicao_ + 1) / total
    for corte in (0.10, 0.25):
        if topo <= corte:
            return f"entre os {corte:.0%} maiores"
        if base <= corte:
            return f"entre os {corte:.0%} menores"
    return "acima da mediana" if posicao_ <= total / 2 else "abaixo da mediana"


def linha_cidade(cor: str, nome: str, serie: pd.Series, cod: str, unidade: str) -> str:
    validos = serie.dropna()
    if cod not in validos.index:
        return f":{cor}-badge[{nome}] sem dado"
    pos = int(validos.rank(ascending=False, method="min")[cod])
    return (f":{cor}-badge[{nome}] **{pos}º** de {len(validos)} · {fmt(validos[cod], unidade)} · "
            f"{faixa_do_ranking(pos, len(validos))}")


NOMES_FAIXA = ["20% maiores", "2ª faixa", "faixa do meio", "4ª faixa", "20% menores"]


def ranking(item: dict) -> tuple[alt.LayerChart | None, str]:
    """Faixa do 1º ao último lugar, em cinco partes, com as duas cidades marcadas na posição de cada uma.

    Devolve o gráfico e uma frase sobre o limite ou mínimo legal (quantos municípios ficam do lado de fora).
    """
    s = pd.to_numeric(tab[item["chave"]], errors="coerce").dropna()
    if s.empty:
        return None, ""
    n, unidade = len(s), item["unidade"]
    ordem = s.sort_values(ascending=False, kind="stable")
    rank = s.rank(ascending=False, method="min").astype(int)
    rampa = T["sequencial"]  # do menor para o maior valor (mesmas cores do mapa)
    partes = 5 if n >= 5 else 1
    cortes = [round(k * n / partes) for k in range(partes + 1)]
    segmentos = []
    for k in range(partes):
        fatia = ordem.iloc[cortes[k]: cortes[k + 1]]
        if fatia.empty:
            continue
        segmentos.append({"x0": cortes[k] + 0.5 + (0.004 * n if k else 0), "x1": cortes[k + 1] + 0.5,
                          "faixa": NOMES_FAIXA[k] if partes == 5 else "todos",
                          "de_ate": f"{fmt(fatia.max(), unidade)} a {fmt(fatia.min(), unidade)}",
                          "cor": rampa[partes - 1 - k] if partes == 5 else T["serie"][0],
                          "posicoes": f"{cortes[k] + 1}º a {cortes[k + 1]}º"})
    seg = pd.DataFrame(segmentos)
    escala_x = alt.Scale(domain=[0.5, n + 0.5], nice=False, zero=False)
    escala_y = alt.Scale(domain=[-2.5, 2.0], nice=False)
    camadas = [alt.Chart(seg).mark_rect(cornerRadius=4).encode(
        x=alt.X("x0:Q", scale=escala_x, axis=None), x2="x1:Q",
        y=alt.datum(-0.45, scale=escala_y, axis=None), y2=alt.datum(0.45),
        color=alt.Color("cor:N", scale=None),
        tooltip=[alt.Tooltip("faixa:N", title="Faixa"), alt.Tooltip("posicoes:N", title="Posições"),
                 alt.Tooltip("de_ate:N", title="Valores")])]
    mediana = float(s.median())
    rodape = pd.DataFrame([
        {"x": 0.5, "texto": "1º", "alinha": "left"},
        {"x": (n + 1) / 2, "texto": f"mediana {fmt(mediana, unidade)}", "alinha": "center"},
        {"x": n + 0.5, "texto": f"{n}º", "alinha": "right"},
    ])
    for alinha in ("left", "center", "right"):
        camadas.append(alt.Chart(rodape[rodape["alinha"] == alinha]).mark_text(
            align=alinha, baseline="top", fontSize=11, color=T["tinta2"]).encode(
            x="x:Q", y=alt.datum(-1.85), text="texto:N"))
    frase = ""
    if item.get("referencia"):
        valor_ref, rotulo_ref = item["referencia"]
        limite = rotulo_ref.startswith("limite")
        fora = int((s > valor_ref).sum()) if limite else int((s < valor_ref).sum())
        corte_ref = (fora if limite else n - fora) + 0.5
        if 0 < fora < n:
            camadas.append(alt.Chart(pd.DataFrame({"x": [corte_ref]})).mark_rule(
                color=T["tinta"], strokeWidth=1.5, strokeDash=[3, 2]).encode(x="x:Q", y=alt.datum(-0.75),
                                                                           y2=alt.datum(0.75)))
        regra = f"{'limite' if limite else 'mínimo'} de {numero(valor_ref, 0)}%"
        frase = (f"{fora} {'município passou' if fora == 1 else 'municípios passaram'} do {regra} "
                 "(à esquerda da linha tracejada)." if limite else
                 f"{fora} {'município ficou' if fora == 1 else 'municípios ficaram'} abaixo do {regra} "
                 "(à direita da linha tracejada).") if fora else f"Nenhum município fora do {regra}."
    marcas = []
    # a cidade comparada é desenhada primeiro, para a sua cidade ficar por cima quando as duas estão juntas
    for cod, quem, y_rotulo, base in ((outra, "Comparada", -0.95, "top"), (minha, "Sua cidade", 0.95, "bottom")):
        if cod in s.index and not (quem == "Comparada" and outra == minha):
            pos_graf = int(ordem.index.get_loc(cod)) + 1
            fracao = pos_graf / n
            marcas.append({"pos": pos_graf, "quem": quem, "nome": nomes.get(cod, cod), "texto": fmt(s[cod], unidade),
                           "lugar": f"{rank[cod]}º de {n}", "marca": f"{nomes.get(cod, cod)} · {rank[cod]}º",
                           "y_rotulo": y_rotulo, "base": base,
                           "alinha": "right" if fracao > 0.75 else ("left" if fracao < 0.25 else "center")})
    if marcas:
        m = pd.DataFrame(marcas)
        cor = alt.Color("quem:N", scale=alt.Scale(domain=["Sua cidade", "Comparada"], range=[COR_A, COR_B]),
                        legend=None)
        dica = [alt.Tooltip("nome:N", title="Município"), alt.Tooltip("texto:N", title="Valor"),
                alt.Tooltip("lugar:N", title="Posição")]
        camadas.append(alt.Chart(m).mark_circle(size=190, opacity=1, stroke=T["superficie"], strokeWidth=2.5)
                       .encode(x="pos:Q", y=alt.datum(0), color=cor, tooltip=dica))
        # rótulo em tinta de texto (a cor fica na bolinha); sua cidade em cima, a comparada embaixo
        for (base, alinha), parte in m.groupby(["base", "alinha"]):
            camadas.append(alt.Chart(parte).mark_text(baseline=base, align=alinha, fontSize=12, fontWeight="bold",
                                                      color=T["tinta"])
                           .encode(x="pos:Q", y="y_rotulo:Q", text="marca:N"))
    return alt.layer(*camadas).properties(height=104), frase


itens = [i for i in INDICADORES if tab[i["chave"]].notna().any()]
total_com_dado = len(com_dado)
for par in range(0, len(itens), 2):
    colunas = st.columns(2, gap="large")
    for coluna, item in zip(colunas, itens[par: par + 2]):
        with coluna.container(border=True):
            s = pd.to_numeric(tab[item["chave"]], errors="coerce")
            st.markdown(f"**{item['nome']}**")
            st.markdown(md(linha_cidade("blue", nome_a, s, minha, item["unidade"]) + "  \n"
                           + linha_cidade("orange", nome_b, s, outra, item["unidade"])))
            grafico, frase = ranking(item)
            if grafico is not None:
                st.altair_chart(grafico, width="stretch")
            if frase:
                st.caption(frase)
            if s.notna().sum() < 0.9 * total_com_dado:
                st.caption(f"Só {s.notna().sum()} dos {total_com_dado} municípios informaram este dado no "
                           f"relatório de {ano}.")

with st.expander("Ranking completo", icon=":material/format_list_numbered:"):
    escolhido = st.selectbox("Indicador", [i["chave"] for i in itens], key="cmp_ranking",
                             format_func=lambda k: INDICADORES_POR_CHAVE[k]["nome"],
                             index=[i["chave"] for i in itens].index(indicador) if indicador in
                             [i["chave"] for i in itens] else 0)
    item_r = INDICADORES_POR_CHAVE[escolhido]
    s_r = pd.to_numeric(tab[escolhido], errors="coerce").dropna()
    reais_r = item_r["unidade"] == "R$/hab"
    coluna_valor = "Valor (R$ por habitante)" if reais_r else "Valor (%)"
    tabela_r = pd.DataFrame({"Posição": s_r.rank(ascending=False, method="min").astype(int),
                             "Município": [nomes.get(c, c) for c in s_r.index],
                             coluna_valor: s_r.round(0 if reais_r else 1).values,
                             "Destaque": ["Sua cidade" if c == minha else ("Comparada" if c == outra else "")
                                          for c in s_r.index]},
                            index=s_r.index).sort_values(["Posição", "Município"])
    st.dataframe(tabela_r, hide_index=True, height=420,
                 column_config={"Posição": st.column_config.NumberColumn(format="%dº", width=90),
                                coluna_valor: st.column_config.NumberColumn(format="localized")})
    st.caption("1º é o maior valor do estado. Empates ficam na mesma posição. Use a lupa da tabela para "
               "procurar uma cidade.")

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
