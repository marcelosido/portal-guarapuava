"""Compras públicas do município no PNCP: coleta, padronização e proteção de dados pessoais.

Fonte: API de consultas do PNCP (Manual das APIs de Consultas, versão 1.0). Campos usados:
contratações (/v1/contratacoes/publicacao) e contratos (/v1/contratos). As contratações são
filtradas pelo código IBGE do município e pela esfera municipal ("M"): órgãos estaduais e federais
com sede na cidade (universidades, por exemplo) ficam de fora.

LGPD: fornecedores pessoa física e microempreendedores individuais (MEI) são gravados com o nome, mas sem
nenhum número de documento (nem CPF, nem CNPJ do MEI); números de CPF em textos livres são mascarados.
No portal, os nomes aparecem só nas tabelas; rankings e pontos de atenção os mostram agrupados.
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
_MEI = re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}\s*$")          # MEI antigo: "NOME 12345678901"
_MEI_CNPJ = re.compile(r"^\s*\d{2}\.?\d{3}\.?\d{3}\s+(?=\D)")      # MEI novo: "12.345.678 NOME"
# Regra de publicação dos fornecedores. Mudou em 1.2.3 (antes: pessoa física e MEI sem nome); quando muda, o
# coletor busca de novo, uma vez, os contratos já gravados.
POLITICA_FORNECEDOR = "nome-sem-documento"


# ----------------------------------------------------------------- dados pessoais
def mascarar_cpf(texto: object) -> str:
    """Troca números com formato de CPF por asteriscos (textos livres, como o objeto da compra)."""
    return _CPF.sub("***.***.***-**", "" if texto is None else str(texto))


def _sem_documento(nome: str) -> str:
    """Nome sem números de documento: tira o CPF (no fim ou no meio) e o CNPJ básico no começo (MEI)."""
    nome = _MEI_CNPJ.sub("", nome)
    nome = re.sub(r"\b(?:CPF|CNPJ)\s*[:nº°.]*\s*", " ", _CPF.sub(" ", nome), flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", nome).strip(" -–,.;:/")


def fornecedor_publico(tipo: object, documento: object, nome: object) -> tuple[str, str, str]:
    """(tipo, documento, nome) que podem ser publicados.

    Pessoa jurídica: CNPJ e razão social, que são públicos. Pessoa física ("PF") e microempreendedor
    individual ("MEI"): só o nome, sem nenhum número de documento.
    """
    tipo = str(tipo or "").strip().upper()
    documento = re.sub(r"\D", "", str(documento or ""))
    nome = str(nome or "").strip()
    if tipo == "PF" or (tipo != "PE" and len(documento) == 11):
        return "PF", "", _sem_documento(nome) or "Pessoa física"
    if _MEI.search(nome) or _MEI_CNPJ.match(nome):
        return "MEI", "", _sem_documento(nome) or "Microempreendedor individual"
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
    """Coleta incremental, do trimestre mais recente para o mais antigo.

    Em cada trimestre: as contratações (todas as modalidades) e, logo depois, os contratos de cada órgão
    municipal, começando pelo CNPJ do município. Se o tempo acabar, o que falta é sempre o período mais antigo,
    e ele fica em `pendentes` para a próxima execução. Os dois trimestres mais recentes são sempre consultados de
    novo (atualizações). `controle` vem do metadados.json anterior
    ({"janelas_ok": [...], "contratos_ok": {cnpj: [...]}}). Devolve (contratações, contratos, controle atualizado).
    """
    from pathlib import Path

    pasta = Path(pasta)
    antigas = (_ler(pasta / "fContratacoes.csv", COLS_CONTRATACOES, tipar_contratacoes) if not completo
               else _tabela([], COLS_CONTRATACOES, tipar_contratacoes))
    antigos = (_ler(pasta / "fContratos.csv", COLS_CONTRATOS, tipar_contratos) if not completo
               else _tabela([], COLS_CONTRATOS, tipar_contratos))
    janelas_ok = set() if completo else set(controle.get("janelas_ok", []))
    contratos_ok = {} if completo else {k: set(v) for k, v in controle.get("contratos_ok", {}).items()}
    # Regra de publicação dos fornecedores mudou: busca de novo, uma vez, os contratos já gravados (por último,
    # depois do que falta; não conta como "em falta", porque os contratos já estão lá).
    if controle.get("politica_fornecedor") == POLITICA_FORNECEDOR or completo:
        renovar = {tuple(str(x).split(" ", 1)) for x in controle.get("renovar_contratos", [])}
    else:
        renovar = {(c, r) for c, rotulos in contratos_ok.items() for r in rotulos}
    todas = janelas(inicio, hoje)
    recentes = {j.rotulo for j in todas[-2:]}
    ordem = todas[::-1]  # mais recente primeiro
    orgaos = {c for c in antigas["orgao_cnpj"] if c} | set(contratos_ok) | {cnpj_principal}
    falhas: list[str] = []
    novas: list[dict] = []
    novos: list[dict] = []
    recusadas: set[int] = set()
    consultados: set[tuple[str, str]] = set()
    estado = {"seguidas": 0, "parar": False}  # falhas seguidas: com a API fora do ar, desiste logo

    def lista_orgaos() -> list[str]:
        return [cnpj_principal] + sorted(orgaos - {cnpj_principal})

    def precisa(feitos: set, janela: Janela) -> bool:
        return janela.rotulo not in feitos or janela.rotulo in recentes

    def falhou(descricao: str, exc: Exception) -> None:
        falhas.append(descricao)
        log.error("PNCP %s: %s", descricao, exc)
        estado["seguidas"] += 1
        if estado["seguidas"] >= FALHAS_SEGUIDAS_MAX:
            log.error("PNCP: %d falhas seguidas; o restante fica para a próxima execução.", estado["seguidas"])
            estado["parar"] = True

    def buscar_contratacoes(janela: Janela) -> None:
        registros: list[dict] = []
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
        linhas = [normalizar_contratacao(r) for r in registros]
        linhas = [x for x in linhas if str(x["esfera"]).upper() == "M"
                  and (not x["municipio_ibge"] or x["municipio_ibge"] == str(municipio_ibge))]
        novas.extend(linhas)
        orgaos.update(x["orgao_cnpj"] for x in linhas if x["orgao_cnpj"])
        janelas_ok.add(janela.rotulo)
        estado["seguidas"] = 0
        log.info("PNCP %s: %d contratações municipais", janela.rotulo, len(linhas))

    def buscar_contratos(cnpj: str, janela: Janela) -> None:
        registros = _consultar_em_partes(cliente.contratos, janela, cnpj)
        novos.extend(normalizar_contrato(r) for r in registros)
        contratos_ok.setdefault(cnpj, set()).add(janela.rotulo)
        consultados.add((cnpj, janela.rotulo))
        renovar.discard((cnpj, janela.rotulo))
        estado["seguidas"] = 0

    def contratos_da_janela(janela: Janela) -> None:
        for cnpj in lista_orgaos():
            if (cnpj, janela.rotulo) in consultados or not precisa(contratos_ok.get(cnpj, set()), janela):
                continue
            try:
                buscar_contratos(cnpj, janela)
            except ErroAPI as exc:
                falhou(f"contratos {cnpj} {janela.rotulo}", exc)
                if estado["parar"]:
                    return

    interrompido = False
    try:
        for janela in ordem:
            if precisa(janelas_ok, janela):
                try:
                    buscar_contratacoes(janela)
                except ErroAPI as exc:
                    falhou(f"contratações {janela.rotulo}", exc)
            if not estado["parar"]:
                contratos_da_janela(janela)
            if estado["parar"]:
                break
        else:  # órgãos que só apareceram nos trimestres mais antigos: completa os contratos deles
            for janela in ordem:
                contratos_da_janela(janela)
                if estado["parar"]:
                    break
            else:  # por último, a renovação dos contratos gravados com a regra antiga (mais recentes primeiro)
                por_rotulo = {j.rotulo: j for j in todas}
                for cnpj, rotulo in sorted(renovar, key=lambda x: (x[1], x[0] == cnpj_principal), reverse=True):
                    if (cnpj, rotulo) in consultados or rotulo not in por_rotulo:
                        renovar.discard((cnpj, rotulo))
                        continue
                    try:
                        buscar_contratos(cnpj, por_rotulo[rotulo])
                    except ErroAPI as exc:
                        falhou(f"contratos {cnpj} {rotulo}", exc)
                        if estado["parar"]:
                            break
    except TempoEsgotado:
        interrompido = True
    interrompido = interrompido or estado["parar"]

    contratacoes = pd.concat([antigas, _tabela(novas, COLS_CONTRATACOES, tipar_contratacoes)],
                             ignore_index=True) if novas else antigas
    contratacoes = (contratacoes.drop_duplicates("id_pncp", keep="last")
                    .sort_values(["data_publicacao", "id_pncp"]).reset_index(drop=True))
    contratos = pd.concat([antigos, _tabela(novos, COLS_CONTRATOS, tipar_contratos)],
                          ignore_index=True) if novos else antigos
    contratos = (contratos.drop_duplicates("id_pncp", keep="last")
                 .sort_values(["data_publicacao", "id_pncp"]).reset_index(drop=True))

    cnpjs = lista_orgaos()
    contratos_pendentes = [f"{c} {j.rotulo}" for c in cnpjs for j in todas if j.rotulo not in contratos_ok.get(c, set())]
    pendentes = [j.rotulo for j in todas if j.rotulo not in janelas_ok] + contratos_pendentes
    status = ("falhou" if falhas and not novas and not novos
              else ("parcial" if interrompido or falhas or pendentes or renovar else "ok"))
    controle_novo = {
        "status": status,
        "inicio": inicio.isoformat(),
        "janelas_ok": sorted(janelas_ok),
        "contratos_ok": {k: sorted(v) for k, v in sorted(contratos_ok.items())},
        "pendentes": pendentes[:50],
        "contratos_pendentes": contratos_pendentes,
        "politica_fornecedor": POLITICA_FORNECEDOR,
        "renovar_contratos": sorted(f"{c} {r}" for c, r in renovar),
        "falhas": falhas,
        "modalidades_recusadas": sorted(recusadas),
        "contratacoes": int(len(contratacoes)),
        "contratos": int(len(contratos)),
        "orgaos": cnpjs,
        "coletado_em": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    return contratacoes[COLS_CONTRATACOES], contratos[COLS_CONTRATOS], controle_novo


def contratos_em_falta(controle: dict, ano: int | None = None) -> list[str]:
    """CNPJs dos órgãos cujos contratos ainda não foram coletados (no ano, se informado).

    Usa `contratos_pendentes` (coletor 1.2.2 em diante) ou, nos metadados antigos, os itens "CNPJ AAAAT#"
    de `pendentes`.
    """
    itens = controle.get("contratos_pendentes")
    if itens is None:
        itens = [p for p in controle.get("pendentes", []) if " " in str(p)]
    faltam = set()
    for item in itens:
        cnpj, _, rotulo = str(item).partition(" ")
        if cnpj and (ano is None or rotulo.startswith(str(ano))):
            faltam.add(cnpj)
    return sorted(faltam)


def contratados_por_compra(contratos: pd.DataFrame) -> pd.Series:
    """Fornecedor de cada contratação (pelo número de controle da compra), do contrato de maior valor.

    Uma contratação com contratos de várias empresas vira "EMPRESA A e mais 2". Pessoas físicas e MEI chegam
    com o nome e sem documento (LGPD); esta coluna é de tabela, então o nome aparece.
    """
    k = contratos[contratos["id_compra"].astype(str) != ""]
    if k.empty:
        return pd.Series(dtype=str)
    k = k.assign(_valor=k["valor_global"].fillna(0)).sort_values("_valor", ascending=False)

    def juntar(nomes: pd.Series) -> str:
        unicos = list(dict.fromkeys(n for n in nomes if n))
        if not unicos:
            return ""
        return unicos[0] if len(unicos) == 1 else f"{unicos[0]} e mais {len(unicos) - 1}"

    return k.groupby("id_compra")["fornecedor_nome"].agg(juntar)
