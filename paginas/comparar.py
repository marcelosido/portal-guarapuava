"""Página "Comparar cidades": mapa do estado e comparação entre dois municípios no último ano fechado.

Medida principal de cada área: o peso no orçamento (de cada R$ 100 gastos no ano, quanto foi para a área). O gasto
por habitante aparece como dado secundário. A comparação pode ser com todo o Paraná ou só com cidades do mesmo porte.

Fonte: SICONFI – RREO Anexo 14 (6º bimestre), RGF Anexo 1 (Executivo) e Balanço Anual (DCA Anexos I-D e I-E)
enviados por cada prefeitura. Malha municipal: IBGE (via geodata-br, domínio público), simplificada.
"""

from __future__ import annotations

import math

import altair as alt
import pandas as pd
import streamlit as st

from despesas import config
from despesas.comparativo import (INDICADORES, INDICADORES_POR_CHAVE, SECUNDARIOS, cidades_do_mesmo_porte,
                                  tabela_indicadores)
from despesas.formatacao import numero
from despesas.painel import (assinatura, cabecalho, carregar_comparativo, carregar_malha, ler_metadados, md,
                             pasta_dados, tema)

PASTA = pasta_dados()
meta = ler_metadados(PASTA)
comp = meta.get("comparativo", {})
cidade_padrao = config.ID_ENTE
TODO_PR, MESMO_PORTE = "Todo o Paraná", "Cidades do mesmo porte"
DESCRICAO = ("Escolha duas cidades do Paraná e veja quanto do orçamento cada prefeitura destinou a educação, saúde, "
             "transporte e investimentos, e como ficou nos limites e mínimos da lei. Compare com todo o estado ou só "
             "com cidades do mesmo porte; clique no mapa para trocar a cidade comparada.")

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
populacao = pd.to_numeric(tab["populacao"], errors="coerce")


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
    """Valor e posição no grupo, para a tabela resumo: "26,4% · 10º"."""
    validos = serie.dropna()
    if cod not in validos.index:
        return "sem dado"
    return f"{fmt(validos[cod], unidade)} · {int(validos.rank(ascending=False, method='min')[cod])}º"


def mais_perto(cod: str, candidatos: list[str]) -> str:
    """A cidade de população mais parecida com `cod` (em proporção), para ser a comparada."""
    outras = [c for c in candidatos if c != cod]
    if not outras:
        return cod
    alvo = populacao.get(cod)
    if alvo is None or pd.isna(alvo):
        return outras[0]
    return min(outras, key=lambda c: abs(math.log(populacao.get(c) or 1) - math.log(alvo)))


# ---- estado da página: sua cidade, grupo de comparação e cidade comparada (antes de desenhar os seletores).
# O Streamlit já guarda em st.session_state o que a pessoa escolheu, então o grupo é calculado antes dos seletores.
if st.session_state.get("cmp_minha") not in codigos:
    st.session_state["cmp_minha"] = cidade_padrao if cidade_padrao in codigos else codigos[0]
if st.session_state.get("cmp_escopo") not in (TODO_PR, MESMO_PORTE):
    st.session_state["cmp_escopo"] = TODO_PR
minha_atual = st.session_state["cmp_minha"]
if st.session_state["cmp_escopo"] == MESMO_PORTE:
    grupo, sobre_grupo = cidades_do_mesmo_porte(populacao.loc[codigos], minha_atual)
else:
    grupo, sobre_grupo = codigos, f"os {len(codigos)} municípios do Paraná com dados"
grupo = sorted(grupo, key=lambda c: nomes.get(c, ""))
no_grupo = set(grupo)
NO_PR = st.session_state["cmp_escopo"] == TODO_PR
ONDE = "no Paraná" if NO_PR else "entre as cidades do mesmo porte"
REF = "do PR" if NO_PR else "do grupo"

# ---- clique no mapa: troca a cidade comparada (só dentro do grupo)
clique = st.session_state.get("mapa_pr")
try:
    selecionados = clique["selection"]["cidade"] if clique else []
except (KeyError, TypeError):
    selecionados = []
if selecionados:
    cod_clicado = str(selecionados[0].get("cod", ""))
    if cod_clicado and cod_clicado != st.session_state.get("_ultimo_clique"):
        if cod_clicado in no_grupo:
            st.session_state["cmp_outra"] = cod_clicado
        elif cod_clicado in nomes:
            st.toast(f"{nomes[cod_clicado]} não é do mesmo porte de {nomes.get(minha_atual)}. Para compará-la, "
                     f"escolha \"{TODO_PR}\".", icon=":material/info:")
    st.session_state["_ultimo_clique"] = cod_clicado
if st.session_state.get("cmp_outra") not in no_grupo:
    st.session_state["cmp_outra"] = mais_perto(minha_atual, grupo)

c1, c2, c3 = st.columns(3)
minha = c1.selectbox("Sua cidade", codigos, format_func=lambda c: nomes.get(c, c), key="cmp_minha")
outra = c2.selectbox("Comparar com", grupo, format_func=lambda c: nomes.get(c, c), key="cmp_outra",
                     help="Também dá para escolher clicando no mapa.")
c3.radio("Comparar entre", [TODO_PR, MESMO_PORTE], key="cmp_escopo", horizontal=True,
         help="Mesmo porte = cidades na mesma faixa de população: até 20 mil, 20 a 50 mil, 50 a 100 mil, "
              "100 a 900 mil ou mais de 900 mil habitantes.")
st.caption(md(f"Posições e medianas calculadas entre {sobre_grupo}."))
nome_a, nome_b = nomes.get(minha, minha), nomes.get(outra, outra)


def serie_do_grupo(chave: str) -> pd.Series:
    """Valores do indicador só para as cidades do grupo de comparação."""
    return pd.to_numeric(tab.loc[grupo, chave], errors="coerce") if chave in tab else pd.Series(dtype=float)


opcoes = [i["chave"] for i in INDICADORES if serie_do_grupo(i["chave"]).notna().any()] or chaves
# ---------------------------------------------------------------------------------- mapa
esq, dir_ = st.columns([5, 4], gap="large")
indicador = esq.selectbox("Colorir o mapa por", opcoes, key="cmp_indicador",
                          format_func=lambda k: INDICADORES_POR_CHAVE[k]["nome"])
info = INDICADORES_POR_CHAVE[indicador]
serie = serie_do_grupo(indicador)
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
    if cod in no_grupo:
        faixa = classe.get(cod) if isinstance(classe.get(cod), str) else "Sem dado"
        valor, lugar = fmt(serie.get(cod, float("nan")), info["unidade"]), posicao(serie, cod)
    else:
        faixa, valor, lugar = "Fora do grupo", "–", "fora do grupo"
    feicoes.append({"type": "Feature", "geometry": f["geometry"], "properties": {
        "cod": cod, "nome": f["properties"]["name"], "faixa": faixa, "valor": valor, "posicao": lugar}})

ordem_faixas = faixas + ["Sem dado"] + ([] if NO_PR else ["Fora do grupo"])
cores_faixas = ((T["sequencial"][: len(faixas)] if len(faixas) == 5 else [T["serie"][0]] * len(faixas))
                + [T["sem_dado"]] + ([] if NO_PR else [T["fora"]]))
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

with esq:
    st.altair_chart(mapa, on_select="rerun", selection_mode="cidade", key="mapa_pr", width="stretch")
    st.caption(md(f"Cores em cinco faixas com o mesmo número de municípios {ONDE}. Contorno: {nome_a} e {nome_b}. "
                  "Clique numa cidade para compará-la."))

with dir_:
    st.subheader(f"{nome_a} × {nome_b}")
    pop_a, pop_b = (pd.to_numeric(tab.loc[c, "populacao"], errors="coerce") if c in tab.index else None
                    for c in (minha, outra))
    st.markdown(f":blue-badge[:material/location_on: {nome_a}] {numero(pop_a, 0) if pop_a == pop_a else '–'} habitantes  \n"
                f":orange-badge[:material/location_on: {nome_b}] {numero(pop_b, 0) if pop_b == pop_b else '–'} habitantes")
    coluna_mediana = "Mediana"
    linhas = []
    for item in INDICADORES:
        s = serie_do_grupo(item["chave"])
        linhas.append({"Indicador": item["curto"],
                       nome_a: com_posicao(s, minha, item["unidade"]),
                       nome_b: com_posicao(s, outra, item["unidade"]),
                       coluna_mediana: fmt(s.median() if s.notna().any() else None, item["unidade"])})
    resumo = pd.DataFrame(linhas)
    if nome_a == nome_b:
        resumo = resumo.loc[:, ~resumo.columns.duplicated()]
    largura_cidade = st.column_config.Column(width=102)
    st.dataframe(resumo, hide_index=True, height=35 * (len(resumo) + 1) + 3,
                 column_config={"Indicador": st.column_config.Column(width=168, pinned=True),
                                nome_a: largura_cidade, nome_b: largura_cidade,
                                coluna_mediana: st.column_config.Column(width=74)})
    st.caption(f"Ao lado de cada valor, a posição {ONDE} (1º é o maior). \"% do gasto\" é o peso no orçamento: "
               "de cada R$ 100 gastos no ano, quanto foi para a área. Mediana " + ("do Paraná" if NO_PR else "do grupo")
               + ": metade das cidades fica abaixo desse valor e metade acima.")

# ------------------------------------------------------- ranking: onde cada cidade fica
st.subheader("Onde cada cidade fica no ranking " + ("do Paraná" if NO_PR else "das cidades do mesmo porte"))
st.caption("Cada faixa vai do 1º lugar (maior valor, à esquerda) ao último (menor valor, à direita), dividida em "
           "cinco partes com o mesmo número de cidades, nas mesmas cores do mapa. A bolinha azul é a sua cidade (nome "
           "em cima) e a laranja, a comparada (nome embaixo); passe o mouse para ver os valores. Embaixo de cada "
           "faixa, o gasto por habitante da área, como dado de apoio.")


def faixa_do_ranking(posicao_: int, total: int) -> str:
    """Frase curta sobre a posição: 1º, entre os 10%/25% maiores ou menores, acima ou abaixo da mediana."""
    if posicao_ == 1:
        return f"maior valor {REF}"
    if posicao_ == total:
        return f"menor valor {REF}"
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

    Devolve o gráfico e uma frase sobre o limite ou mínimo legal (quantas cidades ficam do lado de fora).
    """
    s = serie_do_grupo(item["chave"]).dropna()
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
        frase = (f"{fora} {'cidade passou' if fora == 1 else 'cidades passaram'} do {regra} "
                 "(à esquerda da linha tracejada)." if limite else
                 f"{fora} {'cidade ficou' if fora == 1 else 'cidades ficaram'} abaixo do {regra} "
                 "(à direita da linha tracejada).") if fora else f"Nenhuma cidade fora do {regra}."
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


def linha_por_habitante(item: dict) -> str:
    """Dado secundário: o gasto por habitante da área, com a posição no mesmo grupo."""
    if not item.get("secundario"):
        return ""
    s2 = serie_do_grupo(item["secundario"]).dropna()
    partes = [f"{nome} {fmt(s2[cod], 'R$/hab')} ({int(s2.rank(ascending=False, method='min')[cod])}º)"
              for cod, nome in ((minha, nome_a), (outra, nome_b)) if cod in s2.index and not (cod == outra == minha)]
    return (":material/person: Por habitante: " + " · ".join(partes)) if partes else ""


itens = [i for i in INDICADORES if serie_do_grupo(i["chave"]).notna().any()]
total_com_dado = len(grupo)
for par in range(0, len(itens), 2):
    colunas = st.columns(2, gap="large")
    for coluna, item in zip(colunas, itens[par: par + 2]):
        with coluna.container(border=True):
            s = serie_do_grupo(item["chave"])
            st.markdown(f"**{item['nome']}**")
            st.markdown(md(linha_cidade("blue", nome_a, s, minha, item["unidade"]) + "  \n"
                           + linha_cidade("orange", nome_b, s, outra, item["unidade"])))
            grafico, frase = ranking(item)
            if grafico is not None:
                st.altair_chart(grafico, width="stretch")
            apoio = linha_por_habitante(item)
            if apoio:
                st.caption(md(apoio))
            if frase:
                st.caption(frase)
            if s.notna().sum() < 0.9 * total_com_dado:
                st.caption(f"Só {s.notna().sum()} das {total_com_dado} cidades "
                           + (f"registraram gasto nesta área no Balanço de {ano}." if item.get("secundario") else
                              f"informaram este dado no relatório de {ano}."))

with st.expander("Ranking completo", icon=":material/format_list_numbered:"):
    opcoes_r = [i["chave"] for i in itens + SECUNDARIOS if serie_do_grupo(i["chave"]).notna().any()]
    escolhido = st.selectbox("Indicador", opcoes_r, key="cmp_ranking",
                             format_func=lambda k: INDICADORES_POR_CHAVE[k]["nome"],
                             index=opcoes_r.index(indicador) if indicador in opcoes_r else 0)
    item_r = INDICADORES_POR_CHAVE[escolhido]
    s_r = serie_do_grupo(escolhido).dropna()
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
    st.caption(f"1º é o maior valor {REF}. Empates ficam na mesma posição. Use a lupa da tabela para procurar "
               "uma cidade.")

with st.expander("Como comparar com cuidado"):
    st.markdown(
        f"""
- **Peso no orçamento** ("% do gasto"): de cada R$ 100 que a prefeitura gastou no ano, quanto foi para a área.
  É a despesa liquidada na área dividida pela despesa liquidada total, as duas do Balanço Anual (DCA), sem as
  transferências entre os próprios órgãos da prefeitura. Não depende do tamanho da cidade, por isso é a medida
  principal.
- **Por habitante** (dado de apoio) divide a mesma despesa pela população que o próprio município informou no
  relatório (estimativa do IBGE). Cidades pequenas quase sempre têm valor maior: têm custos fixos e recebem mais
  repasses por pessoa. Para comparar por habitante, prefira **cidades do mesmo porte**.
- **Cidades do mesmo porte**: mesma faixa de população (até 20 mil, 20 a 50 mil, 50 a 100 mil, 100 a 900 mil ou
  mais de 900 mil habitantes). Curitiba, a única acima de 900 mil, é comparada com as 12 cidades de população
  mais próxima.
- **Funções de governo** (educação, saúde, transporte...) seguem a classificação de cada prefeitura. Um mesmo
  gasto pode estar em funções diferentes: transporte escolar, por exemplo, às vezes fica em Educação.
- **% da receita de impostos** são os mínimos da Constituição (25% em educação e 15% em saúde), apurados pelo
  próprio município no RREO. **Salários e encargos** é a despesa total com pessoal da prefeitura (sem a
  Câmara), em % da receita corrente líquida, como na Lei de Responsabilidade Fiscal (limite de 54%).
- Valores do ano de {ano}, como publicados, sem correção pela inflação. Municípios que não entregaram algum
  relatório aparecem em cinza.
"""
    )
