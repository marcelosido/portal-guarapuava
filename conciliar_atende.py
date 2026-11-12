#!/usr/bin/env python3
"""Confere o arquivo exportado do portal da transparência (Atende.net) com os dados do SICONFI.

Como exportar: no portal da transparência, abra Despesas > Demonstrativo das Despesas, escolha
Entidade = Todos, o Ano e o Mês, clique em Consultar e depois em "Dados Abertos" (CSV) – ou no
ícone de impressora, formato "Arquivo Delimitado (csv)". Em seguida:

    python conciliar_atende.py Demonstrativo.csv --ano 2026 --mes 8

Compara, por poder/órgão e natureza da despesa (até elemento):
    "Liquidado até o Mês"  x  liquidado acumulado da MSC
    "Prevista para o Ano"  x  dotação atualizada e dotação inicial da MSC
e grava data/conciliacao_atende_AAAA_MM.csv.

ATENÇÃO: o leitor foi escrito a partir das colunas que a página exibe na tela
(Entidade, Natureza da Despesa - Elemento, Conta - Código, Prevista para o Ano,
Liquidado até o Mês). Se o CSV vier com outros nomes, informe-os com --col-*.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

from despesas import config
from despesas.formatacao import brl, numero, pct

PADROES = {
    "entidade": ("entidade",),
    "codigo": ("conta codigo", "codigo"),
    "elemento": ("elemento",),
    "previsto": ("prevista", "previsto", "dotacao"),
    "liquidado": ("liquidado",),
}


def normalizar(texto: str) -> str:
    sem_acento = "".join(c for c in unicodedata.normalize("NFKD", str(texto)) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", sem_acento.lower()).strip()


def para_numero(valor: str) -> float:
    """Aceita 1.234,56 · 1234,56 · 1234.56 · 1,234.56 · R$ 1.234,56 · (vazio)."""
    s = re.sub(r"[^\d,.\-]", "", str(valor))
    if not s or s in {"-", ".", ","}:
        return 0.0
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    return float(s)


def ler_csv(caminho: Path) -> pd.DataFrame:
    bruto = caminho.read_bytes()
    for codificacao in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            texto = bruto.decode(codificacao)
            break
        except UnicodeDecodeError:
            continue
    linhas = texto.splitlines()
    # Alguns exportadores põem título/filtros antes do cabeçalho: procura a linha com as colunas de valor.
    inicio = next((i for i, l in enumerate(linhas[:50]) if "liquidado" in normalizar(l) and
                   any(p in normalizar(l) for p in PADROES["previsto"])), 0)
    corpo = "\n".join(linhas[inicio:])
    try:
        separador = csv.Sniffer().sniff(corpo[:5000], delimiters=";,\t|").delimiter
    except csv.Error:
        separador = ";"
    return pd.read_csv(io.StringIO(corpo), sep=separador, dtype=str, keep_default_na=False)


def achar_colunas(df: pd.DataFrame, forcadas: dict[str, str | None]) -> dict[str, str]:
    colunas = {}
    for alvo, padroes in PADROES.items():
        if forcadas.get(alvo):
            if forcadas[alvo] not in df.columns:
                raise SystemExit(f"Coluna '{forcadas[alvo]}' não existe no arquivo. Colunas: {list(df.columns)}")
            colunas[alvo] = forcadas[alvo]
            continue
        encontrada = next((c for p in padroes for c in df.columns if p in normalizar(c)), None)
        if encontrada is None:
            raise SystemExit(
                f"Não achei a coluna de '{alvo}'. Colunas do arquivo: {list(df.columns)}.\n"
                f"Informe com --col-{alvo} \"Nome da coluna\"."
            )
        colunas[alvo] = encontrada
    return colunas


def natureza6(codigo: str, elemento: str) -> str | None:
    """Código da conta no Atende = "3" + categoria + grupo + modalidade + zeros (ex.: 3319000000000000000).

    Junta com o elemento ("11 - ...") para formar a natureza até elemento: 319011.
    """
    d = re.sub(r"\D", "", str(codigo))
    el = re.match(r"\s*(\d{1,2})\b", str(elemento))
    if len(d) < 5 or not el or d[0] != "3" or d[1] not in "3479":
        return None
    return d[1] + d[2] + d[3:5] + el.group(1).zfill(2)


def poder_orgao(entidade: str) -> str:
    """Hipótese: Câmara -> Legislativo; instituto de previdência -> RPPS; demais entidades -> Executivo."""
    e = normalizar(entidade)
    if "camara" in e:
        return "20231"
    if "previdencia" in e or " prev" in f" {e}":
        return "10132"
    return "10131"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Confere o CSV do portal da transparência com a MSC do SICONFI.")
    p.add_argument("arquivo", type=Path, help="CSV exportado do Demonstrativo das Despesas")
    p.add_argument("--ano", type=int, required=True, help="ano usado na exportação")
    p.add_argument("--mes", type=int, required=True, help="mês usado na exportação (1 a 12)")
    p.add_argument("--pasta", type=Path, default=config.PASTA_DADOS, help="pasta com os dados do portal")
    p.add_argument("--tolerancia", type=float, default=config.TOLERANCIA_CONCILIACAO)
    for alvo in PADROES:
        p.add_argument(f"--col-{alvo}", dest=f"col_{alvo}", help=f"nome da coluna de {alvo} no CSV")
    args = p.parse_args(argv)

    fato = pd.read_parquet(args.pasta / "fDespesa.parquet")
    msc = fato[(fato["ano"] == args.ano) & (fato["mes"] == args.mes)]
    if msc.empty:
        print(f"O mês {args.mes:02d}/{args.ano} não está nos dados do portal. Rode coletar.py ou escolha outro mês.")
        return 2

    bruto = ler_csv(args.arquivo)
    col = achar_colunas(bruto, {a: getattr(args, f"col_{a}") for a in PADROES})
    print("Colunas usadas: " + " | ".join(f"{a} = '{c}'" for a, c in col.items()))

    atende = pd.DataFrame({
        "poder_orgao": bruto[col["entidade"]].map(poder_orgao),
        "natureza6": [natureza6(c, e) for c, e in zip(bruto[col["codigo"]], bruto[col["elemento"]])],
        "previsto_atende": bruto[col["previsto"]].map(para_numero),
        "liquidado_atende": bruto[col["liquidado"]].map(para_numero),
    })
    sem_natureza = atende["natureza6"].isna()
    if sem_natureza.all():
        print("Não consegui montar a natureza da despesa a partir do código e do elemento. Exemplos:\n"
              + bruto[[col["codigo"], col["elemento"]]].head().to_string(index=False))
        return 2
    if sem_natureza.any():
        print(f"Aviso: {int(sem_natureza.sum())} linhas sem natureza reconhecida ficaram de fora "
              f"(liquidado {brl(atende.loc[sem_natureza, 'liquidado_atende'].sum())}).")
    atende = atende[~sem_natureza].groupby(["poder_orgao", "natureza6"]).sum()

    lado_msc = (msc.assign(natureza6=msc["natureza_despesa"].str[:6])
                .groupby(["poder_orgao", "natureza6"])[["dotacao_inicial", "dotacao_atualizada", "liquidado"]].sum()
                .rename(columns={"liquidado": "liquidado_msc"}))
    comp = atende.join(lado_msc, how="outer").fillna(0.0).round(2)
    comp["dif_liquidado"] = (comp["liquidado_atende"] - comp["liquidado_msc"]).round(2)
    comp["dif_previsto_x_atualizada"] = (comp["previsto_atende"] - comp["dotacao_atualizada"]).round(2)
    comp["dif_previsto_x_inicial"] = (comp["previsto_atende"] - comp["dotacao_inicial"]).round(2)
    comp["status_liquidado"] = comp["dif_liquidado"].abs().le(args.tolerancia).map({True: "Igual", False: "Diferente"})
    saida = args.pasta / f"conciliacao_atende_{args.ano}_{args.mes:02d}.csv"
    comp.reset_index().to_csv(saida, sep=";", decimal=",", index=False, encoding="utf-8-sig")

    tot = comp.sum(numeric_only=True)
    iguais = int((comp["status_liquidado"] == "Igual").sum())
    print(f"\nConferência {args.mes:02d}/{args.ano} – portal da transparência x SICONFI (MSC)")
    print(f"  Liquidado:  Atende {brl(tot['liquidado_atende'])} | MSC {brl(tot['liquidado_msc'])}"
          f" | diferença {brl(tot['dif_liquidado'])}")
    print(f"  Previsto:   Atende {brl(tot['previsto_atende'])} | dotação atualizada {brl(tot['dotacao_atualizada'])}"
          f" | dotação inicial {brl(tot['dotacao_inicial'])}")
    print(f"  Linhas (poder/órgão x natureza): {iguais} de {len(comp)} iguais no liquidado"
          f" ({pct(iguais / len(comp)) if len(comp) else '–'})")
    diferentes = comp[comp["status_liquidado"] == "Diferente"].sort_values("dif_liquidado", key=abs, ascending=False)
    if len(diferentes):
        print("  Maiores diferenças no liquidado (Atende − MSC):")
        for (po, nat), linha in diferentes.head(10).iterrows():
            print(f"    {po}  {nat[0]}.{nat[1]}.{nat[2:4]}.{nat[4:6]}  {brl(linha['dif_liquidado']):>22}")
    print(f"  Detalhe gravado em {saida} ({numero(len(comp), 0)} linhas)")
    return 0 if len(diferentes) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
