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
from .formatacao import numero, pct

# Cores (paleta validada para daltonismo e contraste, temas claro e escuro).
# Nenhum elemento de dado usa branco ou cor igual ao fundo.
AZUL = "#2a78d6"                          # série principal
AZUL_TRILHA = "rgba(42, 120, 214, 0.28)"  # trilha (previsto/autorizado): mesmo matiz, visível nos dois temas
CINZA = "#898781"                         # contexto: ano anterior, "outras", linhas de limite

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


@st.cache_data(show_spinner="Preparando arquivo…")
def pacote_dados_abertos(pasta: str, versao: float) -> bytes:
    """Zip com a base completa em CSV (padrão brasileiro: ; e vírgula decimal)."""
    p = Path(pasta)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        if (p / "fDespesa.parquet").exists():
            fato = pd.read_parquet(p / "fDespesa.parquet")
            z.writestr("fDespesa.csv", fato.to_csv(sep=";", decimal=",", index=False).encode("utf-8-sig"))
        for nome in ("dNatureza.csv", "dFuncao.csv", "dPoderOrgao.csv", "fIndicadores.csv",
                     "conciliacao_rreo.csv", "metadados.json"):
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


def mostrar(fig: go.Figure, alt: str) -> None:
    st.plotly_chart(fig, theme="streamlit", config={"displayModeBar": False}, alt=alt)


def tabela(df: pd.DataFrame, monetarias: list[str] = (), percentuais: list[str] = (), altura: int | str = "auto",
           colunas: dict | None = None, pontos_percentuais: list[str] = ()):
    """Tabela com números no padrão brasileiro; a ordenação continua numérica.

    `percentuais` recebe frações (0,519 -> 51,9%); `pontos_percentuais` recebe valores já em % (51,07 -> 51,07%).
    """
    formatos = {c: (lambda v: numero(v, 2)) for c in monetarias}
    formatos.update({c: (lambda v: pct(v)) for c in percentuais})
    formatos.update({c: (lambda v: f"{numero(v, 2)}%") for c in pontos_percentuais})
    st.dataframe(df.style.format(formatos, na_rep="–"), hide_index=True, height=altura, column_config=colunas)
