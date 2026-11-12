"""Compras públicas do município no PNCP: coleta, padronização e proteção de dados pessoais.

Fonte: API de consultas do PNCP (Manual das APIs de Consultas, versão 1.0). Campos usados:
contratações (/v1/contratacoes/publicacao) e contratos (/v1/contratos). As contratações são
filtradas pelo código IBGE do município e pela esfera municipal ("M"): órgãos estaduais e federais
com sede na cidade (universidades, por exemplo) ficam de fora.

LGPD: fornecedores pessoa física e microempreendedores individuais (razão social terminada no CPF)
são gravados sem nome e sem documento; números de CPF em textos livres são mascarados.
"""

from __future__ import annotations

import datetime as dt
import logging
import re
from dataclasses import dataclass

import pandas as pd

from .api import ClientePNCP, ErroAPI, TempoEsgotado

log = logging.getLogger(__name__)

# Tabela de modalidades do PNCP (/api/pncp/v1/modalidades, conferida em 12/11/2026).
MODALIDADES = {
    1: "Leilão – eletrônico", 2: "Diálogo competitivo", 3: "Concurso", 4: "Concorrência – eletrônica",
    5: "Concorrência – presencial", 6: "Pregão – eletrônico", 7: "Pregão – presencial", 8: "Dispensa",
    9: "Inexigibilidade", 10: "Manifestação de interesse", 11: "Pré-qualificação", 12: "Credenciamento",
    13: "Leilão – presencial", 14: "Inaplicabilidade da licitação", 15: "Chamada pública",
    16: "Concorrência – eletrônica internacional", 17: "Concorrência – presencial internacional",
    18: "Pregão – eletrônico internacional", 19: "Pregão – presencial internacional",
}
LICITACOES = {4, 5, 6, 7, 16, 17, 18, 19}
FALHAS_SEGUIDAS_MAX = 2  # períodos seguidos com erro: a API deve estar fora do ar      # pregão e concorrência: têm prazo mínimo de propostas
CONTRATACAO_DIRETA = {8, 9}                     # dispensa e inexigibilidade

COLS_CONTRATACOES = [
    "id_pncp", "ano_compra", "sequencial", "numero_compra", "processo", "orgao_cnpj", "orgao_nome", "esfera",
    "unidade_nome", "municipio_ibge", "modalidade_id", "modalidade", "modo_disputa", "instrumento",
    "amparo_codigo", "amparo_nome", "situacao_id", "situacao", "srp", "objeto", "valor_estimado",
    "valor_homologado", "data_publicacao", "data_abertura", "data_encerramento", "data_atualizacao", "link_origem",
]
COLS_CONTRATOS = [
    "id_pncp", "id_compra", "numero", "ano_contrato", "sequencial", "processo", "tipo", "categoria", "receita",
    "objeto", "orgao_cnpj", "orgao_nome", "unidade_nome", "fornecedor_tipo", "fornecedor_doc", "fornecedor_nome",
    "valor_inicial", "valor_global", "valor_acumulado", "parcelas", "valor_parcela", "data_assinatura",
    "vigencia_inicio", "vigencia_fim", "data_publicacao", "data_atualizacao",
]

_CPF = re.compile(r"(?<![\d./-])\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?![\d./-])")
_MEI = re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}\s*$")


# ----------------------------------------------------------------- dados pessoais
def mascarar_cpf(texto: object) -> str:
    """Troca números com formato de CPF por asteriscos (textos livres, como o objeto da compra)."""
    return _CPF.sub("***.***.***-**", "" if texto is None else str(texto))


def fornecedor_publico(tipo: object, documento: object, nome: object) -> tuple[str, str, str]:
    """(tipo, documento, nome) que podem ser publicados.

    Pessoa jurídica: CNPJ e razão social, que são públicos. Pessoa física e MEI cuja razão social
    termina com o CPF: sem documento e sem nome.
    """
    tipo = str(tipo or "").strip().upper()
    documento = re.sub(r"\D", "", str(documento or ""))
    nome = str(nome or "").strip()
    if tipo == "PF" or (tipo != "PE" and len(documento) == 11):
        return "PF", "", "Pessoa física (dado protegido)"
    if _MEI.search(nome):
        return tipo or "PJ", "", "Microempreendedor individual (dado protegido)"
    return tipo or "PJ", documento, nome


# ----------------------------------------------------------------- padronização
def _campo(registro: dict, *nomes: str, padrao=None):
    """Lê um campo aceitando variações de maiúsculas (o manual e a API divergem em alguns nomes)."""
    for nome in nomes:
        if registro.get(nome) is not None:
            return registro[nome]
    minusculas = {str(k).lower(): v for k, v in registro.items()}
    for nome in nomes:
        valor = minusculas.get(nome.lower())
        if valor is not None:
            return valor
    return padrao


def _num(valor) -> float | None:
    try:
        return None if valor is None or valor == "" else round(float(valor), 2)
    except (TypeError, ValueError):
        return None


def _data(valor) -> str:
    """'2026-10-05T08:00:00' -> '2026-10-05T08:00:00' (sem fuso); vazio quando não houver."""
    return "" if not valor else str(valor)[:19]


def normalizar_contratacao(reg: dict) -> dict:
    orgao = _campo(reg, "orgaoEntidade", padrao={}) or {}
    unidade = _campo(reg, "unidadeOrgao", padrao={}) or {}
    amparo = _campo(reg, "amparoLegal", padrao={}) or {}
    modalidade_id = int(_campo(reg, "modalidadeId", padrao=0) or 0)
    return {
        "id_pncp": _campo(reg, "numeroControlePNCP", padrao=""),
        "ano_compra": _campo(reg, "anoCompra"),
        "sequencial": _campo(reg, "sequencialCompra"),
        "numero_compra": mascarar_cpf(_campo(reg, "numeroCompra", padrao="")),
        "processo": mascarar_cpf(_campo(reg, "processo", padrao="")),
        "orgao_cnpj": re.sub(r"\D", "", str(_campo(orgao, "cnpj", padrao=""))),
        "orgao_nome": _campo(orgao, "razaoSocial", "razaosocial", padrao=""),
        "esfera": _campo(orgao, "esferaId", padrao=""),
        "unidade_nome": _campo(unidade, "nomeUnidade", padrao=""),
        "municipio_ibge": str(_campo(unidade, "codigoIbge", padrao="")),
        "modalidade_id": modalidade_id,
        "modalidade": MODALIDADES.get(modalidade_id, _campo(reg, "modalidadeNome", padrao="")),
        "modo_disputa": _campo(reg, "modoDisputaNome", padrao=""),
        "instrumento": _campo(reg, "tipoInstrumentoConvocatorioNome", padrao=""),
        "amparo_codigo": _campo(amparo, "codigo"),
        "amparo_nome": _campo(amparo, "nome", padrao=""),
        "situacao_id": _campo(reg, "situacaoCompraId"),
        "situacao": _campo(reg, "situacaoCompraNome", padrao=""),
        "srp": bool(_campo(reg, "srp", padrao=False)),
        "objeto": mascarar_cpf(_campo(reg, "objetoCompra", padrao="")).strip(),
        "valor_estimado": _num(_campo(reg, "valorTotalEstimado")),
        "valor_homologado": _num(_campo(reg, "valorTotalHomologado")),
        "data_publicacao": _data(_campo(reg, "dataPublicacaoPncp")),
        "data_abertura": _data(_campo(reg, "dataAberturaProposta")),
        "data_encerramento": _data(_campo(reg, "dataEncerramentoProposta")),
        "data_atualizacao": _data(_campo(reg, "dataAtualizacao", "dataAtualizacaoGlobal")),
        "link_origem": _campo(reg, "linkSistemaOrigem", padrao="") or "",
    }


def normalizar_contrato(reg: dict) -> dict:
    orgao = _campo(reg, "orgaoEntidade", padrao={}) or {}
    unidade = _campo(reg, "unidadeOrgao", padrao={}) or {}
    tipo_contrato = _campo(reg, "tipoContrato", padrao={}) or {}
    categoria = _campo(reg, "categoriaProcesso", padrao={}) or {}
    tipo, documento, nome = fornecedor_publico(_campo(reg, "tipoPessoa"), _campo(reg, "niFornecedor"),
                                               _campo(reg, "nomeRazaoSocialFornecedor"))
    return {
        "id_pncp": _campo(reg, "numeroControlePNCP", padrao=""),
        "id_compra": _campo(reg, "numeroControlePNCPCompra", "numeroControlePncpCompra", padrao="") or "",
        "numero": mascarar_cpf(_campo(reg, "numeroContratoEmpenho", padrao="")),
        "ano_contrato": _campo(reg, "anoContrato"),
        "sequencial": _campo(reg, "sequencialContrato"),
        "processo": mascarar_cpf(_campo(reg, "processo", padrao="")),
        "tipo": _campo(tipo_contrato, "nome", "Nome", padrao=""),
        "categoria": _campo(categoria, "nome", "Nome", padrao=""),
        "receita": bool(_campo(reg, "receita", padrao=False)),
        "objeto": mascarar_cpf(_campo(reg, "objetoContrato", padrao="")).strip(),
        "orgao_cnpj": re.sub(r"\D", "", str(_campo(orgao, "cnpj", padrao=""))),
        "orgao_nome": _campo(orgao, "razaoSocial", "razaosocial", padrao=""),
        "unidade_nome": _campo(unidade, "nomeUnidade", padrao=""),
        "fornecedor_tipo": tipo,
        "fornecedor_doc": documento,
        "fornecedor_nome": nome,
        "valor_inicial": _num(_campo(reg, "valorInicial")),
        "valor_global": _num(_campo(reg, "valorGlobal")),
        "valor_acumulado": _num(_campo(reg, "valorAcumulado")),
        "parcelas": _campo(reg, "numeroParcelas"),
        "valor_parcela": _num(_campo(reg, "valorParcela")),
        "data_assinatura": _data(_campo(reg, "dataAssinatura")),
        "vigencia_inicio": _data(_campo(reg, "dataVigenciaInicio")),
        "vigencia_fim": _data(_campo(reg, "dataVigenciaFim")),
        "data_publicacao": _data(_campo(reg, "dataPublicacaoPncp")),
        "data_atualizacao": _data(_campo(reg, "dataAtualizacao", "dataAtualizacaoGlobal")),
    }


def url_contratacao(linha) -> str:
    return f"https://pncp.gov.br/app/editais/{linha['orgao_cnpj']}/{linha['ano_compra']}/{linha['sequencial']}"


def url_contrato(linha) -> str:
    return f"https://pncp.gov.br/app/contratos/{linha['orgao_cnpj']}/{linha['ano_contrato']}/{linha['sequencial']}"


# ----------------------------------------------------------------- coleta
@dataclass(frozen=True)
class Janela:
    rotulo: str
    inicio: dt.date
    fim: dt.date

    def texto(self) -> tuple[str, str]:
        return self.inicio.strftime("%Y%m%d"), self.fim.strftime("%Y%m%d")


def janelas(inicio: dt.date, hoje: dt.date) -> list[Janela]:
    """Trimestres de `inicio` até hoje (o último termina hoje)."""
    saida = []
    ano, tri = inicio.year, (inicio.month - 1) // 3 + 1
    while (ano, tri) <= (hoje.year, (hoje.month - 1) // 3 + 1):
        ini = dt.date(ano, 3 * tri - 2, 1)
        fim = (dt.date(ano + (tri == 4), (3 * tri) % 12 + 1, 1) - dt.timedelta(days=1))
        saida.append(Janela(f"{ano}T{tri}", max(ini, inicio), min(fim, hoje)))
        ano, tri = (ano + 1, 1) if tri == 4 else (ano, tri + 1)
    return saida


def _meses(janela: Janela) -> list[Janela]:
    """Divide um trimestre em meses (usado se a API recusar o período maior)."""
    saida, d = [], janela.inicio
    while d <= janela.fim:
        prox = dt.date(d.year + (d.month == 12), d.month % 12 + 1, 1)
        saida.append(Janela(f"{d:%Y-%m}", d, min(prox - dt.timedelta(days=1), janela.fim)))
        d = prox
    return saida


def _consultar_em_partes(funcao, janela: Janela, *args) -> list[dict]:
    try:
        return funcao(*janela.texto(), *args)
    except ErroAPI as exc:
        if exc.status not in (400, 422):
            raise
        log.info("PNCP recusou o período %s (%s); consultando mês a mês.", janela.rotulo, exc.status)
        return [r for mes in _meses(janela) for r in funcao(*mes.texto(), *args)]


def _ler(caminho, colunas, tipar) -> pd.DataFrame:
    if caminho.exists():
        df = pd.read_csv(caminho, sep=";", encoding="utf-8-sig", dtype=str, keep_default_na=False)
        return tipar(df.reindex(columns=colunas, fill_value=""))
    return tipar(pd.DataFrame(columns=colunas))


def _tabela(registros: list[dict], colunas: list[str], tipar) -> pd.DataFrame:
    df = pd.DataFrame(registros, columns=colunas).map(lambda v: "" if v is None else str(v))
    return tipar(df)


def _numero(serie: pd.Series) -> pd.Series:
    """Aceita '1234.5' (coleta) e '1234,5' (CSV gravado com vírgula decimal)."""
    return pd.to_numeric(serie.astype(str).str.replace(",", ".", regex=False), errors="coerce")


def tipar_contratacoes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in ("valor_estimado", "valor_homologado"):
        df[c] = _numero(df[c])
    for c in ("modalidade_id", "situacao_id", "amparo_codigo"):
        df[c] = _numero(df[c]).astype("Int64")
    df["srp"] = df["srp"].astype(str).str.lower().isin(["true", "1"])
    return df


def tipar_contratos(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in ("valor_inicial", "valor_global", "valor_acumulado", "valor_parcela"):
        df[c] = _numero(df[c])
    df["receita"] = df["receita"].astype(str).str.lower().isin(["true", "1"])
    return df


def coletar_pncp(cliente: ClientePNCP, pasta, hoje: dt.date, municipio_ibge: str, cnpj_principal: str,
                 inicio: dt.date, controle: dict, completo: bool = False) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Coleta incremental: trimestres ainda não coletados + os dois mais recentes (atualizações).

    `controle` vem do metadados.json anterior ({"janelas_ok": [...], "contratos_ok": {cnpj: [...]}}).
    Devolve (contratações, contratos, controle atualizado). Para no meio se o tempo acabar.
    """
    from pathlib import Path

    pasta = Path(pasta)
    antigas = (_ler(pasta / "fContratacoes.csv", COLS_CONTRATACOES, tipar_contratacoes) if not completo
               else _tabela([], COLS_CONTRATACOES, tipar_contratacoes))
    antigos = (_ler(pasta / "fContratos.csv", COLS_CONTRATOS, tipar_contratos) if not completo
               else _tabela([], COLS_CONTRATOS, tipar_contratos))
    janelas_ok = set() if completo else set(controle.get("janelas_ok", []))
    contratos_ok = {} if completo else {k: set(v) for k, v in controle.get("contratos_ok", {}).items()}
    todas = janelas(inicio, hoje)
    recentes = {j.rotulo for j in todas[-2:]}
    falhas: list[str] = []
    interrompido = False

    novas: list[dict] = []
    seguidas = 0  # falhas consecutivas: com a API fora do ar, desiste logo em vez de gastar o tempo da coleta
    recusadas: set[int] = set()
    for janela in todas:
        if janela.rotulo in janelas_ok and janela.rotulo not in recentes:
            continue
        registros: list[dict] = []
        try:
            for modalidade in MODALIDADES:
                if modalidade in recusadas:
                    continue
                try:
                    registros += _consultar_em_partes(cliente.contratacoes, janela, modalidade, municipio_ibge)
                except ErroAPI as exc:
                    if exc.status is None or exc.status >= 500 or exc.status in (408, 429):
                        raise
                    recusadas.add(modalidade)  # a API não aceita esta modalidade: segue com as outras
                    log.warning("PNCP recusou a modalidade %s (%s); ela fica de fora nesta coleta.", modalidade, exc.status)
        except TempoEsgotado:
            interrompido = True
            break
        except ErroAPI as exc:
            falhas.append(f"contratações {janela.rotulo}")
            log.error("PNCP contratações %s: %s", janela.rotulo, exc)
            seguidas += 1
            if seguidas >= FALHAS_SEGUIDAS_MAX:
                log.error("PNCP: %d falhas seguidas; a coleta das compras fica para a próxima execução.", seguidas)
                interrompido = True
                break
            continue
        seguidas = 0
        linhas = [normalizar_contratacao(r) for r in registros]
        linhas = [x for x in linhas if str(x["esfera"]).upper() == "M"
                  and (not x["municipio_ibge"] or x["municipio_ibge"] == str(municipio_ibge))]
        novas += linhas
        janelas_ok.add(janela.rotulo)
        log.info("PNCP %s: %d contratações municipais", janela.rotulo, len(linhas))

    contratacoes = pd.concat([antigas, _tabela(novas, COLS_CONTRATACOES, tipar_contratacoes)],
                             ignore_index=True) if novas else antigas
    contratacoes = (contratacoes.drop_duplicates("id_pncp", keep="last")
                    .sort_values(["data_publicacao", "id_pncp"]).reset_index(drop=True))

    # contratos: por órgão municipal encontrado nas contratações (e o CNPJ do município)
    cnpjs = sorted({c for c in contratacoes["orgao_cnpj"] if c} | {cnpj_principal})
    novos: list[dict] = []
    if not interrompido:
        for cnpj in cnpjs:
            feitos = contratos_ok.setdefault(cnpj, set())
            for janela in todas:
                if janela.rotulo in feitos and janela.rotulo not in recentes:
                    continue
                try:
                    registros = _consultar_em_partes(cliente.contratos, janela, cnpj)
                except TempoEsgotado:
                    interrompido = True
                    break
                except ErroAPI as exc:
                    falhas.append(f"contratos {cnpj} {janela.rotulo}")
                    log.error("PNCP contratos %s %s: %s", cnpj, janela.rotulo, exc)
                    seguidas += 1
                    if seguidas >= FALHAS_SEGUIDAS_MAX:
                        interrompido = True
                        break
                    continue
                seguidas = 0
                novos += [normalizar_contrato(r) for r in registros]
                feitos.add(janela.rotulo)
            if interrompido:
                break
    contratos = pd.concat([antigos, _tabela(novos, COLS_CONTRATOS, tipar_contratos)],
                          ignore_index=True) if novos else antigos
    contratos = (contratos.drop_duplicates("id_pncp", keep="last")
                 .sort_values(["data_publicacao", "id_pncp"]).reset_index(drop=True))

    pendentes = [j.rotulo for j in todas if j.rotulo not in janelas_ok]
    pendentes += [f"{c} {j.rotulo}" for c in cnpjs for j in todas if j.rotulo not in contratos_ok.get(c, set())]
    status = "falhou" if falhas and not novas and not novos else ("parcial" if interrompido or falhas or pendentes else "ok")
    controle_novo = {
        "status": status,
        "inicio": inicio.isoformat(),
        "janelas_ok": sorted(janelas_ok),
        "contratos_ok": {k: sorted(v) for k, v in sorted(contratos_ok.items())},
        "pendentes": pendentes[:50],
        "falhas": falhas,
        "modalidades_recusadas": sorted(recusadas),
        "contratacoes": int(len(contratacoes)),
        "contratos": int(len(contratos)),
        "orgaos": cnpjs,
        "coletado_em": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    return contratacoes[COLS_CONTRATACOES], contratos[COLS_CONTRATOS], controle_novo
