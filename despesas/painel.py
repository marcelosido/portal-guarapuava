"""Peças compartilhadas pelas páginas do portal: leitura dos dados, cores, gráficos e tabelas."""

from __future__ import annotations

import io
import json
import os
import unicodedata
import zipfile
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from . import config
from .dicionarios import NOMES_MES
from .formatacao import brl, numero, pct

# Cores (paleta validada para daltonismo e contraste, temas claro e escuro).
# Nenhum elemento de dado usa branco ou cor igual ao fundo.
AZUL = "#2a78d6"                          # série principal
AZUL_TRILHA = "rgba(42, 120, 214, 0.28)"  # trilha (previsto/autorizado): mesmo matiz, visível nos dois temas
CINZA = "#898781"                         # contexto: ano anterior, "outras", linhas de limite
LARANJA = "#eb6834"                       # 2ª série (ex.: a cidade comparada)
VERDE_AGUA = "#1baf7a"                    # 3ª série

# Tokens por tema. A rampa sequencial (mapa) vai do claro ao escuro no tema claro e se inverte no escuro.
TOKENS = {
    "light": {"serie": [AZUL, LARANJA, VERDE_AGUA], "superficie": "#ffffff", "tinta": "#0b0b0b",
              "tinta2": "#52514e", "apagado": "#898781", "sem_dado": "#e1e0d9", "grade": "#e1e0d9",
              "sequencial": ["#b7d3f6", "#6da7ec", "#2a78d6", "#1c5cab", "#104281"]},
    "dark": {"serie": ["#3987e5", "#d95926", "#199e70"], "superficie": "#0e1117", "tinta": "#f0efec",
             "tinta2": "#c3c2b7", "apagado": "#898781", "sem_dado": "#383835", "grade": "#2c2c2a",
             "sequencial": ["#104281", "#1c5cab", "#2a78d6", "#6da7ec", "#b7d3f6"]},
}


def tema() -> dict:
    """Tokens do tema em uso (claro ou escuro), lidos do navegador pelo Streamlit."""
    try:
        tipo = st.context.theme.type or "light"
    except Exception:  # noqa: BLE001 – versões sem st.context.theme
        tipo = "light"
    return TOKENS.get(tipo, TOKENS["light"])

# Semáforo: a cor sempre vem com ícone e texto (nunca só a cor).
STATUS = {
    "ok": ("green", ":material/check_circle:"),
    "alerta": ("orange", ":material/warning:"),
    "grave": ("red", ":material/error:"),
    "critico": ("red", ":material/dangerous:"),
    "info": ("blue", ":material/schedule:"),
    "sem_dado": ("gray", ":material/help:"),
}


def pasta_dados() -> Path:
    return Path(os.getenv("PORTAL_PASTA_DADOS", str(config.PASTA_DADOS)))


def assinatura(arquivo: Path) -> float:
    """Muda quando o arquivo muda: serve de chave do cache (o portal recarrega sozinho após a coleta)."""
    return arquivo.stat().st_mtime if arquivo.exists() else 0.0


def ler_metadados(pasta: Path) -> dict:
    arq = pasta / "metadados.json"
    try:
        return json.loads(arq.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


@st.cache_data(show_spinner="Carregando dados…")
def carregar_despesa(pasta: str, versao: float):
    p = Path(pasta)
    fato = pd.read_parquet(p / "fDespesa.parquet")

    def ler(nome: str) -> pd.DataFrame:
        return pd.read_csv(p / nome, sep=";", dtype=str, encoding="utf-8-sig").fillna("")

    fato = (
        fato.merge(ler("dNatureza.csv"), on="natureza_despesa", how="left")
        .merge(ler("dFuncao.csv"), on="funcao", how="left")
        .merge(ler("dPoderOrgao.csv"), on="poder_orgao", how="left")
    )
    arq_conc = p / "conciliacao_rreo.csv"
    conc = pd.read_csv(arq_conc, sep=";", decimal=",", encoding="utf-8-sig") if arq_conc.exists() else pd.DataFrame()
    return fato, conc


@st.cache_data(show_spinner="Carregando indicadores…")
def carregar_indicadores(pasta: str, versao: float) -> pd.DataFrame:
    arq = Path(pasta) / "fIndicadores.csv"
    if not arq.exists():
        return pd.DataFrame(columns=["relatorio", "ano", "periodo", "poder", "chave", "valor"])
    return pd.read_csv(arq, sep=";", decimal=",", encoding="utf-8-sig", dtype={"poder": str}, keep_default_na=False)


@st.cache_data(show_spinner="Carregando receitas…")
def carregar_receita_corrente(pasta: str, versao: float) -> pd.DataFrame:
    arq = Path(pasta) / "fReceitaCorrente.csv"
    if not arq.exists():
        return pd.DataFrame(columns=["ano", "periodo", "chave", "referencia", "valor"])
    return pd.read_csv(arq, sep=";", decimal=",", encoding="utf-8-sig", dtype={"referencia": str})


@st.cache_data(show_spinner="Carregando compras…")
def carregar_compras(pasta: str, versao: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    from .pncp import COLS_CONTRATACOES, COLS_CONTRATOS, tipar_contratacoes, tipar_contratos

    def ler(nome, colunas, tipar):
        arq = Path(pasta) / nome
        df = (pd.read_csv(arq, sep=";", encoding="utf-8-sig", dtype=str, keep_default_na=False)
              if arq.exists() else pd.DataFrame(columns=colunas))
        return tipar(df.reindex(columns=colunas, fill_value=""))

    return (ler("fContratacoes.csv", COLS_CONTRATACOES, tipar_contratacoes),
            ler("fContratos.csv", COLS_CONTRATOS, tipar_contratos))


@st.cache_data(show_spinner="Carregando a comparação entre cidades…")
def carregar_comparativo(pasta: str, versao: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    p = Path(pasta)
    if not (p / "fComparativo.csv").exists() or not (p / "dMunicipios.csv").exists():
        return pd.DataFrame(), pd.DataFrame()
    dados = pd.read_csv(p / "fComparativo.csv", sep=";", decimal=",", encoding="utf-8-sig", dtype={"cod_ibge": str})
    lista = pd.read_csv(p / "dMunicipios.csv", sep=";", decimal=",", encoding="utf-8-sig", dtype={"cod_ibge": str, "cnpj": str})
    return dados, lista


def _area(anel: list) -> float:
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(anel, anel[1:])) / 2


@st.cache_data
def carregar_malha() -> dict:
    """Malha municipal do PR (IBGE, via geodata-br, domínio público), simplificada para a web.

    O desenho do mapa (d3-geo, no Vega) exige o anel externo de cada polígono no sentido horário; se vier no
    anti-horário (padrão RFC 7946), o polígono vira "o mundo inteiro menos o município". A orientação é corrigida aqui.
    """
    malha = json.loads((config.PASTA_RECURSOS / "malha_pr.geojson").read_text(encoding="utf-8"))
    for feicao in malha["features"]:
        geo = feicao["geometry"]
        for poligono in ([geo["coordinates"]] if geo["type"] == "Polygon" else geo["coordinates"]):
            for i, anel in enumerate(poligono):
                if (_area(anel) > 0) == (i == 0):
                    anel.reverse()
    return malha


ARQUIVOS_ABERTOS = ("dNatureza.csv", "dFuncao.csv", "dPoderOrgao.csv", "fIndicadores.csv", "fReceitaCorrente.csv",
                    "conciliacao_rreo.csv", "fContratacoes.csv", "fContratos.csv", "dMunicipios.csv",
                    "fComparativo.csv", "metadados.json")


@st.cache_data(show_spinner="Preparando arquivo…")
def pacote_dados_abertos(pasta: str, versao: float) -> bytes:
    """Zip com a base completa em CSV (padrão brasileiro: ; e vírgula decimal)."""
    p = Path(pasta)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        if (p / "fDespesa.parquet").exists():
            fato = pd.read_parquet(p / "fDespesa.parquet")
            z.writestr("fDespesa.csv", fato.to_csv(sep=";", decimal=",", index=False).encode("utf-8-sig"))
        for nome in ARQUIVOS_ABERTOS:
            if (p / nome).exists():
                z.write(p / nome, nome)
    return buffer.getvalue()


def md(texto: str) -> str:
    """Escapa o cifrão: no Markdown do Streamlit, dois "$" na mesma linha viram fórmula matemática."""
    return str(texto).replace("$", "\\$")


def sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", str(texto)) if not unicodedata.combining(c)).lower()


def mes_extenso(ano_mes: str) -> str:
    """'2026-09' -> 'setembro/2026'"""
    if not ano_mes:
        return "–"
    a, m = map(int, ano_mes.split("-"))
    return f"{NOMES_MES[m].lower()}/{a}"


def coletado_em(meta: dict) -> str:
    return pd.Timestamp(meta["coletado_em"]).strftime("%d/%m/%Y") if meta.get("coletado_em") else "–"


def aviso_demonstracao(meta: dict) -> None:
    if meta.get("url_api") and meta["url_api"] != config.URL_OFICIAL:
        st.warning(
            f"Estes dados vieram de `{meta['url_api']}`, não da API oficial do SICONFI. "
            "Servem só para demonstração – rode `python coletar.py` para carregar os dados reais.",
            icon=":material/science:",
        )


def sem_dados() -> None:
    st.info(
        "Ainda não há dados na pasta `data/`. Rode a coleta (no robô do GitHub ou no terminal com "
        "`python coletar.py`) e recarregue esta página."
    )
    st.stop()


def selo(nivel: str, rotulo: str) -> None:
    cor, icone = STATUS.get(nivel, STATUS["sem_dado"])
    st.badge(rotulo, icon=icone, color=cor)


ROTULO_NIVEL = {"critico": "Crítico", "grave": "Grave", "alerta": "Atenção", "info": "Para acompanhar", "ok": "Em dia"}


def selo_md(nivel: str) -> str:
    """Selo em Markdown (cor + ícone + texto), para usar dentro de uma linha de texto."""
    cor, icone = STATUS.get(nivel, STATUS["sem_dado"])
    return f":{cor}-badge[{icone} {ROTULO_NIVEL.get(nivel, nivel)}]"


def cabecalho(titulo: str, descricao: str, status: str = "", seletor=None):
    """Título, uma frase sobre a página e a linha de fonte/atualização. `seletor(coluna)` desenha o filtro de ano."""
    if seletor is None:
        st.title(titulo)
        st.markdown(descricao)
        resultado = None
    else:
        esq, dir_ = st.columns([4, 1], vertical_alignment="bottom")
        with esq:
            st.title(titulo)
            st.markdown(descricao)
        resultado = seletor(dir_)
    if status:
        st.caption(md(status))
    return resultado


def seletor_ano(coluna, anos: list[int], rotulo: str = "Ano", ajuda: str | None = None) -> int:
    """Seleção de ano compartilhada entre as páginas: a escolha feita numa página vale nas outras."""
    preferido = st.session_state.get("ano_escolhido")
    indice = anos.index(preferido) if preferido in anos else 0
    ano = coluna.selectbox(rotulo, anos, index=indice, help=ajuda)
    st.session_state["ano_escolhido"] = ano
    return ano


def lista_pontos(pontos, vazio: str = "Nenhum ponto de atenção com as regras atuais.") -> None:
    """Lista de pontos de atenção: selo (cor + ícone + texto), título e explicação curta."""
    if not pontos:
        st.markdown(f":green-badge[:material/check_circle: Em dia] {vazio}")
        return
    for ponto in pontos:
        st.markdown(f"{selo_md(ponto.nivel)} **{md(ponto.titulo)}**  \n{md(ponto.detalhe)}")


def estilo_grafico(fig: go.Figure, altura: int, legenda: bool = True) -> go.Figure:
    fig.update_layout(
        height=altura,
        margin=dict(l=4, r=56, t=36 if legenda else 8, b=4),
        separators=",.",
        showlegend=legenda,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None),
        hoverlabel=dict(namelength=-1),
        font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif"),
    )
    return fig


def mostrar(fig: go.Figure, alt: str, **kwargs):
    return st.plotly_chart(fig, theme="streamlit", config={"displayModeBar": False}, alt=alt, **kwargs)


def tabela(df: pd.DataFrame, monetarias: list[str] = (), percentuais: list[str] = (), altura: int | str = "auto",
           colunas: dict | None = None, pontos_percentuais: list[str] = ()):
    """Tabela com números no padrão brasileiro; a ordenação continua numérica.

    `percentuais` recebe frações (0,519 -> 51,9%); `pontos_percentuais` recebe valores já em % (51,07 -> 51,07%).
    """
    formatos = {c: (lambda v: numero(v, 2)) for c in monetarias}
    formatos.update({c: (lambda v: pct(v)) for c in percentuais})
    formatos.update({c: (lambda v: f"{numero(v, 2)}%") for c in pontos_percentuais})
    # Célula vazia: o st.dataframe mostra "None" e ignora o na_rep do Styler. Colunas com valores em branco
    # viram texto já formatado ("–" no lugar do vazio); as demais continuam numéricas (ordenáveis).
    df = df.copy()
    for coluna, formatar in list(formatos.items()):
        if coluna in df and df[coluna].isna().any():
            df[coluna] = [("–" if pd.isna(v) else formatar(v)) for v in df[coluna]]
            del formatos[coluna]
    st.dataframe(df.style.format(formatos, na_rep="–"), hide_index=True, height=altura, column_config=colunas)


def medidor(linhas: list[tuple[str, str, float, float]], nome_total: str, nome_feito: str, alt: str,
            percentual: bool = False, marca: float | None = None) -> None:
    """Barras de progresso: faixa de fundo = total (previsto), barra azul = realizado.

    `linhas` = (título, detalhe, total, realizado), de cima para baixo. O título fica ACIMA de cada barra
    (e não no eixo), para a barra usar a largura toda também no celular.
    """
    cats = [f"l{i}" for i in range(len(linhas))]
    total = [100.0 if percentual else t / 1e6 for _, _, t, _ in linhas]
    feito = [100 * f / t if percentual else f / 1e6 for _, _, t, f in linhas]
    fig = go.Figure()
    fig.add_bar(y=cats, x=total, orientation="h", width=0.28, name=nome_total,
                marker=dict(color=AZUL_TRILHA, cornerradius=4), customdata=[brl(t) for _, _, t, _ in linhas],
                hovertemplate="%{customdata}")
    fig.add_bar(y=cats, x=feito, orientation="h", width=0.28, name=nome_feito,
                marker=dict(color=AZUL, cornerradius=4), customdata=[brl(f) for _, _, _, f in linhas],
                hovertemplate="%{customdata}")
    for cat, (titulo, detalhe, _, _) in zip(cats, linhas):
        fig.add_annotation(x=0, y=cat, xref="x", yref="y", xanchor="left", yanchor="bottom", yshift=16,
                           showarrow=False, align="left", font=dict(size=12), bgcolor=tema()["superficie"],
                           text=f"<b>{titulo}</b><br>{detalhe}")
    if marca is not None:
        fig.add_vline(x=marca, line_dash="dot", line_width=1.5, line_color=CINZA)
    fig.update_layout(barmode="overlay", hovermode="y unified")
    fig.update_yaxes(showticklabels=False, autorange="reversed", title=None)
    fig.update_xaxes(range=[0, 100] if percentual else None, ticksuffix="%" if percentual else "",
                     tickformat=",.0f", title=None if percentual else "R$ milhões")
    estilo_grafico(fig, 110 + 92 * len(linhas))
    fig.update_layout(margin=dict(t=44))  # legenda no topo, acima do primeiro título
    mostrar(fig, alt=alt)
