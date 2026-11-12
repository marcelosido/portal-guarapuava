"""Comparação entre os municípios do estado, com os relatórios oficiais de um ano já fechado.

Para cada município (399 no Paraná) o coletor consulta, no SICONFI:
    extrato de entregas   -> que relatório a prefeitura entregou (normal ou simplificado, RGF semestral)
    RREO Anexo 14 (6º bim) -> % aplicado em educação e saúde, receita corrente líquida, população
    RGF Anexo 1 (fim do ano, Executivo) -> despesa com pessoal e % da receita corrente líquida
    DCA Anexo I-E          -> despesa liquidada no ano por função (educação, saúde, transporte...)
    DCA Anexo I-D          -> despesa liquidada com investimentos

São ~2.000 consultas. A coleta é retomável: guarda o que já foi feito em comparativo_controle.csv e,
se o tempo da execução acabar, continua de onde parou na próxima.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path

import pandas as pd

from .api import ClienteSiconfi, ErroAPI, TempoEsgotado
from .indicadores import (extrair_dca_funcoes, extrair_dca_natureza, extrair_rgf_pessoal, extrair_rreo14,
                          resumir_extrato)

log = logging.getLogger(__name__)

ARQ_MUNICIPIOS = "dMunicipios.csv"
ARQ_DADOS = "fComparativo.csv"
ARQ_CONTROLE = "comparativo_controle.csv"
COLS_MUNICIPIOS = ["cod_ibge", "municipio", "populacao", "cnpj", "capital"]
COLS_DADOS = ["ano", "cod_ibge", "fonte", "chave", "valor"]
COLS_CONTROLE = ["ano", "cod_ibge", "etapa", "situacao", "verificado_em", "detalhe"]
ETAPAS = ("extrato", "rreo14", "rgf01", "dca_ie", "dca_id")
REPETIR_EM_DIAS = 7  # relatório ainda não entregue: consulta de novo depois de uma semana
FALHAS_SEGUIDAS_MAX = 8  # consultas seguidas com erro: a API deve estar fora do ar
CSV = {"sep": ";", "decimal": ",", "index": False, "encoding": "utf-8-sig"}

CHAVES_RREO14 = ["educacao_pct", "educacao_minimo_pct", "fundeb_pct", "saude_pct", "saude_minimo_pct", "rcl",
                 "receita_realizada", "despesa_liquidada", "resultado_orcamentario", "restos_a_pagar_saldo"]

# Funções de governo comparadas (Portaria MOG nº 42/1999)
FUNCOES = {"12": "educacao", "10": "saude", "26": "transporte", "15": "urbanismo", "08": "assistencia",
           "06": "seguranca", "17": "saneamento", "18": "ambiental", "13": "cultura", "27": "esporte",
           "20": "agricultura", "04": "administracao"}

# Indicadores exibidos: chave, nome, unidade, tema, referência legal (linha no gráfico)
INDICADORES = [
    {"chave": "educacao_hab", "nome": "Educação: gasto por habitante", "curto": "Educação (R$/hab.)",
     "unidade": "R$/hab", "tema": "Educação"},
    {"chave": "educacao_pct", "nome": "Educação: % da receita de impostos", "curto": "Educação (% impostos)",
     "unidade": "%", "tema": "Educação", "referencia": (25.0, "mínimo 25%")},
    {"chave": "saude_hab", "nome": "Saúde: gasto por habitante", "curto": "Saúde (R$/hab.)", "unidade": "R$/hab",
     "tema": "Saúde"},
    {"chave": "saude_pct", "nome": "Saúde: % da receita de impostos", "curto": "Saúde (% impostos)", "unidade": "%",
     "tema": "Saúde", "referencia": (15.0, "mínimo 15%")},
    {"chave": "transporte_hab", "nome": "Transporte: gasto por habitante", "curto": "Transporte (R$/hab.)",
     "unidade": "R$/hab", "tema": "Transporte"},
    {"chave": "pessoal_pct", "nome": "Salários e encargos: % da receita corrente líquida", "curto": "Salários (% RCL)",
     "unidade": "%", "tema": "Salários", "referencia": (54.0, "limite 54%")},
    {"chave": "pessoal_hab", "nome": "Salários e encargos: gasto por habitante", "curto": "Salários (R$/hab.)",
     "unidade": "R$/hab", "tema": "Salários"},
    {"chave": "investimento_hab", "nome": "Investimentos (obras e equipamentos) por habitante",
     "curto": "Investimentos (R$/hab.)", "unidade": "R$/hab", "tema": "Investimento"},
    {"chave": "urbanismo_hab", "nome": "Urbanismo por habitante", "curto": "Urbanismo (R$/hab.)", "unidade": "R$/hab",
     "tema": "Cidade"},
    {"chave": "assistencia_hab", "nome": "Assistência social por habitante", "curto": "Assistência (R$/hab.)",
     "unidade": "R$/hab", "tema": "Cidade"},
    {"chave": "rcl_hab", "nome": "Receita corrente líquida por habitante", "curto": "Receita (RCL, R$/hab.)",
     "unidade": "R$/hab", "tema": "Receita"},
]
INDICADORES_POR_CHAVE = {i["chave"]: i for i in INDICADORES}


def ano_comparativo(hoje: dt.date) -> int:
    """Último ano fechado com relatórios entregues: o RREO do 6º bimestre e o RGF vencem em 30 de janeiro
    e a DCA em 30 de abril; até fevereiro, usa o ano retrasado."""
    return hoje.year - 1 if hoje.month >= 3 else hoje.year - 2


# ------------------------------------------------------------------ leitura e gravação
def _ler(pasta: Path, nome: str, colunas: list[str]) -> pd.DataFrame:
    arq = pasta / nome
    if arq.exists():
        return pd.read_csv(arq, sep=";", decimal=",", encoding="utf-8-sig", dtype={"cod_ibge": str, "cnpj": str,
                                                                                   "detalhe": str},
                           keep_default_na=False)
    return pd.DataFrame(columns=colunas)


def _gravar(caminho: Path, df: pd.DataFrame) -> None:
    temporario = caminho.with_name(caminho.name + ".tmp")
    df.to_csv(temporario, **CSV)
    temporario.replace(caminho)


def municipios(cliente: ClienteSiconfi, pasta: Path, uf: str) -> pd.DataFrame:
    """Lista dos municípios da UF (endpoint `entes`). Guardada em dMunicipios.csv."""
    salvo = _ler(pasta, ARQ_MUNICIPIOS, COLS_MUNICIPIOS)
    if len(salvo):
        return salvo
    linhas = [
        {"cod_ibge": str(e.get("cod_ibge")), "municipio": e.get("ente", ""), "populacao": e.get("populacao"),
         "cnpj": str(e.get("cnpj") or ""), "capital": str(e.get("capital", "")).strip() == "1"}
        for e in cliente.entes()
        if str(e.get("uf", "")).upper() == uf.upper() and str(e.get("esfera", "")).upper() == "M"
    ]
    df = pd.DataFrame(linhas, columns=COLS_MUNICIPIOS).sort_values("municipio").reset_index(drop=True)
    if len(df):
        _gravar(pasta / ARQ_MUNICIPIOS, df)
    return df


# ------------------------------------------------------------------ etapas
def _executar(cliente: ClienteSiconfi, etapa: str, cod: str, ano: int, info: dict) -> tuple[str, dict, dict]:
    """Devolve (situação, valores, info). Situação: ok | nao_entregue | sem_dado."""
    if etapa == "extrato":
        info = resumir_extrato(cliente.extrato_entregas(cod, ano))
        completo = info["rreo_ultimo"] >= 6 and info.get("rgf_final") and info["rgf_ultimo"] >= info["rgf_final"] \
            and info["dca"]
        return ("ok" if completo else "incompleto"), {}, info
    if etapa == "rreo14":
        if info.get("rreo_ultimo", 0) < 6:
            return "nao_entregue", {}, info
        itens = cliente.rreo(cod, ano, 6, anexo="RREO-Anexo 14", tipo=info.get("rreo_tipo") or "RREO")
        valores = {k: v for k, v in extrair_rreo14(itens).items() if k in CHAVES_RREO14}
        populacao = next((i.get("populacao") for i in itens if i.get("populacao")), None)
        if populacao:
            valores["populacao"] = float(populacao)
        return ("ok" if valores else "sem_dado"), valores, info
    if etapa == "rgf01":
        final = info.get("rgf_final")
        if not final or info.get("rgf_ultimo", 0) < final:
            return "nao_entregue", {}, info
        itens = cliente.rgf(cod, ano, final, anexo="RGF-Anexo 01", poder="E",
                            periodicidade=info.get("rgf_periodicidade") or "Q", tipo=info.get("rgf_tipo") or "RGF")
        valores = extrair_rgf_pessoal(itens)
        return ("ok" if valores else "sem_dado"), valores, info
    if etapa in ("dca_ie", "dca_id"):
        if not info.get("dca"):
            return "nao_entregue", {}, info
        anexo = "DCA-Anexo I-E" if etapa == "dca_ie" else "DCA-Anexo I-D"
        itens = cliente.dca(cod, ano, anexo)
        valores = extrair_dca_funcoes(itens) if etapa == "dca_ie" else extrair_dca_natureza(itens)
        return ("ok" if valores else "sem_dado"), valores, info
    raise ValueError(etapa)


def coletar_comparativo(cliente: ClienteSiconfi, pasta: Path, hoje: dt.date, uf: str, primeiro: str,
                        completo: bool = False) -> dict:
    """Coleta (ou continua) o comparativo do último ano fechado. Devolve o resumo para o metadados.json."""
    pasta = Path(pasta)
    ano = ano_comparativo(hoje)
    agora = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        lista = municipios(cliente, pasta, uf)
    except TempoEsgotado:
        return {"status": "parcial", "ano": ano, "motivo": "tempo esgotado antes de começar"}
    except ErroAPI as exc:
        log.error("Comparativo: não foi possível obter a lista de municípios (%s)", exc)
        return {"status": "falhou", "ano": ano, "falhas": ["lista de municípios"]}

    dados = _ler(pasta, ARQ_DADOS, COLS_DADOS)
    controle = _ler(pasta, ARQ_CONTROLE, COLS_CONTROLE)
    if completo:
        dados = dados[dados["ano"].astype(int) != ano] if len(dados) else dados
        controle = controle[controle["ano"].astype(int) != ano] if len(controle) else controle
    estado = {(int(r.ano), str(r.cod_ibge), r.etapa): r for r in controle.itertuples(index=False)}
    novos_dados: dict[tuple[str, str], dict] = {}
    novos_controle: dict[tuple[int, str, str], dict] = {}

    lista = lista.assign(_pop=pd.to_numeric(lista["populacao"], errors="coerce").fillna(0))
    ordem = [primeiro] + lista[lista["cod_ibge"] != primeiro].sort_values("_pop", ascending=False)["cod_ibge"].tolist()
    ordem = [c for c in ordem if c in set(lista["cod_ibge"])]

    def situacao(cod, etapa):
        chave = (ano, cod, etapa)
        if chave in novos_controle:
            return novos_controle[chave]
        r = estado.get(chave)
        return None if r is None else {"situacao": r.situacao, "verificado_em": r.verificado_em, "detalhe": r.detalhe}

    def precisa(cod, etapa) -> bool:
        s = situacao(cod, etapa)
        if s is None or s["situacao"] == "falha":
            return True
        if s["situacao"] == "ok":
            return False
        try:  # incompleto, nao_entregue, sem_dado: tenta de novo depois de alguns dias
            verificado = dt.datetime.fromisoformat(str(s["verificado_em"])).date()
        except ValueError:
            return True
        return (hoje - verificado).days >= REPETIR_EM_DIAS

    falhas, interrompido, consultas, seguidas = 0, False, 0, 0
    for etapa in ETAPAS:
        for cod in ordem:
            if etapa == "extrato":
                if not precisa(cod, "extrato"):
                    continue
                info = {}
            else:
                s_ext = situacao(cod, "extrato")
                if s_ext is None or s_ext["situacao"] == "falha" or not precisa(cod, etapa):
                    continue
                info = json.loads(s_ext["detalhe"] or "{}")
                s_et = situacao(cod, etapa)
                # relatório que não tinha sido entregue: só tenta de novo depois que o extrato for refeito
                if s_et and s_et["situacao"] == "nao_entregue" and s_ext["verificado_em"] <= s_et["verificado_em"] \
                        and etapa_entregue(etapa, info) is False:
                    continue
            try:
                consultas += 1
                resultado, valores, info = _executar(cliente, etapa, cod, ano, info)
            except TempoEsgotado:
                interrompido = True
                break
            except ErroAPI as exc:
                falhas += 1
                seguidas += 1
                log.warning("Comparativo %s %s: %s", cod, etapa, exc)
                novos_controle[(ano, cod, etapa)] = {"situacao": "falha", "verificado_em": agora, "detalhe": ""}
                if seguidas >= FALHAS_SEGUIDAS_MAX:
                    log.error("Comparativo: %d falhas seguidas; o restante fica para a próxima execução.", seguidas)
                    interrompido = True
                    break
                continue
            seguidas = 0
            detalhe = json.dumps(info, ensure_ascii=False, sort_keys=True) if etapa == "extrato" else ""
            novos_controle[(ano, cod, etapa)] = {"situacao": resultado, "verificado_em": agora, "detalhe": detalhe}
            if etapa != "extrato":
                novos_dados[(cod, etapa)] = valores
            elif info.get("populacao"):
                novos_dados[(cod, "extrato")] = {"populacao": float(info["populacao"])}
        if interrompido:
            break
        log.info("Comparativo %d: etapa %s concluída.", ano, etapa)

    # ---- junta com o que já existia e grava
    if novos_dados:
        trocar = pd.DataFrame([{"cod_ibge": c, "fonte": f} for c, f in novos_dados])
        if len(dados):
            marca = dados.merge(trocar.assign(_x=1), on=["cod_ibge", "fonte"], how="left")["_x"].notna().values
            dados = dados[~(marca & (dados["ano"].astype(int) == ano).values)]
        linhas = [{"ano": ano, "cod_ibge": c, "fonte": f, "chave": k, "valor": v}
                  for (c, f), valores in novos_dados.items() for k, v in valores.items()]
        novos = pd.DataFrame(linhas, columns=COLS_DADOS)
        dados = pd.concat([dados, novos], ignore_index=True) if len(dados) else novos
    if novos_controle:
        antigos = controle[[(int(a), str(c), e) not in novos_controle
                            for a, c, e in controle[["ano", "cod_ibge", "etapa"]].itertuples(index=False)]] \
            if len(controle) else controle
        linhas = [{"ano": a, "cod_ibge": c, "etapa": e, **v} for (a, c, e), v in novos_controle.items()]
        novos_ctrl = pd.DataFrame(linhas, columns=COLS_CONTROLE)
        controle = pd.concat([antigos, novos_ctrl], ignore_index=True) if len(antigos) else novos_ctrl
    if len(dados):
        dados = dados.astype({"ano": int, "cod_ibge": str})
        dados["valor"] = pd.to_numeric(dados["valor"], errors="coerce")
        dados = dados.sort_values(["ano", "cod_ibge", "fonte", "chave"]).reset_index(drop=True)
        _gravar(pasta / ARQ_DADOS, dados)
    if len(controle):
        controle = controle.astype({"ano": int}).sort_values(["ano", "cod_ibge", "etapa"]).reset_index(drop=True)
        _gravar(pasta / ARQ_CONTROLE, controle)

    do_ano = controle[controle["ano"].astype(int) == ano] if len(controle) else controle
    ok = do_ano[do_ano["situacao"] == "ok"].groupby("cod_ibge")["etapa"].nunique() if len(do_ano) else pd.Series(dtype=int)
    completos = int((ok >= len(ETAPAS)).sum()) if len(ok) else 0
    com_algum = int(len(ok))
    nomes = dict(zip(lista["cod_ibge"], lista["municipio"]))
    nao_entregues = sorted({nomes.get(c, c) for c in do_ano.loc[do_ano["situacao"].isin(["nao_entregue", "incompleto"]),
                                                                  "cod_ibge"]}) if len(do_ano) else []
    pendentes = len(ordem) - com_algum
    status = "parcial" if interrompido or pendentes > 0 else "ok"
    if consultas and falhas >= max(10, consultas // 2):
        status = "falhou"
    return {
        "status": status,
        "ano": ano,
        "uf": uf,
        "municipios": len(ordem),
        "com_dados": com_algum,
        "completos": completos,
        "sem_dados_ainda": max(0, pendentes),
        "relatorios_nao_entregues": nao_entregues[:40],
        "consultas_nesta_execucao": consultas,
        "falhas_nesta_execucao": falhas,
        "coletado_em": agora,
    }


def etapa_entregue(etapa: str, info: dict) -> bool | None:
    if etapa == "rreo14":
        return info.get("rreo_ultimo", 0) >= 6
    if etapa == "rgf01":
        return bool(info.get("rgf_final")) and info.get("rgf_ultimo", 0) >= info.get("rgf_final", 99)
    if etapa in ("dca_ie", "dca_id"):
        return bool(info.get("dca"))
    return None


# ------------------------------------------------------------------ indicadores para o portal
def tabela_indicadores(dados: pd.DataFrame, lista: pd.DataFrame, ano: int) -> pd.DataFrame:
    """Uma linha por município com os indicadores do ano (por habitante usa a população do RREO)."""
    d = dados[dados["ano"].astype(int) == ano]
    largo = d.pivot_table(index="cod_ibge", columns="chave", values="valor", aggfunc="first")
    base = lista[["cod_ibge", "municipio", "populacao"]].rename(columns={"populacao": "populacao_ibge"}).copy()
    base = base.merge(largo, left_on="cod_ibge", right_index=True, how="left")
    pop = pd.to_numeric(base.get("populacao"), errors="coerce") if "populacao" in base else pd.Series(float("nan"), index=base.index)
    pop = pop.fillna(pd.to_numeric(base["populacao_ibge"], errors="coerce"))
    base["populacao"] = pop
    por_hab = lambda col: pd.to_numeric(base[col], errors="coerce") / pop if col in base else float("nan")  # noqa: E731
    for codigo, nome in FUNCOES.items():
        base[f"{nome}_hab"] = por_hab(f"funcao_{codigo}")
    base["pessoal_hab"] = por_hab("pessoal_valor")
    base["investimento_hab"] = por_hab("investimentos")
    base["rcl_hab"] = por_hab("rcl")
    base["despesa_hab"] = por_hab("despesa_total")
    for coluna in ("educacao_pct", "saude_pct", "pessoal_pct"):
        if coluna not in base:
            base[coluna] = float("nan")
    return base.drop(columns=["populacao_ibge"])
