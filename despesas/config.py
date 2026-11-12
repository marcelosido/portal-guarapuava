"""Configurações do portal.

Todos os valores podem ser sobrescritos por variáveis de ambiente, o que permite
reaproveitar o mesmo código para outro município (basta trocar o código IBGE e o CNPJ).
"""

from __future__ import annotations

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Ente federativo: código IBGE de 7 dígitos. 4109401 = Guarapuava - PR.
ID_ENTE = os.getenv("PORTAL_ID_ENTE", "4109401")
NOME_ENTE = os.getenv("PORTAL_NOME_ENTE", "Guarapuava - PR")
UF = os.getenv("PORTAL_UF", "PR")
# CNPJ do município (PNCP: órgão "MUNICIPIO DE GUARAPUAVA", conferido em 12/11/2026).
CNPJ_MUNICIPIO = os.getenv("PORTAL_CNPJ", "76178037000176")

# Primeiro exercício com MSC na API para Guarapuava (consulta de 2018 volta vazia).
ANO_INICIAL = int(os.getenv("PORTAL_ANO_INICIAL", "2019"))

# API de dados abertos do SICONFI (Tesouro Nacional) – pública, sem autenticação.
URL_OFICIAL = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/"
BASE_URL = os.getenv("PORTAL_SICONFI_URL", URL_OFICIAL)

# API de consultas do PNCP (Portal Nacional de Contratações Públicas) – pública, sem autenticação.
URL_PNCP_OFICIAL = "https://pncp.gov.br/api/consulta/"
PNCP_URL = os.getenv("PORTAL_PNCP_URL", URL_PNCP_OFICIAL)
URL_PNCP_SITE = "https://pncp.gov.br/app"
# Desde quando buscar compras no PNCP (a Lei 14.133/2021 passou a valer sozinha em 2024).
PNCP_INICIO = os.getenv("PORTAL_PNCP_INICIO", "2024-01-01")

# Intervalo mínimo entre requisições, para não sobrecarregar os serviços públicos.
PAUSA_SEGUNDOS = float(os.getenv("PORTAL_PAUSA_SEGUNDOS", "1.0"))
PAUSA_PNCP = float(os.getenv("PORTAL_PAUSA_PNCP", "0.5"))
PAUSA_COMPARATIVO = float(os.getenv("PORTAL_PAUSA_COMPARATIVO", "0.5"))
TIMEOUT_SEGUNDOS = float(os.getenv("PORTAL_TIMEOUT_SEGUNDOS", "90"))
TENTATIVAS = int(os.getenv("PORTAL_TENTATIVAS", "5"))

# Tempo máximo de uma execução do coletor, em minutos. O robô do GitHub encerra o trabalho
# em 90 minutos; o que não couber (comparação entre cidades, na 1ª vez) continua na próxima execução.
TEMPO_MAXIMO_MIN = float(os.getenv("PORTAL_TEMPO_MAXIMO", "70"))

# Quantos meses mais recentes são recoletados a cada execução. O município pode
# retificar a MSC depois do envio; recoletar os últimos meses captura essas correções.
MESES_RECOLETAR = int(os.getenv("PORTAL_MESES_RECOLETAR", "3"))

PASTA_DADOS = Path(os.getenv("PORTAL_PASTA_DADOS", str(RAIZ / "data")))
PASTA_RECURSOS = Path(__file__).resolve().parent / "recursos"

# Diferença máxima (em R$) para considerar MSC e RREO conciliados.
TOLERANCIA_CONCILIACAO = float(os.getenv("PORTAL_TOLERANCIA", "1.00"))

# Página de origem no portal da transparência do município (referência no rodapé).
URL_PORTAL_TRANSPARENCIA = os.getenv(
    "PORTAL_URL_TRANSPARENCIA",
    "https://guarapuava.atende.net/transparencia/item/demonstrativo-das-despesas",
)
URL_REPOSITORIO = os.getenv("PORTAL_URL_REPOSITORIO", "https://github.com/marcelosido/portal-guarapuava")
