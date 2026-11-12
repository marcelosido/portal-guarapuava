"""Linhas copiadas da API do SICONFI para Guarapuava (consultas de 30/10/2026).

Servem de gabarito para os testes da extração e para a API simulada: os códigos,
os nomes de conta e de coluna são exatamente os que a API devolve.
"""

# RREO Anexo 14 (demonstrativo simplificado), 4º bimestre de 2026 – todas as 66 linhas.
RREO14_2026_4 = [
    ("PrevisaoInicialDemonstrativoSimplificadoBalancoOrcamentario", "Previsão Inicial", "Até o Bimestre", 925500000),
    ("PrevisaoAtualizadaDemonstrativoSimplificadoBalancoOrcamentario", "Previsão Atualizada", "Até o Bimestre", 1171101596.73),
    ("ReceitasRealizadasDemonstrativoSimplificadoBalancoOrcamentario", "Receitas Realizadas", "Até o Bimestre", 726358549.65),
    ("SaldoDeExerciciosAnterioresUtilizadosParaCreditosAdicionaisDemonstrativoSimplificadoBalancoOrcamentario", "Saldos de Exercícios Anteriores (Utilizados para Créditos Adicionais)", "Até o Bimestre", 131317633.11),
    ("DotacaoInicialDemonstrativoSimplificadoBalancoOrcamentario", "Dotação Inicial", "Até o Bimestre", 925498530.46),
    ("DotacaoAtualizadaDemonstrativoSimplificadoBalancoOrcamentario", "Dotação Atualizada", "Até o Bimestre", 1302417760.3),
    ("DespesasEmpenhadasDemonstrativoSimplificadoBalancoOrcamentario", "Despesas Empenhadas", "Até o Bimestre", 739943915.03),
    ("DespesasLiquidadasDemonstrativoSimplificadoBalancoOrcamentario", "Despesas Liquidadas", "Até o Bimestre", 676044444.25),
    ("DespesasPagasDemonstrativoSimplificadoBalancoOrcamentario", "Despesas Pagas", "Até o Bimestre", 639837248.19),
    ("SuperavitOrcamentarioDemonstrativoSimplificadoBalancoOrcamentario", "Superávit Orçamentário", "Até o Bimestre", 50314105.4),
    ("DespesasEmpenhadasDemonstrativoSimplificadoDespesasPorFuncaoSubfuncao", "Despesas Empenhadas", "Até o Bimestre", 739943915.03),
    ("DespesasLiquidadasDemonstrativoSimplificadoDespesasPorFuncaoSubfuncao", "Despesas Liquidadas", "Até o Bimestre", 676044444.25),
    ("ReceitaCorrenteLiquidaDemonstrativoSimplificado", "Receita Corrente Líquida", "Até o Bimestre", 929125228.65),
    ("ReceitaCorrenteLiquidaAjustadaParaCalculoDosLimitesDeEndividamentoDemonstrativoSimplificado", "Receita Corrente Líquida Ajustada para Cálculo dos Limites de Endividamento", "Até o Bimestre", 918027236.65),
    ("ReceitaCorrenteLiquidaAjustadaParaCalculoDosLimitesDaDespesaComPessoalDemonstrativoSimplificado", "Receita Corrente Líquida Ajustada para Cálculo dos Limites da Despesa com Pessoal", "Até o Bimestre", 904679684.65),
    ("ReceitasPrevidenciariasRealizadasRPPSPrevidenciarioDemonstrativoSimplificado", "Receitas Previdenciárias Realizadas", "Até o Bimestre", 74669500.17),
    ("DespesasPrevidenciariasEmpenhadasRPPSPrevidenciarioDemonstrativoSimplificado", "Despesas Previdenciárias Empenhadas", "Até o Bimestre", 59420589.55),
    ("DespesasPrevidenciariasLiquidadasRPPSPrevidenciarioDemonstrativoSimplificado", "Despesas Previdenciárias Liquidadas", "Até o Bimestre", 59390858.18),
    ("DespesasPrevidenciariasPagasRPPSPrevidenciarioDemonstrativoSimplificado", "Despesas Previdenciárias Pagas", "Até o Bimestre", 59390858.18),
    ("ResultadoPrevidenciarioRPPSPrevidenciarioDemonstrativoSimplificado", "Resultado Previdenciário", "Até o Bimestre", 15278641.99),
    ("ResultadoPrimarioAcimaDaLinhaSemRPPSDemonstrativoSimplificado", "RESULTADO PRIMÁRIO (SEM RPPS) - Acima da Linha", "Meta Fixada no Anexo de Metas Fiscais da LDO (a)", 19273424.92),
    ("ResultadoPrimarioAcimaDaLinhaSemRPPSDemonstrativoSimplificado", "RESULTADO PRIMÁRIO (SEM RPPS) - Acima da Linha", "Resultado Apurado até o Bimestre (b)", 11137948.37),
    ("ResultadoNominalAbaixoDaLinhaSemRPPSDemonstrativoSimplificado", "RESULTADO NOMINAL (SEM RPPS) - Abaixo da Linha", "Meta Fixada no Anexo de Metas Fiscais da LDO (a)", -68071790.03),
    ("ResultadoNominalAbaixoDaLinhaSemRPPSDemonstrativoSimplificado", "RESULTADO NOMINAL (SEM RPPS) - Abaixo da Linha", "Resultado Apurado até o Bimestre (b)", 41775665.93),
    ("RestosAPagarProcessadosDemonstrativoSimplificado", "RESTOS A PAGAR PROCESSADOS", "Inscrição", 26835985.63),
    ("RestosAPagarProcessadosDemonstrativoSimplificado", "RESTOS A PAGAR PROCESSADOS", "Cancelamento Até o Bimestre", 383300.07),
    ("RestosAPagarProcessadosDemonstrativoSimplificado", "RESTOS A PAGAR PROCESSADOS", "Pagamento Até o Bimestre", 26134512.74),
    ("RestosAPagarProcessadosDemonstrativoSimplificado", "RESTOS A PAGAR PROCESSADOS", "Saldo a Pagar", 318172.82),
    ("RestosAPagarProcessadosPoderExecutivoDemonstrativoSimplificado", "Poder Executivo", "Inscrição", 26822406.38),
    ("RestosAPagarProcessadosPoderExecutivoDemonstrativoSimplificado", "Poder Executivo", "Cancelamento Até o Bimestre", 383300.07),
    ("RestosAPagarProcessadosPoderExecutivoDemonstrativoSimplificado", "Poder Executivo", "Pagamento Até o Bimestre", 26134512.74),
    ("RestosAPagarProcessadosPoderExecutivoDemonstrativoSimplificado", "Poder Executivo", "Saldo a Pagar", 304593.57),
    ("RestosAPagarProcessadosPoderLegislativoDemonstrativoSimplificado", "Poder Legislativo", "Inscrição", 13579.25),
    ("RestosAPagarProcessadosPoderLegislativoDemonstrativoSimplificado", "Poder Legislativo", "Saldo a Pagar", 13579.25),
    ("RestosAPagarNaoProcessadosDemonstrativoSimplificado", "RESTOS A PAGAR NÃO PROCESSADOS", "Inscrição", 43267826.86),
    ("RestosAPagarNaoProcessadosDemonstrativoSimplificado", "RESTOS A PAGAR NÃO PROCESSADOS", "Cancelamento Até o Bimestre", 4439853.13),
    ("RestosAPagarNaoProcessadosDemonstrativoSimplificado", "RESTOS A PAGAR NÃO PROCESSADOS", "Pagamento Até o Bimestre", 23721879.68),
    ("RestosAPagarNaoProcessadosDemonstrativoSimplificado", "RESTOS A PAGAR NÃO PROCESSADOS", "Saldo a Pagar", 15106094.05),
    ("RestosAPagarNaoProcessadosPoderExecutivoDemonstrativoSimplificado", "Poder Executivo", "Inscrição", 43215017.88),
    ("RestosAPagarNaoProcessadosPoderExecutivoDemonstrativoSimplificado", "Poder Executivo", "Cancelamento Até o Bimestre", 4439853.13),
    ("RestosAPagarNaoProcessadosPoderExecutivoDemonstrativoSimplificado", "Poder Executivo", "Pagamento Até o Bimestre", 23669070.7),
    ("RestosAPagarNaoProcessadosPoderExecutivoDemonstrativoSimplificado", "Poder Executivo", "Saldo a Pagar", 15106094.05),
    ("RestosAPagarNaoProcessadosPoderLegislativoDemonstrativoSimplificado", "Poder Legislativo", "Inscrição", 52808.98),
    ("RestosAPagarNaoProcessadosPoderLegislativoDemonstrativoSimplificado", "Poder Legislativo", "Pagamento Até o Bimestre", 52808.98),
    ("TotalRestosAPagarDemonstrativoSimplificado", "TOTAL", "Inscrição", 70103812.49),
    ("TotalRestosAPagarDemonstrativoSimplificado", "TOTAL", "Cancelamento Até o Bimestre", 4823153.2),
    ("TotalRestosAPagarDemonstrativoSimplificado", "TOTAL", "Pagamento Até o Bimestre", 49856392.42),
    ("TotalRestosAPagarDemonstrativoSimplificado", "TOTAL", "Saldo a Pagar", 15424266.87),
    ("MinimoAnualDasReceitasDeImpostosNaManutencaoEDesenvolvimentoDoEnsinoDemonstrativoSimplificado", "Mínimo Anual de <18% / 25%> das Receitas de Impostos na Manutenção e Desenvolvimento do Ensino", "Valor Apurado Até o Bimestre", 115181455.65),
    ("MinimoAnualDasReceitasDeImpostosNaManutencaoEDesenvolvimentoDoEnsinoDemonstrativoSimplificado", "Mínimo Anual de <18% / 25%> das Receitas de Impostos na Manutenção e Desenvolvimento do Ensino", "% Mínimo a Aplicar no Exercício", 25),
    ("MinimoAnualDasReceitasDeImpostosNaManutencaoEDesenvolvimentoDoEnsinoDemonstrativoSimplificado", "Mínimo Anual de <18% / 25%> das Receitas de Impostos na Manutenção e Desenvolvimento do Ensino", "% Aplicado Até o Bimestre", 25.71),
    ("MinimoAnualDoFUNDEBNaRemuneracaoDoMagisterioComEducacaoInfantilEnsinoFundamentalEMedioDemonstrativoSimplificado", "Mínimo Anual de 70% do FUNDEB na Remuneração dos Profissionais da Educação Básica", "Valor Apurado Até o Bimestre", 96554613.57),
    ("MinimoAnualDoFUNDEBNaRemuneracaoDoMagisterioComEducacaoInfantilEnsinoFundamentalEMedioDemonstrativoSimplificado", "Mínimo Anual de 70% do FUNDEB na Remuneração dos Profissionais da Educação Básica", "% Mínimo a Aplicar no Exercício", 70),
    ("MinimoAnualDoFUNDEBNaRemuneracaoDoMagisterioComEducacaoInfantilEnsinoFundamentalEMedioDemonstrativoSimplificado", "Mínimo Anual de 70% do FUNDEB na Remuneração dos Profissionais da Educação Básica", "% Aplicado Até o Bimestre", 91.75),
    ("ReceitaDeOperacoesDeCreditoDemonstrativoSimplificado", "Receitas de Operações de Crédito", "Valor Apurado no Exercício", 47429775.48),
    ("ReceitaDeOperacoesDeCreditoDemonstrativoSimplificado", "Receitas de Operações de Crédito", "Saldo Não Realizado", 150019909.51),
    ("DespesaDeCapitalLiquidaDemonstrativoSimplificado", "Despesa de Capital Líquida", "Valor Apurado no Exercício", 48277865.99),
    ("DespesaDeCapitalLiquidaDemonstrativoSimplificado", "Despesa de Capital Líquida", "Saldo Não Realizado", 250294231.55),
    ("ReceitaDeCapitalResultanteDaAlienacaoDeAtivosDemonstrativoSimplificado", "Receitas da Alienação de Ativos", "Valor Apurado no Exercício", 295105.73),
    ("ReceitaDeCapitalResultanteDaAlienacaoDeAtivosDemonstrativoSimplificado", "Receitas da Alienação de Ativos", "Saldo a Realizar", -284105.73),
    ("AplicacaoDosRecursosDaAlienacaoDeAtivosDemonstrativoSimplificado", "Aplicação dos Recursos da Alienação de Ativos", "Valor Apurado no Exercício", 891960.54),
    ("AplicacaoDosRecursosDaAlienacaoDeAtivosDemonstrativoSimplificado", "Aplicação dos Recursos da Alienação de Ativos", "Saldo a Realizar", 454272.38),
    ("AplicacaoTotalDasDespesasComAcoesEServicosPublicosDeSaude", "Despesas com Ações e Serviços Públicos de Saúde Executadas com Recursos de Impostos", "Valor Apurado Até o Bimestre", 113107935.17),
    ("AplicacaoTotalDasDespesasComAcoesEServicosPublicosDeSaude", "Despesas com Ações e Serviços Públicos de Saúde Executadas com Recursos de Impostos", "% Mínimo a Aplicar no Exercício", 15),
    ("AplicacaoTotalDasDespesasComAcoesEServicosPublicosDeSaude", "Despesas com Ações e Serviços Públicos de Saúde Executadas com Recursos de Impostos", "% Aplicado Até o Bimestre", 25.71),
    ("TotalDasDespesasDeCaraterContinuadoEmRelacaoAReceitaCorrenteLiquidaDemonstrativoSimplificado", "Total das Despesas Consideradas para o Limite / RCL (%)", "Valor Apurado no Exercício Corrente", 0.73),
]

# RREO Anexo 14, 6º bimestre de 2021: formato antigo do resultado primário/nominal (sem meta).
RREO14_2021_6_DIFERENCAS = [
    ("ReceitasRealizadasDemonstrativoSimplificadoBalancoOrcamentario", "Receitas Realizadas", "Até o Bimestre", 611205738.12),
    ("DespesasLiquidadasDemonstrativoSimplificadoBalancoOrcamentario", "Despesas Liquidadas", "Até o Bimestre", 511609392.57),
    ("SuperavitOrcamentarioDemonstrativoSimplificadoBalancoOrcamentario", "Superávit Orçamentário", "Até o Bimestre", 99596345.55),
    ("ResultadoPrimarioDemonstrativoSimplificado", "RESULTADO PRIMÁRIO", "Resultado Apurado até o Bimestre (b)", 61047980.92),
    ("ResultadoNominalDemonstrativoSimplificado", "RESULTADO NOMINAL", "Resultado Apurado até o Bimestre (b)", 60255063.55),
    ("MinimoAnualDasReceitasDeImpostosNaManutencaoEDesenvolvimentoDoEnsinoDemonstrativoSimplificado", "Mínimo Anual de <18% / 25%> das Receitas de Impostos na Manutenção e Desenvolvimento do Ensino", "% Aplicado Até o Bimestre", 25.89),
    ("AplicacaoTotalDasDespesasComAcoesEServicosPublicosDeSaude", "Despesas com Ações e Serviços Públicos de Saúde Executadas com Recursos de Impostos", "% Aplicado Até o Bimestre", 28.21),
]

# RREO Anexo 1, 4º bimestre de 2026: receitas (previsão atualizada e realizado até o bimestre).
RREO01_2026_4_RECEITAS = [
    ("ReceitasExcetoIntraOrcamentarias", "RECEITAS (EXCETO INTRA-ORÇAMENTÁRIAS) (I)", 1161336596.73, 679787384.21),
    ("ReceitasCorrentes", "RECEITAS CORRENTES", 937562101.7, 667413644.28),
    ("ReceitaTributaria", "IMPOSTOS, TAXAS E CONTRIBUIÇÕES DE MELHORIA", 245456600, 182033924.85),
    ("Impostos", "Impostos", 218766490, 162221502.63),
    ("TransferenciasCorrentes", "TRANSFERÊNCIAS CORRENTES", 618795312, 406037271.99),
    ("ReceitasDeCapital", "RECEITAS DE CAPITAL", 223774495.03, 12373739.93),
]

# RGF Anexo 1 (despesa com pessoal), 2º quadrimestre de 2026.
RGF01_2026_2_EXECUTIVO = [
    ("DespesaComPessoalTotal", "DESPESA TOTAL COM PESSOAL - DTP (VI) = (IIIa + IIIb)", "Valor", 461997742.46),
    ("DespesaComPessoalTotal", "DESPESA TOTAL COM PESSOAL - DTP (VI) = (IIIa + IIIb)", "% sobre a RCL Ajustada", 51.07),
    ("ReceitaCorrenteLiquidaLimiteLegal", "RECEITA CORRENTE LIQUIDA - RCL (IV)", "Valor", 929125228.65),
    ("ReceitaCorrenteLiquidaAjustada", "= RECEITA CORRENTE LÍQUIDA AJUSTADA PARA CÁLCULO DOS LIMITES DA DESPESA COM PESSOAL (V)", "Valor", 904679684.65),
    ("LimiteMaximoDespesaComPessoalTotal", "LIMITE MÁXIMO (VII) (incisos I, II e III, art. 20 da LRF)", "Valor", 488527029.71),
    ("LimiteMaximoDespesaComPessoalTotal", "LIMITE MÁXIMO (VII) (incisos I, II e III, art. 20 da LRF)", "% sobre a RCL Ajustada", 54),
    ("LimitePrudencialDespesaComPessoalTotal", "LIMITE PRUDENCIAL (VIII) = (0,95 x VII) (parágrafo único do art. 22 da LRF)", "Valor", 464100678.22),
    ("LimitePrudencialDespesaComPessoalTotal", "LIMITE PRUDENCIAL (VIII) = (0,95 x VII) (parágrafo único do art. 22 da LRF)", "% sobre a RCL Ajustada", 51.3),
    ("LimiteDeAlertaDespesaComPessoalTotal", "LIMITE DE ALERTA (IX) = (0,90 x VII) (inciso II do §1º do art. 59 da LRF)", "Valor", 439674326.74),
    ("LimiteDeAlertaDespesaComPessoalTotal", "LIMITE DE ALERTA (IX) = (0,90 x VII) (inciso II do §1º do art. 59 da LRF)", "% sobre a RCL Ajustada", 48.6),
]
RGF01_2026_2_LEGISLATIVO = [
    ("DespesaComPessoalTotal", "DESPESA TOTAL COM PESSOAL - DTP (VI) = (III a + III b)", "Valor", 26283419.3),
    ("DespesaComPessoalTotal", "DESPESA TOTAL COM PESSOAL - DTP (VI) = (III a + III b)", "% sobre a RCL Ajustada", 2.91),
    ("LimiteMaximoDespesaComPessoalTotal", "LIMITE MÁXIMO (VII) (incisos I, II e III, art. 20 da LRF)", "% sobre a RCL Ajustada", 6),
    ("LimitePrudencialDespesaComPessoalTotal", "LIMITE PRUDENCIAL (VIII) = (0,95 x VII) (parágrafo único do art. 22 da LRF)", "% sobre a RCL Ajustada", 5.7),
    ("LimiteDeAlertaDespesaComPessoalTotal", "LIMITE DE ALERTA (IX) = (0,90 x VII) (inciso II do §1º do art. 59 da LRF)", "% sobre a RCL Ajustada", 5.4),
]

# RGF Anexo 2 (dívida consolidada), 2026: três colunas (exercício anterior, 1º e 2º quadrimestres).
RGF02_2026 = [
    ("DividaConsolidada", "DÍVIDA CONSOLIDADA - DC (I)", "SALDO DO EXERCÍCIO ANTERIOR", 88910139.13),
    ("DividaConsolidada", "DÍVIDA CONSOLIDADA - DC (I)", "Até o 1º Quadrimestre", 83895916.42),
    ("DividaConsolidada", "DÍVIDA CONSOLIDADA - DC (I)", "Até o 2º Quadrimestre", 79304484.47),
    ("DividaConsolidadaLiquida", "DÍVIDA CONSOLIDADA LÍQUIDA (DCL) (III) = (I - II)", "SALDO DO EXERCÍCIO ANTERIOR", 21528304.14),
    ("DividaConsolidadaLiquida", "DÍVIDA CONSOLIDADA LÍQUIDA (DCL) (III) = (I - II)", "Até o 1º Quadrimestre", -6360505.78),
    ("DividaConsolidadaLiquida", "DÍVIDA CONSOLIDADA LÍQUIDA (DCL) (III) = (I - II)", "Até o 2º Quadrimestre", -20247361.79),
    ("PercentualDaDCSobreARCL", "% da DC sobre a RCL AJUSTADA (I/VI)", "SALDO DO EXERCÍCIO ANTERIOR", 10.13),
    ("PercentualDaDCSobreARCL", "% da DC sobre a RCL AJUSTADA (I/VI)", "Até o 1º Quadrimestre", 9.46),
    ("PercentualDaDCSobreARCL", "% da DC sobre a RCL AJUSTADA (I/VI)", "Até o 2º Quadrimestre", 8.64),
    ("PercentualDaDCLSobreARCL", "% da DCL sobre a RCL AJUSTADA (III/VI)", "SALDO DO EXERCÍCIO ANTERIOR", 2.45),
    ("PercentualDaDCLSobreARCL", "% da DCL sobre a RCL AJUSTADA (III/VI)", "Até o 1º Quadrimestre", -0.72),
    ("PercentualDaDCLSobreARCL", "% da DCL sobre a RCL AJUSTADA (III/VI)", "Até o 2º Quadrimestre", -2.21),
    ("LimiteDefinidoPorResolucaoDoSenadoFederal", "LIMITE DEFINIDO POR RESOLUÇÃO DO SENADO FEDERAL", "SALDO DO EXERCÍCIO ANTERIOR", 1052888555.7),
    ("LimiteDefinidoPorResolucaoDoSenadoFederal", "LIMITE DEFINIDO POR RESOLUÇÃO DO SENADO FEDERAL", "Até o 1º Quadrimestre", 1063929824.08),
    ("LimiteDefinidoPorResolucaoDoSenadoFederal", "LIMITE DEFINIDO POR RESOLUÇÃO DO SENADO FEDERAL", "Até o 2º Quadrimestre", 1101632683.98),
]


def itens(linhas, rotulo="Padrão"):
    """Converte as tuplas (cod_conta, conta, coluna, valor) no formato de item da API."""
    return [{"rotulo": rotulo, "cod_conta": c, "conta": n, "coluna": col, "valor": v} for c, n, col, v in linhas]


def itens_rreo01(linhas):
    saida = []
    for codigo, conta, prevista, realizada in linhas:
        saida.append({"rotulo": "Padrão", "cod_conta": codigo, "conta": conta, "coluna": "PREVISÃO ATUALIZADA (a)", "valor": prevista})
        saida.append({"rotulo": "Padrão", "cod_conta": codigo, "conta": conta, "coluna": "Até o Bimestre (c)", "valor": realizada})
    return saida
