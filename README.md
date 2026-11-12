# Guarapuava em números

Portal público de indicadores fiscais do município: orçamento previsto × realizado, limites da Lei de
Responsabilidade Fiscal, mínimos de educação e saúde, meta fiscal, previdência e a despesa detalhada.
Os dados vêm da API pública do Tesouro Nacional (SICONFI) e são atualizados toda semana por um robô do
GitHub Actions. O site roda no Streamlit Community Cloud.

> Para publicar sem programar, siga o documento **"Passo a passo: portal público de indicadores de
> Guarapuava"**: criar o repositório, ligar o robô e publicar no Streamlit, tudo pelo navegador.

## Como funciona

```
API do SICONFI  ──▶  robô (GitHub Actions, segundas 06:17)  ──▶  pasta data/ no GitHub  ──▶  Streamlit Cloud  ──▶  portal
                     .github/workflows/atualizar-dados.yml       (CSV + parquet)             app.py
```

| Fonte (SICONFI) | Periodicidade | O que alimenta |
|---|---|---|
| RREO Anexo 14 (demonstrativo simplificado) | bimestral | receita prevista × arrecadada, despesa autorizada × liquidada, resultado, RCL, educação, FUNDEB, saúde, meta primária, previdência, restos a pagar |
| RREO Anexo 1 | bimestral | receita por origem; total da despesa para conferir a MSC |
| RGF Anexo 1 (Executivo e Legislativo) | quadrimestral | gasto com pessoal e limites (alerta, prudencial, máximo) |
| RGF Anexo 2 (Executivo) | quadrimestral | dívida consolidada bruta e líquida |
| MSC orçamentária (classes 5 e 6) | mensal | despesa detalhada por natureza, função e poder/órgão; investimentos |

Os indicadores são lidos pelos códigos `cod_conta` que a própria API devolve (conferidos em 30/10/2026);
quando um código não aparece, o indicador fica em branco – nada é estimado.

## Páginas do portal

- **Indicadores** (inicial): previsto × realizado no ano, cartões com semáforo (cor + ícone + texto) para
  pessoal, dívida, educação, FUNDEB, saúde, meta e previdência, evolução desde 2019 e receita por origem.
- **Despesa detalhada**: execução por função, grupo e natureza, mês a mês; demonstrativo no formato do
  portal da transparência; download da base em CSV; conferência MSC × RREO.

## Rodar no seu computador (opcional)

Requer Python 3.10 ou superior.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python coletar.py                   # 1ª vez: 2019 até hoje (~550 requisições, 20 a 40 min)
streamlit run app.py                # abre em http://localhost:8501
python -m pytest                    # 46 testes
```

Opções do coletor: `--anos 2024 2026` (intervalo), `--completo` (recoleta tudo), `--csv` (grava também o
`fDespesa.csv` completo, para Excel ou Power BI) e `--help`.

## Arquivos em `data/`

| Arquivo | Conteúdo |
|---|---|
| `fIndicadores.csv` | Indicadores do RREO e do RGF: `relatorio`, `ano`, `periodo`, `poder` (E/L no RGF), `chave`, `valor` |
| `fDespesa.parquet` | Despesa da MSC por ano, mês, poder/órgão, função, subfunção, natureza e fonte, com dotação inicial e atualizada, empenhado, liquidado e pago acumulados no ano |
| `dNatureza.csv`, `dFuncao.csv`, `dPoderOrgao.csv` | Descrições dos códigos |
| `rreo_totais.csv`, `conciliacao_rreo.csv` | Conferência da MSC com o total do RREO a cada bimestre |
| `metadados.json` | Data da coleta, períodos, relatórios ainda não publicados, falhas |

Os CSVs usam `;` e vírgula decimal. Quando nada muda na fonte, os arquivos ficam idênticos byte a byte e o
Git não registra mudança; só `metadados.json` (data da coleta) muda toda semana.

## Como validar

1. **Testes** – `python -m pytest`. A extração dos indicadores é testada com linhas copiadas da API real
   (`tests/fixtures_api.py`); a coleta, com uma API simulada no mesmo formato (`tests/servidor_simulado.py`).
2. **Valores de referência** (API consultada em 30/10/2026, Guarapuava, RREO e RGF até agosto/2026):
   receita arrecadada R$ 726.358.549,65 de R$ 1.171.101.596,73 previstos; despesa liquidada
   R$ 676.044.444,25 de R$ 1.302.417.760,30 autorizados; RCL R$ 929.125.228,65; pessoal da Prefeitura
   51,07% da RCL (alerta 48,6%); Câmara 2,91%; dívida consolidada líquida −2,21%; educação 25,71%; FUNDEB
   91,75%; saúde 25,71%.
3. **MSC × RREO** – aba "Conferência dos dados" (página Despesa detalhada). Em agosto/2026, empenhado,
   liquidado e pago bateram ao centavo; a dotação da MSC ficou R$ 1.469,54 acima do RREO, diferença do
   próprio envio do município.
4. **Portal da transparência × portal** – exporte o Demonstrativo das Despesas do Atende (Dados Abertos,
   CSV) e rode `python conciliar_atende.py Demonstrativo.csv --ano 2026 --mes 8`. O leitor do CSV foi
   testado com arquivo simulado; confirme com um arquivo real.

## Limitações

- Defasagem de cerca de um mês em relação ao portal da transparência (a MSC e os relatórios são enviados
  depois do fim de cada período).
- A MSC só separa Executivo (10131), RPPS (10132) e Legislativo (20231); fundos e fundações ficam no
  Executivo. Os rótulos foram inferidos dos dados – confirme com a tabela de Poder/Órgão da STN.
- Histórico a partir de 2019 (primeiro ano com MSC na API para Guarapuava).
- Educação e saúde aparecem com o mesmo percentual (25,71%) no RREO de agosto/2026 – conferir com a prefeitura.
- Não confirmado ainda: se os servidores do GitHub Actions acessam a API do Tesouro. Se não, rode a coleta
  num computador e envie a pasta `data/`.

## Outro município

```bash
PORTAL_ID_ENTE=4106902 PORTAL_NOME_ENTE="Curitiba - PR" python coletar.py --pasta data_curitiba
```

No portal publicado, troque `ID_ENTE` e `NOME_ENTE` em `despesas/config.py`. Os rótulos de poder/órgão em
`despesas/dicionarios.py` são de Guarapuava.

## Estrutura

```
app.py                       navegação entre as páginas
paginas/indicadores.py       página inicial
paginas/despesa.py           despesa detalhada
coletar.py                   coleta + transformação + conferência
conciliar_atende.py          conferência com o CSV do portal da transparência
despesas/                    api.py, indicadores.py, transformacao.py, painel.py, dicionarios.py, config.py
tests/                       testes, linhas reais da API e API simulada
.github/workflows/           robô de atualização
.streamlit/config.toml       tema claro/escuro
```
