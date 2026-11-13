# Guarapuava em números

**Portal:** [guarapuava-em-numeros.streamlit.app](https://guarapuava-em-numeros.streamlit.app) ·
**Apostila (PDF):** [como o portal foi feito, passo a passo](Apostila%20-%20Guarapuava%20em%20n%C3%BAmeros.pdf) ·
**Licença:** [MIT](LICENSE)

Portal público com as contas da Prefeitura de Guarapuava (PR): orçamento previsto × realizado, limites da Lei de
Responsabilidade Fiscal, mínimos de educação e saúde, receitas por imposto, despesa detalhada, compras e contratos
publicados no PNCP, comparação com os outros 398 municípios do Paraná e **pontos de atenção** calculados com regras
fixas. Tudo com dados abertos oficiais, atualizados toda semana por um robô do GitHub Actions. O site roda no
Streamlit Community Cloud, sem custo.

> **Quer entender como tudo foi feito, mesmo sem saber programar?** A
> [apostila em PDF](Apostila%20-%20Guarapuava%20em%20n%C3%BAmeros.pdf) explica cada parte em linguagem simples: de onde
> vêm os dados, o que o código faz, quais bibliotecas foram usadas e por quê, além de como publicar, manter e praticar.

## Use na sua cidade

O portal serve para qualquer município do Brasil, porque as fontes são nacionais: todas as prefeituras enviam seus
relatórios ao Tesouro Nacional (SICONFI) e publicam suas compras no PNCP.

1. **Faça um fork** deste repositório: botão **Fork**, no alto da página
   ([ou por este link](https://github.com/marcelosido/portal-guarapuava/fork)).
2. **Troque quatro campos** em `despesas/config.py`. Em cada linha, mude só o valor entre aspas depois da vírgula. Por
   exemplo, em `ID_ENTE = os.getenv("PORTAL_ID_ENTE", "4109401")`, troque `4109401` pelo código da sua cidade.

   | Campo | O que é | Em Guarapuava |
   |---|---|---|
   | `ID_ENTE` | Código IBGE do município (7 dígitos) | `4109401` |
   | `NOME_ENTE` | Nome no formato "Cidade - UF"; vira o título "Cidade em números" | `Guarapuava - PR` |
   | `CNPJ_MUNICIPIO` | CNPJ do município, só números; usado nas compras do PNCP | `76178037000176` |
   | `UF` | Estado usado na comparação entre cidades | `PR` |

   Opcionais, no mesmo arquivo: `ANO_INICIAL` (primeiro ano buscado na API; padrão 2019) e
   `URL_PORTAL_TRANSPARENCIA` (link para o portal da transparência da sua cidade).
3. **Cidade de outro estado?** Troque também o mapa `despesas/recursos/malha_pr.geojson` pela malha municipal do seu
   estado, com o mesmo nome de arquivo. Ela precisa estar em GeoJSON, com as propriedades `id` (código IBGE) e `name`
   (nome). A deste projeto veio do geodata-br (IBGE, domínio público), que tem um arquivo por estado; simplifique o
   arquivo se ele for muito grande (por exemplo, no mapshaper.org).
4. **Revise os textos fixos** (recomendado):
   - `paginas/sobre.py`: três observações sobre os dados de Guarapuava (procure por "Guarapuava");
   - `despesas/dicionarios.py`: nomes dos órgãos em `PODER_ORGAO` (o RPPS daqui se chama "Guarapuava Prev");
   - outro estado: algumas frases de `paginas/comparar.py`, `paginas/indicadores.py` e `paginas/sobre.py` citam
     "Paraná" ou "PR" (procure por esses termos).
5. **Ligue o robô.**
   - Na aba **Actions** do fork, clique no botão que ativa os workflows (o GitHub deixa os workflows desligados em
     forks).
   - Em **Atualizar dados → Run workflow**, marque **"Recoletar tudo"** e rode. Assim o robô descarta os dados de
     Guarapuava e busca os da sua cidade; sem essa opção, ele para com o aviso de que a pasta `data/` é de outro
     município.
   - A primeira coleta completa pode precisar de duas ou três execuções. **Só a primeira leva "Recoletar tudo"**: nas
     seguintes, deixe a opção desmarcada, para o robô continuar de onde parou. Depois, ele roda sozinho toda
     segunda-feira.
   - Se o passo "Gravar os dados no repositório" falhar por falta de permissão, vá em **Settings → Actions → General →
     Workflow permissions**, marque **Read and write permissions** e rode de novo.
6. **Publique o site.** Em [share.streamlit.io](https://share.streamlit.io), clique em **Create app**, escolha o seu
   fork, a branch `main` e o arquivo `app.py`, e clique em **Deploy**.

Os campos também podem ser definidos por variáveis de ambiente (`PORTAL_ID_ENTE`, `PORTAL_NOME_ENTE`,
`PORTAL_CNPJ`, `PORTAL_UF`), o que permite testar outra cidade no seu computador sem mexer no código:

```bash
PORTAL_ID_ENTE=4106902 PORTAL_NOME_ENTE="Curitiba - PR" PORTAL_CNPJ=<CNPJ do município> python coletar.py --pasta data_curitiba
```

## Como contribuir

- **Sugestões, dúvidas e erros:** abra uma *issue* na aba **Issues**. Se encontrar um número diferente do relatório
  oficial, inclua o link ou o nome do relatório para conferência.
- **Mudanças no código:** envie um *pull request*. Antes, rode os testes (`python -m pytest`, 92 testes).

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
- **Comparar cidades**: mapa do Paraná (clique para escolher a cidade) e a sua cidade ao lado de outra. A medida
  principal de cada área (educação, saúde, transporte, investimentos, urbanismo, assistência) é o **peso no
  orçamento**: de cada R$ 100 gastos no ano, quanto foi para a área; o gasto por habitante aparece como dado de
  apoio. Também entram os mínimos de educação e saúde, o gasto com pessoal (% da RCL) e a receita por habitante. A
  comparação pode ser com todo o Paraná ou **só com cidades do mesmo porte** (faixas de população). Para cada
  indicador, uma faixa do 1º ao último lugar (em cinco partes, nas cores do mapa) marca a posição das duas cidades,
  e o ranking completo fica numa tabela. Os percentuais de educação e saúde vêm do resumo do RREO (Anexo 14), que só
  parte dos municípios preenche: em 2025, cerca de 220 de 393.
- **Sobre os dados**: fontes, atualização, conferência MSC × RREO, critérios dos pontos de atenção, LGPD e downloads.

Todas as páginas abrem com o cabeçalho **"Planalto com geada"** (campos com araucárias, geada e sol nascendo). No
tema escuro, a mesma cena aparece à noite, com lua e estrelas. As cores do portal saem do cabeçalho: no tema claro,
fundo azul-geada (`#f5f8fc`) e texto azul-marinho (`#15253b`); no escuro, fundo azul-noite (`#0d1626`) e texto
`#e7edf5`. Elas ficam em `.streamlit/config.toml`, e as mesmas cores de fundo e texto ficam em `TOKENS`, em
`despesas/painel.py`, porque os gráficos usam essas cores. Um teste confere se as duas estão iguais.

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
| Contratação direta | parte do valor estimado do ano em dispensas e inexigibilidades (só acompanhamento: a lei não fixa limite) |
| Concentração | 5 maiores fornecedores com 50% ou mais do valor dos contratos do ano |

## Dados pessoais (LGPD)

Fornecedores pessoa física e microempreendedores individuais (MEI) são gravados **com o nome e sem nenhum número
de documento** (nem CPF, nem o CNPJ do MEI; o CPF que aparece no nome de MEIs antigos é retirado), e números com
formato de CPF em textos livres são mascarados – já na coleta, então os CSVs publicados no GitHub também não têm
esses números. No portal, os nomes aparecem só nas tabelas; nos rankings ("Maiores fornecedores") e nos pontos de
atenção, pessoas físicas e MEI ficam somados num grupo só. A publicação completa continua no PNCP.

## Atualização e tempo de coleta

O robô roda `python coletar.py` toda segunda-feira. A coleta é incremental e limitada a 70 minutos
(`--tempo-max`); o que não couber continua na execução seguinte. Na **primeira execução** (num fork novo ou depois
de trocar de cidade) o robô busca o histórico de compras (centenas de consultas ao PNCP, que responde devagar) e os
relatórios de todos os municípios do estado (cerca de 2.000 consultas ao SICONFI no Paraná): rode o robô **duas ou
três vezes** para completar. Depois disso, cada execução leva poucos minutos.

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
python -m pytest                    # 92 testes
```

Opções do coletor: `--modulos municipio pncp comparativo` (o que coletar), `--anos 2024 2026`, `--completo`
(recoleta tudo), `--tempo-max 70`, `--csv` (grava também o `fDespesa.csv` completo) e `--help`.

Sem instalar nada: no GitHub, clique em **Code → Codespaces → Create codespace on main**. O portal abre sozinho numa
aba de visualização, e os testes rodam no terminal com os mesmos comandos acima.

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

Os CSVs usam `;` e vírgula decimal (abrem direto no Excel e no Power BI). Quando nada muda na fonte, os arquivos
ficam idênticos byte a byte e o Git não registra mudança; só `metadados.json` muda toda semana.

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
   (para o formato de exportação do Atende.net, usado por Guarapuava; testado com arquivo simulado).

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

## Estrutura

```
app.py                       navegação entre as páginas
paginas/                     indicadores (Visão geral), receitas, despesa, compras, comparar, sobre
coletar.py                   coleta: município, PNCP e comparativo, com limite de tempo
conciliar_atende.py          conferência com o CSV do portal da transparência (Atende.net)
despesas/                    api, indicadores, transformacao, pncp, comparativo, alertas, painel, dicionarios, config
despesas/recursos/           malha municipal do PR (IBGE, via geodata-br, domínio público), simplificada;
                             cabecalho.svg e cabecalho.css (ilustração do topo, dia/noite)
tests/                       testes, linhas reais da API e APIs simuladas
.github/workflows/           robô de atualização
.streamlit/config.toml       cores dos temas claro e escuro (tiradas do cabeçalho)
Apostila - Guarapuava em números.pdf   apostila em linguagem simples
LICENSE                      licença MIT
```

## Licença e créditos

Código aberto sob a [licença MIT](LICENSE): qualquer pessoa pode usar, copiar, modificar e distribuir, desde que
mantenha o aviso de copyright. Os dados vêm de fontes públicas oficiais: Tesouro Nacional (SICONFI) e Portal Nacional
de Contratações Públicas (PNCP).

Desenvolvido por Marcelo Júnior com o apoio do Claude (Anthropic), como conta a apostila.
