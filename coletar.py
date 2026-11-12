#!/usr/bin/env python3
"""Coleta os dados do município na API do SICONFI e grava os arquivos do portal.

Exemplos:
    python coletar.py                      # incremental, de 2019 até o ano corrente
    python coletar.py --anos 2024 2026     # só esse intervalo de anos
    python coletar.py --completo           # descarta o que existe e recoleta tudo
    python coletar.py --csv                # grava também fDespesa.csv (para Excel/Power BI)

O que é coletado:
    MSC orçamentária (mensal)  -> despesa detalhada por natureza, função e poder/órgão
    RREO Anexos 1 e 14 (bimestral) -> receitas, resultado, RCL, educação, saúde, previdência, metas
    RGF Anexos 1 e 2 (quadrimestral) -> despesa com pessoal (Prefeitura e Câmara) e dívida

Arquivos gerados na pasta data/:
    fDespesa.parquet                  tabela fato da despesa (acumulado no ano até cada mês)
    dNatureza.csv, dFuncao.csv, dPoderOrgao.csv   dimensões com descrições
    fIndicadores.csv                  indicadores do RREO e do RGF por período
    rreo_totais.csv, conciliacao_rreo.csv         conferência MSC x RREO
    metadados.json                    data da coleta, períodos e origem dos dados
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import sys
from pathlib import Path
from typing import Callable

import pandas as pd

from despesas import __version__, config
from despesas.api import ClienteSiconfi, ErroAPI
from despesas.formatacao import brl, numero
from despesas.indicadores import extrair_rgf_divida, extrair_rgf_pessoal, extrair_rreo01_receitas, extrair_rreo14
from despesas.transformacao import (
    CHAVES,
    COLUNAS_MEDIDAS,
    NOMES_MEDIDAS,
    conciliar_com_rreo,
    dimensao_funcao,
    dimensao_natureza,
    dimensao_poder_orgao,
    fato_vazio,
    msc_para_fato,
    totais_rreo,
)

log = logging.getLogger("coletar")

ARQ_FATO = "fDespesa.parquet"
ARQ_RREO = "rreo_totais.csv"
ARQ_IND = "fIndicadores.csv"
COLS_IND = ["relatorio", "ano", "periodo", "poder", "chave", "valor"]
CSV = {"sep": ";", "decimal": ",", "index": False, "encoding": "utf-8-sig"}
PERIODOS_RECOLETAR = 2  # bimestres/quadrimestres mais recentes recoletados a cada execução


def argumentos(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Coleta os dados do município na API do SICONFI (Tesouro Nacional).")
    p.add_argument("--anos", nargs=2, type=int, metavar=("INICIO", "FIM"),
                   help=f"intervalo de exercícios (padrão: {config.ANO_INICIAL} até o ano corrente)")
    p.add_argument("--ente", default=config.ID_ENTE, help="código IBGE do município (padrão: %(default)s)")
    p.add_argument("--nome-ente", default=config.NOME_ENTE, help="nome exibido no portal")
    p.add_argument("--pasta", type=Path, default=config.PASTA_DADOS, help="pasta de saída (padrão: data/)")
    p.add_argument("--url", default=config.BASE_URL, help="URL base da API do SICONFI")
    p.add_argument("--pausa", type=float, default=config.PAUSA_SEGUNDOS, help="segundos entre requisições")
    p.add_argument("--meses-recoletar", type=int, default=config.MESES_RECOLETAR,
                   help="meses mais recentes recoletados a cada execução (padrão: %(default)s)")
    p.add_argument("--completo", action="store_true", help="ignora os dados existentes e recoleta tudo")
    p.add_argument("--csv", action="store_true", help="grava também fDespesa.csv (arquivo grande)")
    p.add_argument("--hoje", type=dt.date.fromisoformat, default=None, help=argparse.SUPPRESS)  # usado nos testes
    return p.parse_args(argv)


def _gravar(caminho: Path, escrever: Callable[[Path], None]) -> None:
    """Grava num arquivo temporário e renomeia: o portal nunca lê um arquivo pela metade."""
    temporario = caminho.with_name(caminho.name + ".tmp")
    escrever(temporario)
    os.replace(temporario, caminho)


def _ler_json(caminho: Path) -> dict:
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _ler_csv(caminho: Path, colunas: list[str]) -> pd.DataFrame:
    if caminho.exists():
        return pd.read_csv(caminho, sep=";", decimal=",", encoding="utf-8-sig", dtype={"poder": str}, keep_default_na=False)
    return pd.DataFrame(columns=colunas)


def _chave_mes(df: pd.DataFrame) -> pd.Series:
    return df["ano"].astype("int64") * 100 + df["mes"].astype("int64")


def _encerrados(ano_ini: int, ano_fim: int, hoje: dt.date, meses_por_periodo: int) -> list[tuple[int, int]]:
    """Períodos (bimestres ou quadrimestres) cujo último mês já terminou."""
    total = 12 // meses_por_periodo
    return [(a, p) for a in range(ano_ini, ano_fim + 1) for p in range(1, total + 1)
            if (a, p * meses_por_periodo) < (hoje.year, hoje.month)]


def _a_buscar(periodos, existentes, ausentes_antes, rotulo, hoje, completo):
    """Faltantes + os mais recentes já existentes (retificações). Ausências antigas não são repetidas."""
    recentes = set(sorted(existentes)[-PERIODOS_RECOLETAR:])
    saida = []
    for a, p in periodos:
        if (a, p) in recentes:
            saida.append((a, p))
        elif (a, p) not in existentes:
            ausente_antigo = f"{rotulo} {a}/{p}" in ausentes_antes and a < hoje.year - 1
            if completo or not ausente_antigo:
                saida.append((a, p))
    return saida


def _ausentes(antes: set[str], agora: list[str], ind: pd.DataFrame) -> list[str]:
    """Relatórios procurados e não publicados, menos os que já apareceram."""
    presentes = {f"{r} {a}/{p}" for r, a, p in ind[["relatorio", "ano", "periodo"]].itertuples(index=False)}
    return sorted((set(antes) | set(agora)) - presentes)


def coletar_msc(cliente, args, hoje, ano_ini, ano_fim, fato_ant):
    meses_existentes = sorted(set(zip(fato_ant["ano"].astype(int), fato_ant["mes"].astype(int))))
    recentes = set(meses_existentes[-args.meses_recoletar:]) if args.meses_recoletar > 0 else set()
    alvo = [(a, m) for a in range(ano_ini, ano_fim + 1) for m in range(1, 13) if (a, m) <= (hoje.year, hoje.month)]
    a_coletar = [am for am in alvo if am not in meses_existentes or am in recentes]
    log.info("MSC: %d meses a consultar entre %d e %d.", len(a_coletar), ano_ini, ano_fim)

    novos, coletados, indisponiveis, falhas = [], set(), [], []
    for ano, mes in a_coletar:
        rotulo = f"{mes:02d}/{ano}"
        try:
            classe6 = cliente.msc_orcamentaria(args.ente, ano, mes, classe=6)
            if not classe6:
                indisponiveis.append(rotulo)
                log.info("MSC %s: ainda não publicada na API.", rotulo)
                continue
            classe5 = cliente.msc_orcamentaria(args.ente, ano, mes, classe=5)
        except ErroAPI as exc:
            falhas.append(f"MSC {rotulo}")
            log.error("MSC %s: %s", rotulo, exc)
            continue
        fato_mes = msc_para_fato(classe6, classe5)
        novos.append(fato_mes)
        coletados.add((ano, mes))
        log.info("MSC %s: %5d linhas -> %5d no portal | liquidado no ano %s",
                 rotulo, len(classe6) + len(classe5), len(fato_mes), brl(fato_mes["liquidado"].sum()))

    codigos = {a * 100 + m for a, m in coletados}
    mantidos = fato_ant[~_chave_mes(fato_ant).isin(codigos)] if len(fato_ant) else fato_ant
    partes = [df for df in [mantidos, *novos] if len(df)]
    fato = pd.concat(partes, ignore_index=True).sort_values(CHAVES).reset_index(drop=True) if partes else fato_vazio()
    return fato, coletados, indisponiveis, falhas


def coletar_relatorios(cliente, args, hoje, ano_ini, ano_fim, ind_ant, rreo_ant, ausentes_antes):
    """RREO (Anexos 1 e 14) por bimestre e RGF (Anexos 1 e 2) por quadrimestre."""
    linhas, totais, ausentes, falhas = [], [], [], []
    trocados_rreo, trocados_rgf = set(), set()

    existentes = lambda rel: set(zip(ind_ant.loc[ind_ant["relatorio"] == rel, "ano"].astype(int),
                                     ind_ant.loc[ind_ant["relatorio"] == rel, "periodo"].astype(int)))
    buscar_rreo = _a_buscar(_encerrados(ano_ini, ano_fim, hoje, 2), existentes("RREO"), ausentes_antes, "RREO",
                            hoje, args.completo)
    buscar_rgf = _a_buscar(_encerrados(ano_ini, ano_fim, hoje, 4), existentes("RGF"), ausentes_antes, "RGF",
                           hoje, args.completo)
    log.info("Relatórios: %d bimestres do RREO e %d quadrimestres do RGF a consultar.", len(buscar_rreo), len(buscar_rgf))

    def adicionar(relatorio, ano, periodo, poder, valores):
        linhas.extend({"relatorio": relatorio, "ano": ano, "periodo": periodo, "poder": poder, "chave": k, "valor": v}
                      for k, v in valores.items())

    for ano, bim in buscar_rreo:
        try:
            anexo01 = cliente.rreo(args.ente, ano, bim, anexo="RREO-Anexo 01")
            if not anexo01:
                ausentes.append(f"RREO {ano}/{bim}")
                log.info("RREO %dº bim/%d: ainda não publicado.", bim, ano)
                continue
            anexo14 = cliente.rreo(args.ente, ano, bim, anexo="RREO-Anexo 14")
        except ErroAPI as exc:
            falhas.append(f"RREO {ano}/{bim}")
            log.error("RREO %dº bim/%d: %s", bim, ano, exc)
            continue
        trocados_rreo.add((ano, bim))
        adicionar("RREO", ano, bim, "", {**extrair_rreo01_receitas(anexo01), **extrair_rreo14(anexo14)})
        totais += [{"ano": ano, "bimestre": bim, "medida": k, "valor_rreo": v} for k, v in totais_rreo(anexo01).items()]
        log.info("RREO %dº bim/%d: ok", bim, ano)

    for ano, quad in buscar_rgf:
        try:
            pessoal_e = cliente.rgf(args.ente, ano, quad, anexo="RGF-Anexo 01", poder="E")
            if not pessoal_e:
                ausentes.append(f"RGF {ano}/{quad}")
                log.info("RGF %dº quadr/%d: ainda não publicado.", quad, ano)
                continue
            divida = cliente.rgf(args.ente, ano, quad, anexo="RGF-Anexo 02", poder="E")
            pessoal_l = cliente.rgf(args.ente, ano, quad, anexo="RGF-Anexo 01", poder="L")
        except ErroAPI as exc:
            falhas.append(f"RGF {ano}/{quad}")
            log.error("RGF %dº quadr/%d: %s", quad, ano, exc)
            continue
        trocados_rgf.add((ano, quad))
        adicionar("RGF", ano, quad, "E", {**extrair_rgf_pessoal(pessoal_e), **extrair_rgf_divida(divida, quad)})
        adicionar("RGF", ano, quad, "L", extrair_rgf_pessoal(pessoal_l))
        log.info("RGF %dº quadr/%d: ok", quad, ano)

    def substituir(antigo, novos_df, chaves_trocadas, col_periodo, filtro=None):
        if len(antigo):
            chave = antigo["ano"].astype(int) * 10 + antigo[col_periodo].astype(int)
            remover = chave.isin({a * 10 + p for a, p in chaves_trocadas})
            if filtro is not None:
                remover &= filtro
            antigo = antigo[~remover]
        partes = [df for df in (antigo, novos_df) if len(df)]
        return pd.concat(partes, ignore_index=True) if partes else antigo

    novos_ind = pd.DataFrame(linhas, columns=COLS_IND)
    ind = substituir(ind_ant, pd.DataFrame(columns=COLS_IND), trocados_rreo, "periodo", ind_ant["relatorio"] == "RREO")
    ind = substituir(ind, novos_ind, trocados_rgf, "periodo", ind["relatorio"] == "RGF")
    ind = ind.astype({"ano": int, "periodo": int}).sort_values(["relatorio", "ano", "periodo", "poder", "chave"])
    rreo = substituir(rreo_ant, pd.DataFrame(totais, columns=["ano", "bimestre", "medida", "valor_rreo"]),
                      trocados_rreo, "bimestre")
    return ind.reset_index(drop=True), rreo, ausentes, falhas


def main(argv: list[str] | None = None) -> int:
    args = argumentos(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
    hoje = args.hoje or dt.date.today()
    ano_ini, ano_fim = args.anos or (config.ANO_INICIAL, hoje.year)
    if ano_ini > ano_fim or ano_fim > hoje.year:
        log.error("Intervalo de anos inválido: %s a %s.", ano_ini, ano_fim)
        return 2

    pasta: Path = args.pasta
    pasta.mkdir(parents=True, exist_ok=True)
    meta_anterior = _ler_json(pasta / "metadados.json")
    if meta_anterior.get("id_ente") not in (None, args.ente) and not args.completo:
        log.error("A pasta %s tem dados do ente %s. Use --completo ou outra --pasta.", pasta, meta_anterior["id_ente"])
        return 2

    usar_existentes = not args.completo
    fato_ant = pd.read_parquet(pasta / ARQ_FATO) if usar_existentes and (pasta / ARQ_FATO).exists() else fato_vazio()
    ind_ant = _ler_csv(pasta / ARQ_IND, COLS_IND) if usar_existentes else pd.DataFrame(columns=COLS_IND)
    rreo_ant = (_ler_csv(pasta / ARQ_RREO, ["ano", "bimestre", "medida", "valor_rreo"]) if usar_existentes
                else pd.DataFrame(columns=["ano", "bimestre", "medida", "valor_rreo"]))
    ausentes_antes = set(meta_anterior.get("relatorios_ausentes", [])) if usar_existentes else set()

    log.info("Ente %s (%s), exercícios %d a %d.", args.ente, args.nome_ente, ano_ini, ano_fim)
    cliente = ClienteSiconfi(base_url=args.url, pausa=args.pausa)
    fato, coletados, indisponiveis, falhas = coletar_msc(cliente, args, hoje, ano_ini, ano_fim, fato_ant)
    if fato.empty:
        log.error("Nenhum dado disponível. Confira o código IBGE (--ente) e o acesso à internet.")
        return 1
    ind, rreo, ausentes, falhas_rel = coletar_relatorios(cliente, args, hoje, ano_ini, ano_fim, ind_ant, rreo_ant,
                                                         ausentes_antes)
    falhas += falhas_rel
    conciliacao = conciliar_com_rreo(fato, rreo, config.TOLERANCIA_CONCILIACAO)

    # ---- gravação (arquivos idênticos quando nada muda: o Git só registra o que mudou)
    _gravar(pasta / ARQ_FATO, lambda p: fato.to_parquet(p, index=False))
    if args.csv:
        _gravar(pasta / "fDespesa.csv", lambda p: fato.to_csv(p, **CSV))
    _gravar(pasta / "dNatureza.csv", lambda p: dimensao_natureza(fato["natureza_despesa"].unique()).to_csv(p, **CSV))
    _gravar(pasta / "dFuncao.csv", lambda p: dimensao_funcao(fato["funcao"].unique()).to_csv(p, **CSV))
    _gravar(pasta / "dPoderOrgao.csv", lambda p: dimensao_poder_orgao(fato["poder_orgao"].unique()).to_csv(p, **CSV))
    _gravar(pasta / ARQ_IND, lambda p: ind.to_csv(p, **CSV))
    _gravar(pasta / ARQ_RREO, lambda p: rreo.sort_values(["ano", "bimestre", "medida"]).to_csv(p, **CSV))
    _gravar(pasta / "conciliacao_rreo.csv", lambda p: conciliacao.to_csv(p, **CSV))

    meses = sorted(set(zip(fato["ano"], fato["mes"])))
    ultimo = meses[-1]
    ultimo_de = lambda rel: (ind.loc[ind["relatorio"] == rel, ["ano", "periodo"]].drop_duplicates()
                             .sort_values(["ano", "periodo"]).tail(1).astype(int).values.tolist())
    rreo_ult, rgf_ult = ultimo_de("RREO"), ultimo_de("RGF")
    metadados = {
        "id_ente": args.ente,
        "nome_ente": args.nome_ente,
        "fonte": "Tesouro Nacional / SICONFI – MSC orçamentária, RREO (Anexos 1 e 14) e RGF (Anexos 1 e 2)",
        "url_api": args.url,
        "coletado_em": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "versao_coletor": __version__,
        "primeiro_mes": f"{meses[0][0]}-{meses[0][1]:02d}",
        "ultimo_mes": f"{ultimo[0]}-{ultimo[1]:02d}",
        "meses": len(meses),
        "linhas": int(len(fato)),
        "ultimo_rreo": f"{rreo_ult[0][0]}-{rreo_ult[0][1]}" if rreo_ult else None,
        "ultimo_rgf": f"{rgf_ult[0][0]}-{rgf_ult[0][1]}" if rgf_ult else None,
        "requisicoes": cliente.requisicoes,
        "meses_coletados_nesta_execucao": len(coletados),
        "meses_ainda_nao_publicados": indisponiveis,
        "relatorios_ausentes": _ausentes(ausentes_antes, ausentes, ind),
        "falhas": falhas,
    }
    _gravar(pasta / "metadados.json",
            lambda p: p.write_text(json.dumps(metadados, ensure_ascii=False, indent=2), encoding="utf-8"))

    # ---- resumo
    tot = fato[(fato["ano"] == ultimo[0]) & (fato["mes"] == ultimo[1])][COLUNAS_MEDIDAS].sum()
    status = conciliacao["status"].value_counts().to_dict()
    divergentes = conciliacao[conciliacao["status"] == "Divergente"]
    print("\nResumo da coleta")
    print(f"  MSC: {meses[0][1]:02d}/{meses[0][0]} a {ultimo[1]:02d}/{ultimo[0]} ({len(meses)} meses, {numero(len(fato), 0)} linhas)")
    print(f"  {ultimo[1]:02d}/{ultimo[0]}: dotação atualizada {brl(tot['dotacao_atualizada'])} | empenhado {brl(tot['empenhado'])}"
          f" | liquidado {brl(tot['liquidado'])} | pago {brl(tot['pago'])}")
    if rreo_ult:
        print(f"  RREO até o {rreo_ult[0][1]}º bimestre/{rreo_ult[0][0]}")
    if rgf_ult:
        print(f"  RGF até o {rgf_ult[0][1]}º quadrimestre/{rgf_ult[0][0]}")
    print(f"  Conferência MSC x RREO: {status.get('Conciliado', 0)} conciliadas, {status.get('Divergente', 0)} divergentes,"
          f" {status.get('RREO indisponível', 0)} sem RREO publicado")
    if len(divergentes):
        maior = divergentes.loc[divergentes["diferenca"].abs().idxmax()]
        print(f"  Maior divergência: {NOMES_MEDIDAS[maior['medida']]} no {int(maior['bimestre'])}º bim/{int(maior['ano'])}:"
              f" {brl(maior['diferenca'])} (MSC − RREO)")
    print(f"  Requisições à API: {cliente.requisicoes} | arquivos em {pasta.resolve()}")
    if falhas:
        print(f"  ATENÇÃO: falha ao consultar {', '.join(falhas)} – rode novamente para completar.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
