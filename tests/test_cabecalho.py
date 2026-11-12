"""Cabeçalho do portal e cores dos temas: o desenho, o CSS e o config.toml precisam andar juntos."""

import re
import tomllib
from pathlib import Path

from despesas import config
from despesas.painel import TOKENS

RAIZ = Path(__file__).resolve().parent.parent
SVG = (config.PASTA_RECURSOS / "cabecalho.svg").read_text(encoding="utf-8")
CSS = (config.PASTA_RECURSOS / "cabecalho.css").read_text(encoding="utf-8")


def test_desenho_e_decorativo_e_se_ajusta_a_faixa():
    assert SVG.startswith("<svg") and SVG.rstrip().endswith("</svg>")
    assert 'aria-hidden="true"' in SVG                      # o nome do portal é texto de verdade, fora do desenho
    assert 'viewBox="0 0 1600 300"' in SVG and 'preserveAspectRatio="xMidYMax slice"' in SVG
    assert "<script" not in SVG and "href" not in SVG       # nada executável nem externo
    assert "\n\n" not in SVG                                 # linha em branco quebraria o bloco HTML do Markdown


def test_cada_cor_do_desenho_tem_versao_de_dia_e_de_noite():
    classes = set(re.findall(r'class="(gp-[a-z0-9]+)"', SVG)) - {"gp-arte"}
    assert classes, "o desenho deveria usar classes de cor"
    for classe in sorted(classes):
        regra = re.search(rf"\.{classe}\s*\{{([^}}]*)\}}", CSS)
        assert regra, f"{classe} sem regra no cabecalho.css"
        assert "light-dark(" in regra.group(1), f"{classe} sem versão para o tema escuro"


def test_fundo_e_texto_do_tema_iguais_aos_dos_graficos():
    tema = tomllib.loads((RAIZ / ".streamlit" / "config.toml").read_text(encoding="utf-8"))["theme"]
    for modo in ("light", "dark"):
        assert tema[modo]["backgroundColor"].lower() == TOKENS[modo]["superficie"].lower()
        assert tema[modo]["textColor"].lower() == TOKENS[modo]["tinta"].lower()
