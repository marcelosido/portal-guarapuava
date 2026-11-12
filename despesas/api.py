"""Cliente da API de dados abertos do SICONFI (Tesouro Nacional).

Documentação: https://apidatalake.tesouro.gov.br/docs/siconfi/
A API é pública, não exige chave e devolve JSON paginado em blocos de até 5.000
linhas ({"items": [...], "hasMore": true/false, "offset": n, ...}).
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


class ClienteSiconfi:
    def __init__(
        self,
        base_url: str = config.BASE_URL,
        pausa: float = config.PAUSA_SEGUNDOS,
        timeout: float = config.TIMEOUT_SEGUNDOS,
        tentativas: int = config.TENTATIVAS,
        sessao: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.pausa = pausa
        self.timeout = timeout
        self.tentativas = tentativas
        self.sessao = sessao or requests.Session()
        self.sessao.headers.setdefault("User-Agent", f"portal-despesas/{__version__} (dados abertos SICONFI)")
        self.requisicoes = 0
        self._ultima_requisicao = 0.0

    # ------------------------------------------------------------------ HTTP
    def _respeitar_pausa(self) -> None:
        espera = self.pausa - (time.monotonic() - self._ultima_requisicao)
        if espera > 0:
            time.sleep(espera)

    def _get(self, endpoint: str, params: dict[str, Any]) -> dict:
        # Espaços viram %20 (e não "+"), como na documentação da API: "RREO-Anexo%2001".
        url = f"{self.base_url}{endpoint}?{urlencode(params, quote_via=quote)}"
        motivo = ""
        for tentativa in range(1, self.tentativas + 1):
            self._respeitar_pausa()
            espera = min(60.0, 2.0**tentativa)
            try:
                resp = self.sessao.get(url, timeout=self.timeout)
            except requests.RequestException as exc:
                motivo = f"{type(exc).__name__}: {exc}"
            else:
                self.requisicoes += 1
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
                    raise ErroAPI(f"HTTP {resp.status_code} em {url}: {resp.text[:300]}")
            finally:
                self._ultima_requisicao = time.monotonic()
            if tentativa < self.tentativas:
                log.warning("Falha em %s (%s). Tentativa %d de %d; nova tentativa em %.0fs.",
                            endpoint, motivo, tentativa, self.tentativas, espera)
                time.sleep(espera)
        raise ErroAPI(f"Não foi possível consultar {url} após {self.tentativas} tentativas ({motivo}).")

    def paginar(self, endpoint: str, params: dict[str, Any]) -> list[dict]:
        """Busca todas as páginas de uma consulta, seguindo hasMore/offset."""
        itens: list[dict] = []
        offset = 0
        while True:
            dados = self._get(endpoint, {**params, "offset": offset})
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

    def rreo(self, id_ente: str, ano: int, bimestre: int, anexo: str = "RREO-Anexo 01") -> list[dict]:
        """Relatório Resumido da Execução Orçamentária de municípios (esfera M)."""
        return self.paginar(
            "rreo",
            {
                "an_exercicio": ano,
                "nr_periodo": bimestre,
                "co_tipo_demonstrativo": "RREO",
                "no_anexo": anexo,
                "co_esfera": "M",
                "id_ente": id_ente,
            },
        )

    def rgf(self, id_ente: str, ano: int, quadrimestre: int, anexo: str, poder: str = "E") -> list[dict]:
        """Relatório de Gestão Fiscal quadrimestral de um poder (E = Executivo, L = Legislativo)."""
        return self.paginar(
            "rgf",
            {
                "an_exercicio": ano,
                "in_periodicidade": "Q",
                "nr_periodo": quadrimestre,
                "co_tipo_demonstrativo": "RGF",
                "no_anexo": anexo,
                "co_esfera": "M",
                "co_poder": poder,
                "id_ente": id_ente,
            },
        )
