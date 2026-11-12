"""Configurações do portal.

Todos os valores podem ser sobrescritos por variáveis de ambiente, o que permite
reaproveitar o mesmo código para outro município (basta trocar o código IBGE).
"""

from __future__ import annotations

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Ente federativo: código IBGE de 7 dígitos. 4109401 = Guarapuava - PR.
ID_ENTE = os.getenv("PORTAL_ID_ENTE", "4109401")
NOME_ENTE = os.getenv("PORTAL_NOME_ENTE", "Guarapuava - PR")

# Primeiro exercício com MSC na API para Guarapuava (consulta de 2018 volta vazia).
ANO_INICIAL = int(os.getenv("PORTAL_ANO_INICIAL", "2019"))

# API de dados abertos do SICONFI (Tesouro Nacional) – pública, sem autenticação.
URL_OFICIAL = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/"
BASE_URL = os.getenv("PORTAL_SICONFI_URL", URL_OFICIAL)

# Intervalo mínimo entre requisições, para não sobrecarregar o serviço público.
PAUSA_SEGUNDOS = float(os.getenv("PORTAL_PAUSA_SEGUNDOS", "1.0"))
TIMEOUT_SEGUNDOS = float(os.getenv("PORTAL_TIMEOUT_SEGUNDOS", "90"))
TENTATIVAS = int(os.getenv("PORTAL_TENTATIVAS", "5"))

# Quantos meses mais recentes são recoletados a cada execução. O município pode
# retificar a MSC depois do envio; recoletar os últimos meses captura essas correções.
MESES_RECOLETAR = int(os.getenv("PORTAL_MESES_RECOLETAR", "3"))

PASTA_DADOS = Path(os.getenv("PORTAL_PASTA_DADOS", str(RAIZ / "data")))

# Diferença máxima (em R$) para considerar MSC e RREO conciliados.
TOLERANCIA_CONCILIACAO = float(os.getenv("PORTAL_TOLERANCIA", "1.00"))

# Página de origem no portal da transparência do município (referência no rodapé).
URL_PORTAL_TRANSPARENCIA = os.getenv(
    "PORTAL_URL_TRANSPARENCIA",
    "https://guarapuava.atende.net/transparencia/item/demonstrativo-das-despesas",
)
