# Guarapuava em números

Portal público com as contas da Prefeitura de Guarapuava (PR): orçamento previsto × realizado, limites da Lei de
Responsabilidade Fiscal, mínimos de educação e saúde, receitas por imposto, despesa detalhada, compras e contratos
publicados no PNCP, comparação com os outros 398 municípios do Paraná e **pontos de atenção** calculados com regras
fixas. Tudo com dados abertos oficiais, atualizados toda semana por um robô do GitHub Actions. O site roda no
Streamlit Community Cloud.

> Para publicar ou atualizar sem programar, siga o documento **"Passo a passo: portal público de indicadores de
> Guarapuava"**.

## Como funciona

```
APIs públicas  ──▶  robô (GitHub Actions, segundas 06:17)  ──▶  pasta data/ no GitHub  ──▶  Streamlit Cloud  ──▶  portal
SICONFI, PNCP       .github/workflows/atualizar-dados.yml       (CSV + parquet)             app.py
```

| Fonte | Periodicidade | O que alimenta |
|---|---|---|
| SICONFI – RREO Anexo 14 (demonstrativo simplificado) | bimestral | previsto × realizado, resultado, RCL, educação, FUNDEB, saúde, meta, previdência, restos a pagar |
| SICONFI – RREO Anexo 1 | bimestral | receita por origem; total da despesa para conferir a MSC |
| SICONFI – RREO Anexo 3 | bimestral | receita mês a mês por imposto e transferência (IPTU, ISS, FPM, ICMS, FUNDEB...) |
| SICONFI – RGF Anexos 1 e 2 | quadrimestral | gasto com pessoal (Prefeitura e Câmara) e dívida |
| SICONFI – MSC orçamentária (classes 5 e 6) | mensal | despesa detalhada por natureza, função e poder/órgão; investimentos |
| PNCP – contratações e contratos | contínua | compras dos órgãos municipais, pontos de atenção das compras |
| SICONFI – extrato de entregas, RREO 14, RGF 1, DCA I-D e I-E de cada município do PR | anual | página Comparar cidades |

Os indicadores são lidos pelos códigos `cod_conta` que a própria API devolve (conferidos em 30/10 e 12/11/2026);
quando um código não aparece, o indicador fica em branco – nada é estimado.

## Páginas do portal

- **Visão geral**: pontos de atenção (contas e compras), previsto × realizado, cartões com semáforo (cor + ícone +
  texto) para pessoal, dívida, educação, FUNDEB, saúde, meta e previdência, e a evolução desde 2019.
- **Receitas**: impostos e transferências nos últimos 12 meses, mês a mês, previsto × arrecadado por origem e
  evolução anual.
- **Despesas**: execução por função, grupo e natureza, mês a mês; demonstrativo no formato do portal da
  transparência; download em CSV.
- **Compras**: licitações, dispensas e contratos do PNCP, com pontos de atenção (emergenciais, várias dispensas com o
  mesmo fornecedor, prazo curto para propostas, licitações sem desconto, contratação direta, concentração),
  quem foi contratado em cada licitação ou dispensa (quando o contrato já está no PNCP), propostas abertas e links
  para cada publicação oficial.
- **Comparar cidades**: mapa do Paraná (clique para escolher a cidade) e a sua cidade ao lado de outra em educação,
  saúde, transporte, salários, investimentos e receita por habitante. Para cada indicador, uma faixa do 1º ao
  último lugar (em cinco partes, nas cores do mapa) marca a posição das duas cidades, e o ranking completo fica numa
  tabela. Os percentuais de educação e saúde vêm do resumo do RREO (Anexo 14), que só parte dos municípios
  preenche: em 2025, cerca de 220 de 393.
- **Sobre os dados**: fontes, atualização, conferência MSC × RREO, critérios dos pontos de atenção, LGPD e downloads.

Todas as páginas abrem com o cabeçalho **"Planalto com geada"** (campos com araucárias, geada e sol nascendo). No
tema escuro, a mesma cena aparece à noite, com lua e estrelas. As cores do portal saem do cabeçalho: no tema claro, fundo azul-geada
(`#f5f8fc`) e texto azul-marinho (`#15253b`); no escuro, fundo azul-noite (`#0d1626`) e texto `#e7edf5`. Elas ficam em
`.streamlit/config.toml`, e as mesmas cores de fundo e texto ficam em `TOKENS`, em `despesas/painel.py`, porque os
gráficos usam essas cores. Um teste confere se as duas estão iguais.

## Pontos de atenção

Um ponto de atenção não é acusação nem indício de irregularidade: é um número que passa de um limite legal ou que
merece acompanhamento. As regras ficam em `despesas/alertas.py` e são explicadas na página "Sobre os dados".

| Ponto | Regra |
|---|---|
| Gasto com pessoal | acima de 90% (alerta), 95% (prudencial) ou 100% do limite da LRF (54% Prefeitura, 6% Câmara) |
| Dívida | dívida consolidada líquida acima de 108% ou 120% da RCL |
| Educação, FUNDEB, saúde | abaixo do mínimo no ano fechado (no ano em andamento, só acompanhamento) |
| Meta e déficit | resultado primário abaixo da meta da LDO ou déficit orçamentário, no ano fechado |
| Receitas de capital, investimentos | menos de 25% do previsto/autorizado depois de 2/3 do ano |
| Emergenciais | dispensas pelo art. 75, VIII, da Lei 14.133/2021 |
| Mesmo fornecedor | 3 ou mais contratos ligados a dispensas por valor (art. 75, I e II) com a mesma empresa no ano |
| Prazo curto | pregão/concorrência com menos de 8 dias úteis (seg. a sex.) entre publicação e fim das propostas (art. 55) |
| Sem desconto | valor homologado a menos de 1% do estimado |

## Dados pessoais (LGPD)

Fornecedores pessoa física e microempreendedores individuais (MEI) são gravados **com o nome e sem nenhum número
de documento** (nem CPF, nem o CNPJ do MEI; o CPF que aparece no nome de MEIs antigos é retirado), e números com
formato de CPF em textos livres são mascarados – já na coleta, então os CSVs publicados no GitHub também não têm
esses números. No portal, os nomes aparecem só nas tabelas; nos rankings ("Maiores fornecedores") e nos pontos de
atenção, pessoas físicas e MEI ficam somados num grupo só. A publicação completa continua no PNCP.

Até a versão 1.2.2 esses fornecedores eram gravados sem nome. Na primeira coleta da 1.2.3 o robô busca de novo,
uma vez, os contratos já gravados, para trocar o "dado protegido" pelo nome (`renovar_contratos` no
`metadados.json` mostra o que ainda falta).

## Atualização e tempo de coleta

O robô roda `python coletar.py` toda segunda-feira. A coleta é incremental e limitada a 70 minutos
(`--tempo-max`); o que não couber continua na execução seguinte. Na **primeira execução da versão 1.2** o robô
busca o histórico de compras (~400 consultas ao PNCP, que responde devagar) e os relatórios dos 399 municípios
(~2.000 consultas ao SICONFI): rode o robô **duas ou três vezes** para completar. Depois disso, cada execução leva
poucos minutos.

No PNCP, a coleta vai do trimestre mais recente para o mais antigo e, em cada trimestre, busca as contratações e
logo depois os contratos, começando pela Prefeitura. Se o tempo acabar, o que fica faltando é sempre o período mais
antigo. Enquanto faltarem contratos de algum órgão, a página de Compras avisa e suspende os pontos de atenção que
dependem de fornecedores (várias dispensas com a mesma empresa e concentração), para não mostrar um retrato
incompleto.

## Rodar no seu computador (opcional)

Requer Python 3.10 ou superior.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python coletar.py                   # 1ª vez: município + compras + comparativo (até 70 min; rode de novo se faltar)
streamlit run app.py                # abre em http://localhost:8501
python -m pytest                    # 79 testes
```

Opções do coletor: `--modulos municipio pncp comparativo` (o que coletar), `--anos 2024 2026`, `--completo`
(recoleta tudo), `--tempo-max 70`, `--csv` (grava também o `fDespesa.csv` completo) e `--help`.

## Arquivos em `data/`

| Arquivo | Conteúdo |
|---|---|
| `fIndicadores.csv` | Indicadores do RREO e do RGF: `relatorio`, `ano`, `periodo`, `poder` (E/L no RGF), `chave`, `valor` |
| `fReceitaCorrente.csv` | RREO Anexo 3: `ano`, `periodo`, `chave` (iptu, iss, fpm...), `referencia` (AAAA-MM, 12m ou previsao), `valor` |
| `fDespesa.parquet` | Despesa da MSC por ano, mês, poder/órgão, função, subfunção, natureza e fonte (acumulado no ano) |
| `dNatureza.csv`, `dFuncao.csv`, `dPoderOrgao.csv` | Descrições dos códigos |
| `rreo_totais.csv`, `conciliacao_rreo.csv` | Conferência da MSC com o total do RREO a cada bimestre |
| `fContratacoes.csv`, `fContratos.csv` | Compras e contratos dos órgãos municipais no PNCP (sem dados pessoais) |
| `dMunicipios.csv`, `fComparativo.csv` | Municípios do PR e seus indicadores no último ano fechado (`ano`, `cod_ibge`, `fonte`, `chave`, `valor`) |
| `comparativo_controle.csv` | O que já foi coletado no comparativo (permite retomar de onde parou) |
| `metadados.json` | Data da coleta, períodos, situação de cada módulo, relatórios ainda não publicados, falhas |

Os CSVs usam `;` e vírgula decimal. Quando nada muda na fonte, os arquivos ficam idênticos byte a byte e o Git não
registra mudança; só `metadados.json` muda toda semana.

## Como validar

1. **Testes** – `python -m pytest`. A extração é testada com linhas copiadas da API real (`tests/fixtures_api.py`);
   a coleta, com APIs simuladas no mesmo formato (`tests/servidor_simulado.py`).
2. **Valores de referência** (API consultada em 30/10 e 12/11/2026):
   - Guarapuava, até agosto/2026: receita arrecadada R$ 726.358.549,65 de R$ 1.171.101.596,73 previstos; despesa
     liquidada R$ 676.044.444,25; RCL R$ 929.125.228,65; pessoal 51,07% da RCL; Câmara 2,91%; dívida líquida −2,21%.
   - RREO Anexo 3 (set/2025 a ago/2026): IPTU R$ 42.851.715,19 – a soma dos 12 meses bate com o total; ISS
     R$ 113.624.267,76; FPM R$ 186.995.767,52; transferências correntes R$ 688.588.865,57.
   - Abatiá (município pequeno, relatórios simplificados, RGF semestral), 2025: educação 32,39%, saúde 27,62%,
     pessoal 48,06% da RCL; DCA: educação R$ 13.414.241,05 liquidados.
3. **MSC × RREO** – página "Sobre os dados". Em agosto/2026, empenhado, liquidado e pago bateram ao centavo.
4. **Portal da transparência × portal** – `python conciliar_atende.py Demonstrativo.csv --ano 2026 --mes 8`
   (testado com arquivo simulado).

## Limitações

- Defasagem de cerca de um mês em relação ao portal da transparência.
- A MSC separa só Executivo (10131), RPPS (10132) e Legislativo (20231); rótulos inferidos dos dados.
- PNCP: só o que os órgãos publicam lá (compras desde 2024). Prazos contados sem descontar feriados. A ligação
  contrato → dispensa depende do campo do PNCP que indica a contratação de origem.
- Comparativo: cada prefeitura classifica seus gastos por função à sua maneira; por habitante usa a população
  informada no RREO.
- A estrutura das respostas do PNCP segue o manual oficial (versão 1.0) e foi conferida em consultas de teste à
  API; como a coleta completa só roda no robô, confira o resumo do primeiro "Run workflow".
- Em agosto/2026 educação e saúde aparecem com o mesmo percentual (25,71%) no RREO – é o dado publicado.

## Outro município

```bash
PORTAL_ID_ENTE=4106902 PORTAL_NOME_ENTE="Curitiba - PR" PORTAL_CNPJ=<CNPJ do município> python coletar.py --pasta data_curitiba
```

No portal publicado, troque `ID_ENTE`, `NOME_ENTE` e `CNPJ_MUNICIPIO` em `despesas/config.py`. Os rótulos de
poder/órgão em `despesas/dicionarios.py` são de Guarapuava.

## Estrutura

```
app.py                       navegação entre as páginas
paginas/                     indicadores (Visão geral), receitas, despesa, compras, comparar, sobre
coletar.py                   coleta: município, PNCP e comparativo, com limite de tempo
conciliar_atende.py          conferência com o CSV do portal da transparência
despesas/                    api, indicadores, transformacao, pncp, comparativo, alertas, painel, dicionarios, config
despesas/recursos/           malha municipal do PR (IBGE, via geodata-br, domínio público), simplificada;
                             cabecalho.svg e cabecalho.css (ilustração do topo, dia/noite)
tests/                       testes, linhas reais da API e APIs simuladas
.github/workflows/           robô de atualização
.streamlit/config.toml       cores dos temas claro e escuro (tiradas do cabeçalho)
```
