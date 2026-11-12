"""Transforma as linhas da MSC em tabelas do portal e confere os totais com o RREO.

Regra de negócio (PCASP): nas contas de controle da execução da despesa, o saldo
final de cada mês é o acumulado do ano até aquele mês.

    dotação inicial     = 5.2.2.1.1          (saldo devedor)
    dotação atualizada  = 6.2.2.1   (todas)  (saldo credor)
    empenhado           = 6.2.2.1.3 (todas)
    liquidado           = 6.2.2.1.3.03 (liquidado a pagar) + 6.2.2.1.3.04 (pago)
    pago                = 6.2.2.1.3.04

Validação feita em 30/10/2026 com Guarapuava, ago/2026, contra o RREO Anexo 1 do
4º bimestre: empenhado, liquidado e pago bateram ao centavo. A dotação da MSC ficou
R$ 1.469,54 acima da informada no RREO (diferença do próprio envio do município,
presente tanto na dotação inicial quanto na atualizada).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from .dicionarios import CATEGORIA, ELEMENTO, FUNCAO, GRUPO, MODALIDADE, PODER_ORGAO, descrever


@dataclass(frozen=True)
class RegraMedida:
    classe: int
    prefixos: tuple[str, ...]
    natureza_normal: str  # "D" ou "C": saldo nessa natureza soma; na outra, subtrai


MEDIDAS: dict[str, RegraMedida] = {
    "dotacao_inicial": RegraMedida(5, ("52211",), "D"),
    "dotacao_atualizada": RegraMedida(6, ("6221",), "C"),
    "empenhado": RegraMedida(6, ("62213",), "C"),
    "liquidado": RegraMedida(6, ("6221303", "6221304"), "C"),
    "pago": RegraMedida(6, ("6221304",), "C"),
}
NOMES_MEDIDAS = {
    "dotacao_inicial": "Dotação inicial",
    "dotacao_atualizada": "Dotação atualizada",
    "empenhado": "Empenhado",
    "liquidado": "Liquidado",
    "pago": "Pago",
}
COLUNAS_MEDIDAS = list(MEDIDAS)
CHAVES = ["ano", "mes", "poder_orgao", "funcao", "subfuncao", "natureza_despesa", "fonte_recursos"]
_TEXTO = ["conta_contabil", "poder_orgao", "funcao", "subfuncao", "natureza_despesa", "fonte_recursos", "natureza_conta"]


def fato_vazio() -> pd.DataFrame:
    df = pd.DataFrame({c: pd.Series(dtype="str") for c in CHAVES})
    df["ano"] = pd.Series(dtype="int64")
    df["mes"] = pd.Series(dtype="int64")
    for m in COLUNAS_MEDIDAS:
        df[m] = pd.Series(dtype="float64")
    return df[CHAVES + COLUNAS_MEDIDAS]


def _preparar(linhas: Iterable[dict] | None) -> pd.DataFrame:
    df = pd.DataFrame.from_records(list(linhas or []))
    if df.empty:
        return df
    faltando = {"exercicio", "mes_referencia", "conta_contabil", "valor", "natureza_conta"} - set(df.columns)
    if faltando:
        raise ValueError(f"Resposta da MSC sem os campos esperados: {sorted(faltando)}")
    df = df.rename(columns={"exercicio": "ano", "mes_referencia": "mes"})
    for coluna in _TEXTO:
        if coluna not in df.columns:
            df[coluna] = ""
        df[coluna] = df[coluna].astype("str").fillna("").str.strip().replace({"None": "", "nan": ""})
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0.0)
    return df


def msc_para_fato(linhas_classe6: Iterable[dict], linhas_classe5: Iterable[dict] | None = None) -> pd.DataFrame:
    """Converte as linhas da MSC (classes 6 e 5) de um mês na tabela fato do portal.

    Cada linha da saída é uma combinação de ano, mês, poder/órgão, função, subfunção,
    natureza da despesa (8 dígitos) e fonte de recursos, com as cinco medidas
    acumuladas no ano até o mês.
    """
    bases = {6: _preparar(linhas_classe6), 5: _preparar(linhas_classe5)}
    partes = []
    for medida, regra in MEDIDAS.items():
        df = bases[regra.classe]
        if df.empty:
            continue
        sel = df[df["conta_contabil"].str.startswith(regra.prefixos)]
        if sel.empty:
            continue
        sinal = np.where(sel["natureza_conta"].eq(regra.natureza_normal), 1.0, -1.0)
        parte = sel[CHAVES].copy()
        parte["medida"] = medida
        parte["valor"] = sel["valor"].to_numpy() * sinal
        partes.append(parte)
    if not partes:
        return fato_vazio()

    longo = pd.concat(partes, ignore_index=True)
    fato = (
        longo.groupby(CHAVES + ["medida"], dropna=False)["valor"].sum()
        .unstack("medida", fill_value=0.0)
        .reset_index()
    )
    fato.columns.name = None
    for medida in COLUNAS_MEDIDAS:
        if medida not in fato.columns:
            fato[medida] = 0.0
    fato[COLUNAS_MEDIDAS] = fato[COLUNAS_MEDIDAS].round(2)
    fato = fato[(fato[COLUNAS_MEDIDAS].abs() >= 0.005).any(axis=1)]
    fato = fato.astype({"ano": "int64", "mes": "int64"})
    return fato[CHAVES + COLUNAS_MEDIDAS].sort_values(CHAVES).reset_index(drop=True)


# ----------------------------------------------------------------- dimensões
def dimensao_natureza(codigos: Iterable[str]) -> pd.DataFrame:
    linhas = []
    for codigo in sorted({str(c) for c in codigos if c}):
        c = re.sub(r"\D", "", codigo).ljust(8, "0")[:8]
        linhas.append(
            {
                "natureza_despesa": codigo,
                "natureza_formatada": f"{c[0]}.{c[1]}.{c[2:4]}.{c[4:6]}.{c[6:8]}",
                "natureza6": c[:6],
                "categoria": c[0],
                "categoria_desc": descrever(CATEGORIA, c[0], "Categoria"),
                "grupo": c[1],
                "grupo_desc": descrever(GRUPO, c[1], "Grupo"),
                "modalidade": c[2:4],
                "modalidade_desc": descrever(MODALIDADE, c[2:4], "Modalidade"),
                "elemento": c[4:6],
                "elemento_desc": descrever(ELEMENTO, c[4:6], "Elemento"),
            }
        )
    return pd.DataFrame(linhas)


def dimensao_funcao(codigos: Iterable[str]) -> pd.DataFrame:
    cods = sorted({str(c) for c in codigos if c})
    return pd.DataFrame({"funcao": cods, "funcao_desc": [descrever(FUNCAO, c, "Função") for c in cods]})


def dimensao_poder_orgao(codigos: Iterable[str]) -> pd.DataFrame:
    cods = sorted({str(c) for c in codigos if c})
    return pd.DataFrame(
        {"poder_orgao": cods, "poder_orgao_desc": [descrever(PODER_ORGAO, c, "Poder/órgão") for c in cods]}
    )


# ------------------------------------------------------------ conferência RREO
_COLUNAS_RREO = {
    "dotacao_inicial": r"^DOTA[ÇC][ÃA]O INICIAL",
    "dotacao_atualizada": r"^DOTA[ÇC][ÃA]O ATUALIZADA",
    "empenhado": r"^DESPESAS EMPENHADAS AT[ÉE] O BIMESTRE",
    "liquidado": r"^DESPESAS LIQUIDADAS AT[ÉE] O BIMESTRE",
    "pago": r"^DESPESAS PAGAS AT[ÉE] O BIMESTRE",
}


def totais_rreo(itens: Iterable[dict]) -> dict[str, float]:
    """Extrai do RREO Anexo 1 a linha "TOTAL DAS DESPESAS" nas colunas acumuladas."""
    itens = list(itens)
    linhas = [i for i in itens if i.get("cod_conta") == "TotalDespesas"]
    if not linhas:
        linhas = [i for i in itens if str(i.get("conta", "")).upper().startswith("TOTAL DAS DESPESAS")]
    if any(i.get("rotulo") for i in linhas):
        padrao = [i for i in linhas if i.get("rotulo") == "Padrão"]
        linhas = padrao or linhas
    totais: dict[str, float] = {}
    for medida, regex in _COLUNAS_RREO.items():
        for item in linhas:
            if re.search(regex, str(item.get("coluna", "")).upper()):
                totais[medida] = round(float(item["valor"]), 2)
                break
    return totais


def conciliar_com_rreo(fato: pd.DataFrame, rreo: pd.DataFrame, tolerancia: float) -> pd.DataFrame:
    """Compara os totais da MSC no fim de cada bimestre com o RREO Anexo 1.

    `rreo` tem as colunas ano, bimestre, medida, valor_rreo.
    """
    colunas = ["ano", "bimestre", "mes", "medida", "valor_msc", "valor_rreo", "diferenca", "status"]
    if fato.empty:
        return pd.DataFrame(columns=colunas)
    totais_msc = fato.groupby(["ano", "mes"])[COLUNAS_MEDIDAS].sum().round(2)
    linhas = []
    for (ano, mes), tot in totais_msc.iterrows():
        if mes % 2:
            continue
        bimestre = mes // 2
        for medida in COLUNAS_MEDIDAS:
            ref = rreo[(rreo["ano"] == ano) & (rreo["bimestre"] == bimestre) & (rreo["medida"] == medida)]
            valor_msc = round(float(tot[medida]), 2)
            if ref.empty:
                linhas.append([ano, bimestre, mes, medida, valor_msc, None, None, "RREO indisponível"])
                continue
            valor_rreo = round(float(ref["valor_rreo"].iloc[0]), 2)
            diferenca = round(valor_msc - valor_rreo, 2)
            status = "Conciliado" if abs(diferenca) <= tolerancia else "Divergente"
            linhas.append([ano, bimestre, mes, medida, valor_msc, valor_rreo, diferenca, status])
    return pd.DataFrame(linhas, columns=colunas)
