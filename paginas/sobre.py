"""Página "Sobre os dados": fontes, atualização, conferência, critérios dos pontos de atenção e downloads."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from despesas import config
from despesas.alertas import (DESCONTO_MINIMO, EXECUCAO_BAIXA, MIN_DISPENSAS_MESMO_FORNECEDOR,
                              PRAZO_MINIMO_DIAS_UTEIS)
from despesas.formatacao import brl, numero, pct
from despesas.painel import (assinatura, cabecalho, carregar_despesa, coletado_em, ler_metadados, mes_extenso,
                             pacote_dados_abertos, pasta_dados, selo_md, tabela)
from despesas.pncp import contratos_em_falta
from despesas.transformacao import NOMES_MEDIDAS

PASTA = pasta_dados()
meta = ler_metadados(PASTA)
nome_ente = meta.get("nome_ente", config.NOME_ENTE)
pncp, comp = meta.get("pncp", {}), meta.get("comparativo", {})

cabecalho("Sobre os dados", f"De onde vem cada número do portal, quando ele é atualizado, como é conferido e como "
          f"baixar tudo. Os dados são públicos e oficiais: foram enviados pelos próprios órgãos de {nome_ente.split(' - ')[0]} "
          "ao Tesouro Nacional e ao Portal Nacional de Contratações Públicas.")


def periodo(chave: str, rotulo: str) -> str:
    valor = meta.get(chave)
    if not valor:
        return "–"
    a, p = valor.split("-")
    return f"{p}º {rotulo}/{a}"


# ----------------------------------------------------------------------------- fontes
st.subheader("De onde vêm os dados")
fontes = pd.DataFrame([
    ["Matriz de Saldos Contábeis (MSC), Tesouro Nacional", "Despesas: por função, natureza e órgão", "Mensal",
     mes_extenso(meta.get("ultimo_mes", ""))],
    ["Relatório Resumido da Execução Orçamentária (RREO), Anexos 1, 3 e 14", "Visão geral e Receitas", "A cada 2 meses",
     periodo("ultimo_rreo", "bimestre")],
    ["Relatório de Gestão Fiscal (RGF), Anexos 1 e 2", "Gasto com pessoal e dívida", "A cada 4 meses",
     periodo("ultimo_rgf", "quadrimestre")],
    ["Portal Nacional de Contratações Públicas (PNCP)", "Compras e contratos", "Contínua",
     pd.Timestamp(pncp["coletado_em"]).strftime("%d/%m/%Y") if pncp.get("coletado_em") else "ainda não coletado"],
    ["RREO, RGF e Balanço Anual (DCA) de todos os municípios do PR", "Comparar cidades", "Anual",
     f"ano de {comp['ano']}" if comp.get("ano") else "ainda não coletado"],
], columns=["Fonte", "Onde aparece", "Periodicidade", "Último dado"])
st.dataframe(fontes, hide_index=True, column_config={"Fonte": st.column_config.Column(width="large")})
st.markdown(
    f"""
- API do Tesouro Nacional (SICONFI): [apidatalake.tesouro.gov.br]({config.URL_OFICIAL}) – a mesma base usada pelo
  Tesouro para acompanhar as contas de estados e municípios.
- API do PNCP: [pncp.gov.br]({config.URL_PNCP_SITE}) – onde, pela Lei 14.133/2021, todo órgão público publica
  editais, avisos de contratação direta e contratos.
- Valores como publicados pelo município, sem correção pela inflação e sem ajustes.
"""
)

# -------------------------------------------------------------------------- atualização
st.subheader("Atualização")
st.markdown(
    f"Um robô do GitHub busca os dados toda **segunda-feira de manhã** e o portal se atualiza sozinho. Última "
    f"coleta: **{coletado_em(meta)}**. O município envia a MSC e os relatórios até 30 dias depois de cada período, "
    "por isso os dados têm cerca de um mês de defasagem em relação ao portal da transparência."
)
situacao = {"ok": "ok", "parcial": "info", "falhou": "critico"}
linhas = [f"{selo_md('ok' if not meta.get('falhas') else 'alerta')} **Dados do município** – "
          f"{meta.get('meses', '–')} meses de MSC, {meta.get('requisicoes', '–')} consultas na última coleta"]
if pncp:
    sem_contratos = contratos_em_falta(pncp)
    linhas.append(f"{selo_md(situacao.get(pncp.get('status'), 'info'))} **Compras (PNCP)** – "
                  f"{numero(pncp.get('contratacoes', 0), 0)} contratações e {numero(pncp.get('contratos', 0), 0)} contratos"
                  + (f" · faltam os contratos de {len(sem_contratos)} "
                     f"{'órgão' if len(sem_contratos) == 1 else 'órgãos'}"
                     + (", entre eles a Prefeitura" if config.CNPJ_MUNICIPIO in sem_contratos else "")
                     if sem_contratos else "")
                  + (" · parte das consultas fica para a próxima coleta" if pncp.get("status") == "parcial" else ""))
if comp:
    linhas.append(f"{selo_md(situacao.get(comp.get('status'), 'info'))} **Comparação entre cidades** – "
                  f"{comp.get('com_dados', 0)} de {comp.get('municipios', 0)} municípios com dados de {comp.get('ano', '–')}"
                  + (" · a coleta continua nas próximas execuções" if comp.get("status") == "parcial" else ""))
st.markdown("  \n".join(linhas))
pendencias = []
if meta.get("meses_ainda_nao_publicados"):
    pendencias.append(f"MSC ainda não publicada: {', '.join(meta['meses_ainda_nao_publicados'])}")
if meta.get("relatorios_ausentes"):
    pendencias.append(f"Relatórios procurados e ainda não publicados: {', '.join(meta['relatorios_ausentes'])}")
if comp.get("relatorios_nao_entregues"):
    pendencias.append(f"Municípios que ainda não entregaram algum relatório de {comp.get('ano')}: "
                      f"{', '.join(comp['relatorios_nao_entregues'][:15])}"
                      + ("…" if len(comp["relatorios_nao_entregues"]) > 15 else ""))
if pendencias:
    with st.expander("Pendências"):
        st.markdown("\n".join(f"- {p}" for p in pendencias))

# ------------------------------------------------------------------------- conferência
st.subheader("Conferência dos dados")
st.markdown(
    "A despesa detalhada vem da MSC, mês a mês. No fim de cada bimestre, os totais calculados a partir dela são "
    "comparados com a linha **Total das despesas** do RREO Anexo 1, que o próprio município publica. "
    f"Diferenças de até {brl(config.TOLERANCIA_CONCILIACAO)} contam como conciliadas."
)
arq_fato = PASTA / "fDespesa.parquet"
conciliacao = carregar_despesa(str(PASTA), assinatura(arq_fato))[1] if arq_fato.exists() else pd.DataFrame()
if conciliacao.empty:
    st.info("Ainda não há bimestre fechado para conferir.")
else:
    conc = conciliacao.copy()
    contagem = conc["status"].value_counts()
    s1, s2, s3 = st.columns(3)
    s1.metric("Conciliadas", int(contagem.get("Conciliado", 0)), border=True)
    s2.metric("Divergentes", int(contagem.get("Divergente", 0)), border=True)
    s3.metric("Sem RREO publicado", int(contagem.get("RREO indisponível", 0)), border=True)
    if st.toggle("Mostrar só divergências"):
        conc = conc[conc["status"] == "Divergente"]
    icones = {"Conciliado": "✔ Conciliado", "Divergente": "✖ Divergente", "RREO indisponível": "… sem RREO"}
    conc = conc.sort_values(["ano", "bimestre"], ascending=False).assign(
        medida=lambda d: d["medida"].map(NOMES_MEDIDAS), status=lambda d: d["status"].map(icones),
        bimestre=lambda d: d["bimestre"].astype(int).astype(str) + "º",
    )[["ano", "bimestre", "medida", "valor_msc", "valor_rreo", "diferenca", "status"]]
    conc.columns = ["Exercício", "Bimestre", "Medida", "MSC", "RREO", "Diferença (MSC − RREO)", "Situação"]
    tabela(conc, monetarias=["MSC", "RREO", "Diferença (MSC − RREO)"], altura=380)
    st.caption(
        "Como ler as divergências: uma diferença pequena e constante na dotação costuma vir do próprio envio do "
        "município (em ago/2026, a dotação da MSC de Guarapuava ficou R$ 1.469,54 acima da do RREO, enquanto "
        "empenhado, liquidado e pago bateram ao centavo). Diferenças maiores no 6º bimestre podem vir dos "
        "lançamentos de encerramento do ano, que entram no RREO e não na MSC de dezembro – é uma hipótese, a "
        "confirmar com a contabilidade do município."
    )

# -------------------------------------------------------------- pontos de atenção
st.subheader("Como os pontos de atenção são calculados")
st.markdown("Cada ponto segue uma regra fixa, aplicada igualmente a todos os dados. Um ponto de atenção não é "
            "acusação nem indício de irregularidade: indica um número que vale a pena acompanhar ou conferir.")
regras = pd.DataFrame([
    ["Gasto com pessoal", "Acima de 90% (alerta), 95% (prudencial) ou 100% (máximo) do limite da LRF: 54% da "
     "receita corrente líquida na Prefeitura, 6% na Câmara.", "RGF Anexo 1", "LRF, arts. 20, 22 e 59"],
    ["Dívida", "Dívida consolidada líquida acima de 108% (alerta) ou 120% da receita corrente líquida.",
     "RGF Anexo 2", "Resolução do Senado 40/2001"],
    ["Educação, FUNDEB e saúde", "Abaixo do mínimo no ano fechado (25%, 70% e 15%). No ano em andamento, aparece só "
     "como acompanhamento.", "RREO Anexo 14", "Constituição, arts. 198 e 212; Lei 14.113/2020"],
    ["Meta fiscal e déficit", "Resultado primário abaixo da meta da LDO, ou receitas menores que as despesas "
     "liquidadas, no ano fechado.", "RREO Anexo 14", "LRF, arts. 4º e 9º"],
    ["Receitas de capital e investimentos", f"Menos de {pct(EXECUCAO_BAIXA, 0)} do previsto (ou autorizado) "
     "realizado depois de dois terços do ano.", "RREO Anexo 1 e MSC", "–"],
    ["Contratações emergenciais", "Dispensas com amparo no art. 75, VIII (emergência ou calamidade).", "PNCP",
     "Lei 14.133/2021, art. 75, VIII"],
    ["Várias dispensas com o mesmo fornecedor", f"{MIN_DISPENSAS_MESMO_FORNECEDOR} ou mais contratos ligados a "
     "dispensas por valor com a mesma empresa no ano.", "PNCP", "Lei 14.133/2021, art. 75, § 1º"],
    ["Prazo curto para propostas", f"Pregão ou concorrência com menos de {PRAZO_MINIMO_DIAS_UTEIS} dias de segunda "
     "a sexta entre a publicação no PNCP e o fim das propostas.", "PNCP", "Lei 14.133/2021, art. 55"],
    ["Licitação sem desconto", f"Valor homologado a menos de {pct(DESCONTO_MINIMO, 0)} do estimado.", "PNCP", "–"],
    ["Contratação direta e concentração", "Parte do valor por dispensa e inexigibilidade; participação dos cinco "
     "maiores fornecedores (mostrado quando passa de 50%).", "PNCP", "–"],
], columns=["Ponto", "Regra", "Fonte", "Referência"])
st.dataframe(regras, hide_index=True, column_config={"Regra": st.column_config.Column(width="large")})

# --------------------------------------------------------------------------------- LGPD
st.subheader("Dados pessoais")
st.markdown(
    "O portal mostra valores agregados e dados de empresas, que são públicos. Para fornecedores **pessoa física e "
    "microempreendedores individuais (MEI)**, segue a Lei Geral de Proteção de Dados (Lei 13.709/2018) como os "
    "portais oficiais de transparência: **o nome aparece nas tabelas, mas nenhum número de documento** (nem CPF, "
    "nem o CNPJ do MEI), e nos rankings e pontos de atenção eles aparecem somados num grupo só, sem destaque "
    "individual. Números com formato de CPF em textos livres são substituídos por asteriscos – também nos arquivos "
    "para download. A publicação completa continua disponível no PNCP, que é a fonte oficial."
)

# ---------------------------------------------------------------------------- downloads
st.subheader("Baixar os dados")
st.markdown("Todos os arquivos usam ponto e vírgula como separador e vírgula decimal, e abrem direto no Excel.")
b1, b2 = st.columns([1, 2], vertical_alignment="center")
if arq_fato.exists():
    b1.download_button("Baixar tudo (ZIP)", pacote_dados_abertos(str(PASTA), assinatura(arq_fato)),
                       file_name="dados_abertos_portal.zip", mime="application/zip", icon=":material/folder_zip:")
b2.markdown(f"Ou veja arquivo por arquivo na [pasta de dados do projeto]({config.URL_REPOSITORIO}/tree/main/data).")
arquivos = pd.DataFrame([
    ["fDespesa (parquet; CSV no ZIP)", "Despesa por ano, mês, órgão, função, subfunção, natureza e fonte"],
    ["fIndicadores.csv", "Indicadores do RREO e do RGF por período"],
    ["fReceitaCorrente.csv", "Receita mês a mês por imposto e transferência (RREO Anexo 3)"],
    ["fContratacoes.csv, fContratos.csv", "Compras e contratos dos órgãos municipais (PNCP)"],
    ["dMunicipios.csv, fComparativo.csv", "Indicadores dos municípios do PR no último ano fechado"],
    ["dNatureza.csv, dFuncao.csv, dPoderOrgao.csv", "Descrição dos códigos"],
    ["conciliacao_rreo.csv, metadados.json", "Conferência MSC × RREO e informações da coleta"],
], columns=["Arquivo", "Conteúdo"])
st.dataframe(arquivos, hide_index=True)

# ---------------------------------------------------------------------- limitações
with st.expander("Limitações"):
    st.markdown(
        """
- Histórico desde 2019, primeiro ano com MSC na API para Guarapuava; compras desde 2024 no PNCP.
- A MSC separa só Executivo, previdência (RPPS) e Legislativo; fundos e fundações entram no Executivo.
- Compras publicadas apenas no portal da transparência ou no Diário Oficial podem não estar no PNCP.
- Prazos de licitação contados em dias de segunda a sexta, sem descontar feriados.
- Na comparação entre cidades, cada prefeitura classifica seus gastos por função à sua maneira.
- Em agosto/2026, o RREO de Guarapuava trouxe o mesmo percentual (25,71%) para educação e saúde: é o dado
  publicado, que vale conferir com a prefeitura.
"""
    )
with st.expander("Glossário"):
    st.markdown(
        """
- **Dotação**: valor autorizado no orçamento para uma despesa. **Atualizada** inclui os créditos adicionais.
- **Empenho**: reserva do dinheiro para uma despesa. **Liquidação**: confirmação de que o serviço foi prestado ou o
  bem entregue. **Pagamento**: saída do dinheiro.
- **Restos a pagar**: despesas empenhadas em um ano e pagas em anos seguintes.
- **Receita corrente líquida (RCL)**: receitas correntes dos últimos 12 meses menos deduções obrigatórias; é a
  base dos limites da LRF.
- **Resultado primário**: receitas menos despesas, sem juros; mostra se o município gasta mais do que arrecada.
- **Dispensa / inexigibilidade**: contratação direta, sem licitação, nos casos previstos em lei.
- **Homologação**: aprovação do resultado da licitação pela autoridade competente.
"""
    )
