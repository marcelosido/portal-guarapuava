"""Clientes das APIs públicas usadas pelo portal.

SICONFI (Tesouro Nacional) – https://apidatalake.tesouro.gov.br/docs/siconfi/
    JSON paginado em blocos de até 5.000 linhas ({"items": [...], "hasMore": true/false, ...}).
PNCP (Portal Nacional de Contratações Públicas) – Manual das APIs de Consultas, versão 1.0
    JSON paginado ({"data": [...], "totalPaginas": n, "paginasRestantes": n, ...});
    HTTP 204 quando a consulta não tem resultado.

Nenhuma das duas exige chave de acesso.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import quote, urlencode

import requests

from . import __version__, config

log = logging.getLogger(__name__)

STATUS_TRANSITORIOS = {429, 500, 502, 503, 504}


class ErroAPI(RuntimeError):
    """Falha definitiva ao consultar a API."""

    def __init__(self, mensagem: str, status: int | None = None) -> None:
        super().__init__(mensagem)
        self.status = status


class TempoEsgotado(RuntimeError):
    """O tempo reservado para a coleta acabou; o restante fica para a próxima execução."""


class Prazo:
    """Relógio da execução: os módulos opcionais param quando o tempo combinado acaba."""

    def __init__(self, minutos: float | None) -> None:
        self.limite = None if minutos is None else time.monotonic() + 60 * minutos

    def restante(self) -> float:
        return float("inf") if self.limite is None else self.limite - time.monotonic()

    def esgotado(self) -> bool:
        return self.restante() <= 0


class _ClienteHTTP:
    def __init__(self, base_url: str, pausa: float, timeout: float, tentativas: int,
                 sessao: requests.Session | None, prazo: Prazo | None) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.pausa = pausa
        self.timeout = timeout
        self.tentativas = tentativas
        self.prazo = prazo
        self.sessao = sessao or requests.Session()
        self.sessao.headers.setdefault("User-Agent", f"portal-guarapuava/{__version__} (dados abertos)")
        self.sessao.headers.setdefault("Accept", "application/json")
        self.requisicoes = 0
        self._ultima_requisicao = 0.0

    def _respeitar_pausa(self) -> None:
        espera = self.pausa - (time.monotonic() - self._ultima_requisicao)
        if espera > 0:
            time.sleep(espera)

    def _verificar_prazo(self) -> None:
        if self.prazo is not None and self.prazo.esgotado():
            raise TempoEsgotado("tempo reservado para a coleta terminou")

    def _get(self, endpoint: str, params: dict[str, Any]) -> dict | None:
        """GET com novas tentativas em falhas temporárias. Devolve None em HTTP 204 (sem conteúdo)."""
        # Espaços viram %20 (e não "+"), como na documentação do SICONFI: "RREO-Anexo%2001".
        url = f"{self.base_url}{endpoint}?{urlencode(params, quote_via=quote)}"
        motivo = ""
        for tentativa in range(1, self.tentativas + 1):
            self._verificar_prazo()
            self._respeitar_pausa()
            espera = min(60.0, 2.0**tentativa)
            try:
                resp = self.sessao.get(url, timeout=self.timeout)
            except requests.RequestException as exc:
                motivo = f"{type(exc).__name__}: {exc}"
            else:
                self.requisicoes += 1
                if resp.status_code == 204:
                    return None
                if resp.status_code == 200:
                    try:
                        return resp.json()
                    except ValueError as exc:
                        motivo = f"resposta não é JSON ({exc})"
                elif resp.status_code in STATUS_TRANSITORIOS:
                    motivo = f"HTTP {resp.status_code}"
                    retry_after = resp.headers.get("Retry-After", "")
                    if retry_after.isdigit():
                        espera = min(120.0, float(retry_after))
                else:
                    raise ErroAPI(f"HTTP {resp.status_code} em {url}: {resp.text[:300]}", resp.status_code)
            finally:
                self._ultima_requisicao = time.monotonic()
            if tentativa < self.tentativas:
                if self.prazo is not None:
                    espera = min(espera, max(0.0, self.prazo.restante()))
                log.warning("Falha em %s (%s). Tentativa %d de %d; nova tentativa em %.0fs.",
                            endpoint, motivo, tentativa, self.tentativas, espera)
                time.sleep(espera)
        raise ErroAPI(f"Não foi possível consultar {url} após {self.tentativas} tentativas ({motivo}).")


class ClienteSiconfi(_ClienteHTTP):
    def __init__(
        self,
        base_url: str = config.BASE_URL,
        pausa: float = config.PAUSA_SEGUNDOS,
        timeout: float = config.TIMEOUT_SEGUNDOS,
        tentativas: int = config.TENTATIVAS,
        sessao: requests.Session | None = None,
        prazo: Prazo | None = None,
    ) -> None:
        super().__init__(base_url, pausa, timeout, tentativas, sessao, prazo)

    def paginar(self, endpoint: str, params: dict[str, Any]) -> list[dict]:
        """Busca todas as páginas de uma consulta, seguindo hasMore/offset."""
        itens: list[dict] = []
        offset = 0
        while True:
            dados = self._get(endpoint, {**params, "offset": offset}) or {}
            lote = dados.get("items") or []
            itens.extend(lote)
            if not dados.get("hasMore") or not lote:
                return itens
            offset += len(lote)

    # ------------------------------------------------------------- endpoints
    def msc_orcamentaria(
        self,
        id_ente: str,
        ano: int,
        mes: int,
        classe: int,
        tipo_valor: str = "ending_balance",
        tipo_matriz: str = "MSCC",
    ) -> list[dict]:
        """Matriz de Saldos Contábeis – contas orçamentárias (classes 5 e 6).

        tipo_valor="ending_balance" devolve o saldo ao fim do mês, que nas contas de
        execução da despesa é o acumulado do ano até aquele mês.
        """
        return self.paginar(
            "msc_orcamentaria",
            {
                "id_ente": id_ente,
                "an_referencia": ano,
                "me_referencia": mes,
                "co_tipo_matriz": tipo_matriz,
                "classe_conta": classe,
                "id_tv": tipo_valor,
            },
        )

    def rreo(self, id_ente: str, ano: int, bimestre: int, anexo: str = "RREO-Anexo 01",
             tipo: str = "RREO") -> list[dict]:
        """Relatório Resumido da Execução Orçamentária de municípios (esfera M).

        tipo="RREO Simplificado" para os municípios pequenos que adotam o relatório simplificado.
        """
        return self.paginar(
            "rreo",
            {
                "an_exercicio": ano,
                "nr_periodo": bimestre,
                "co_tipo_demonstrativo": tipo,
                "no_anexo": anexo,
                "co_esfera": "M",
                "id_ente": id_ente,
            },
        )

    def rgf(self, id_ente: str, ano: int, periodo: int, anexo: str, poder: str = "E",
            periodicidade: str = "Q", tipo: str = "RGF") -> list[dict]:
        """Relatório de Gestão Fiscal de um poder (E = Executivo, L = Legislativo).

        Quadrimestral (Q, períodos 1 a 3) ou, nos municípios com menos de 50 mil habitantes que
        optam pela divulgação semestral, "RGF Simplificado" semestral (S, períodos 1 e 2).
        """
        return self.paginar(
            "rgf",
            {
                "an_exercicio": ano,
                "in_periodicidade": periodicidade,
                "nr_periodo": periodo,
                "co_tipo_demonstrativo": tipo,
                "no_anexo": anexo,
                "co_esfera": "M",
                "co_poder": poder,
                "id_ente": id_ente,
            },
        )

    def dca(self, id_ente: str, ano: int, anexo: str) -> list[dict]:
        """Declaração de Contas Anuais (balanço do ano), ex.: "DCA-Anexo I-E" (despesa por função)."""
        return self.paginar("dca", {"an_exercicio": ano, "no_anexo": anexo, "id_ente": id_ente})

    def extrato_entregas(self, id_ente: str, ano: int) -> list[dict]:
        """Relatórios entregues pelo ente no ano: tipo (normal ou simplificado), periodicidade e situação."""
        return self.paginar("extrato_entregas", {"id_ente": id_ente, "an_referencia": ano})

    def entes(self) -> list[dict]:
        """Todos os entes da Federação: código IBGE, nome, UF, esfera, população e CNPJ."""
        return self.paginar("entes", {})


class ClientePNCP(_ClienteHTTP):
    TAMANHO_PAGINA = 50

    def __init__(
        self,
        base_url: str = config.PNCP_URL,
        pausa: float = config.PAUSA_PNCP,
        timeout: float = config.TIMEOUT_SEGUNDOS,
        tentativas: int = config.TENTATIVAS,
        sessao: requests.Session | None = None,
        prazo: Prazo | None = None,
    ) -> None:
        super().__init__(base_url, pausa, timeout, tentativas, sessao, prazo)

    def paginar(self, endpoint: str, params: dict[str, Any]) -> list[dict]:
        registros: list[dict] = []
        pagina = 1
        while True:
            dados = self._get(endpoint, {**params, "pagina": pagina, "tamanhoPagina": self.TAMANHO_PAGINA})
            if not dados:
                return registros
            lote = dados.get("data") or []
            registros.extend(lote)
            total_paginas = int(dados.get("totalPaginas") or 0)
            restantes = dados.get("paginasRestantes")
            if not lote or dados.get("empty") or pagina >= total_paginas or restantes == 0:
                return registros
            pagina += 1

    def contratacoes(self, data_inicial: str, data_final: str, modalidade: int, municipio_ibge: str) -> list[dict]:
        """Licitações e contratações diretas publicadas no período (datas AAAAMMDD), por modalidade."""
        return self.paginar("v1/contratacoes/publicacao", {
            "dataInicial": data_inicial, "dataFinal": data_final,
            "codigoModalidadeContratacao": modalidade, "codigoMunicipioIbge": municipio_ibge,
        })

    def contratos(self, data_inicial: str, data_final: str, cnpj_orgao: str) -> list[dict]:
        """Contratos e empenhos publicados no período por um órgão."""
        return self.paginar("v1/contratos", {
            "dataInicial": data_inicial, "dataFinal": data_final, "cnpjOrgao": cnpj_orgao,
        })
