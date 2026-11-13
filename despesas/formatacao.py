"""Formatação de números no padrão brasileiro (R$ 1.234,56)."""

from __future__ import annotations

import math


def _br(texto: str) -> str:
    """Troca separadores do padrão americano (1,234.56) pelo brasileiro (1.234,56)."""
    return texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def numero(valor: float, casas: int = 2) -> str:
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "–"
    return _br(f"{valor:,.{casas}f}")


def brl(valor: float, casas: int = 2) -> str:
    """R$ 1.234.567,89"""
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "–"
    sinal = "-" if valor < 0 else ""
    return f"{sinal}R$ {numero(abs(valor), casas)}"


def brl_compacto(valor: float) -> str:
    """R$ 1,30 bi · R$ 676,0 mi · R$ 12,3 mil · R$ 950,00"""
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "–"
    sinal = "-" if valor < 0 else ""
    v = abs(valor)
    if v >= 1e9:
        return f"{sinal}R$ {numero(v / 1e9, 2)} bi"
    if v >= 1e6:
        return f"{sinal}R$ {numero(v / 1e6, 1)} mi"
    if v >= 1e4:
        return f"{sinal}R$ {numero(v / 1e3, 1)} mil"
    return f"{sinal}R$ {numero(v, 2)}"


def pct(fracao: float, casas: int = 1) -> str:
    """0.519 -> 51,9%"""
    if fracao is None or (isinstance(fracao, float) and (math.isnan(fracao) or math.isinf(fracao))):
        return "–"
    return f"{numero(fracao * 100, casas)}%"


def contagem(n: int, singular: str, plural: str) -> str:
    """Número com a palavra concordando: 1 licitação · 3 licitações · 1.061 licitações"""
    return f"{numero(n, 0)} {singular if n == 1 else plural}"


def razao(numerador: float, denominador: float) -> float:
    """Divisão segura: devolve NaN quando o denominador é zero."""
    return numerador / denominador if denominador else float("nan")
