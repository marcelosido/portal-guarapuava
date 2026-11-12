"""Linhas copiadas da API do SICONFI (consultas de 30/10/2026 e 12/11/2026).

Servem de gabarito para os testes da extração e para a API simulada: os códigos,
os nomes de conta e de coluna e os valores são exatamente os que a API devolve, salvo
onde indicado ("montado no formato real").
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


# RREO Anexo 3 (receita corrente líquida), Guarapuava, 4º bimestre de 2026 (set/2025 a ago/2026).
# IPTU: os 12 meses; demais linhas: total dos 12 meses, previsão atualizada e, nas 8 primeiras, o último mês.
_PREV = "PREVISÃO ATUALIZADA 2026"
_TOTAL = "TOTAL (ÚLTIMOS 12 MESES)"
RREO03_2026_4 = [
    ("IPTULiquidoExcetoTransferenciasEFUNDEB", "IPTU", f"<MR-{k}>" if k else "<MR>", v)
    for k, v in zip(range(11, -1, -1), [3214835.15, 2731111.1, 3580562.51, 2350928.12, 615086.79, 806742.88,
                                        1413508.97, 1236576.32, 4723313.95, 16094251.79, 3158129.43, 2926668.18])
] + [
    ("IPTULiquidoExcetoTransferenciasEFUNDEB", "IPTU", _TOTAL, 42851715.19),
    ("IPTULiquidoExcetoTransferenciasEFUNDEB", "IPTU", _PREV, 36204290),
]
for _cod, _conta, _total, _prev, _mr in [
    ("ReceitasCorrentesLiquidasExcetoTransferenciasEFUNDEB", "RECEITAS CORRENTES (I)", 1097100348.01, 1013482101.7, 93058768.55),
    ("ReceitaTributariaLiquidaExcetoTransferenciasEFUNDEB", "Impostos, Taxas e Contribuições de Melhoria", 272638824.9, 245456600, 22128705.3),
    ("ISSLiquidoExcetoTransferenciasEFUNDEB", "ISS", 113624267.76, 88266340, 9642431.72),
    ("ITBILiquidoExcetoTransferenciasEFUNDEB", "ITBI", 22920865.15, 32895860, 2121422.81),
    ("IRRFLiquidoExcetoTransferenciasEFUNDEB", "IRRF", 64863300.81, 61400000, 5166076.36),
    ("OutrasReceitasTributarias", "Outros Impostos, Taxas e Contribuições de Melhoria", 28378675.99, 26690110, 2272106.23),
    ("RREO3ReceitaDeContribuicoes", "Contribuições", 62677880.07, 43341027.3, 5250490.14),
]:
    RREO03_2026_4 += [(_cod, _conta, _TOTAL, _total), (_cod, _conta, _PREV, _prev), (_cod, _conta, "<MR>", _mr)]
for _cod, _conta, _total, _prev in [
    ("RREO3ReceitaPatrimonial", "Receita Patrimonial", 60652967.52, None),
    ("RendimentosDeAplicacaoFinanceira", "Rendimentos de Aplicação Financeira", 60025539.38, None),
    ("OutrasReceitasPatrimoniais", "Outras Receitas Patrimoniais", 627428.14, None),
    ("RREO3ReceitaAgropecuaria", "Receita Agropecuária", None, 50000),
    ("RREO3ReceitaDeServicos", "Receita de Serviços", 330395.1, 3038100),
    ("RREO3TransferenciasCorrentes", "Transferências Correntes", 688588865.57, 694715312),
    ("RREO3CotaParteDoFPM", "Cota-Parte do FPM", 186995767.52, 193210800),
    ("RREO3CotaParteDoICMS", "Cota-Parte do ICMS", 179928792.22, 200100000),
    ("RREO3CotaParteDoIPVA", "Cota-Parte do IPVA", 49243670.05, 38250000),
    ("RREO3CotaParteDoITR", "Cota-Parte do ITR", 8659061.86, 8650000),
    ("RREO3TransferenciasDaLC611989", "Transferências da LC nº 61/1989", 2798069, 2900000),
    ("RREO3TransferenciasDoFUNDEB", "Transferências do FUNDEB", 155991584.46, 151520000),
    ("RREO3OutrasTransferenciasCorrentes", "Outras Transferências Correntes", 104971920.46, 100084512),
    ("RREO3OutrasReceitasCorrentes", "Outras Receitas Correntes", 12211414.85, 13051900),
    ("DeducoesDaReceitaCorrenteLiquida", "DEDUÇÕES (II)", 167975119.36, 101770000),
    ("DeducaoDeReceitaParaFormacaoDoFUNDEB", "Dedução de Receita para Formação do FUNDEB", 81732774.68, 75920000),
    ("RREO3ReceitaCorrenteLiquida", "RECEITA CORRENTE LÍQUIDA (III) = (I - II)", 929125228.65, 911712101.7),
]:
    if _total is not None:
        RREO03_2026_4.append((_cod, _conta, _TOTAL, _total))
    if _prev is not None:
        RREO03_2026_4.append((_cod, _conta, _PREV, _prev))

# Abatiá - PR (4100103, 7.321 habitantes): município pequeno com RREO e RGF simplificados, RGF semestral.
RREO14_SIMPLIFICADO_ABATIA_2025_6 = [
    ("ReceitasRealizadasDemonstrativoSimplificadoBalancoOrcamentario", "Receitas Realizadas", "Até o Bimestre", 49542985.08),
    ("DespesasLiquidadasDemonstrativoSimplificadoBalancoOrcamentario", "Despesas Liquidadas", "Até o Bimestre", 45358837.38),
    ("DespesasLiquidadasDemonstrativoSimplificadoDespesasPorFuncaoSubfuncao", "Despesas Liquidadas", "Até o Bimestre", 45358837.38),
    ("ReceitaCorrenteLiquidaDemonstrativoSimplificado", "Receita Corrente Líquida", "Até o Bimestre", 45929869.11),
    ("ReceitaCorrenteLiquidaAjustadaParaCalculoDosLimitesDeEndividamentoDemonstrativoSimplificado", "Receita Corrente Líquida Ajustada para Cálculo dos Limites de Endividamento", "Até o Bimestre", 44329562.11),
    ("MinimoAnualDasReceitasDeImpostosNaManutencaoEDesenvolvimentoDoEnsinoDemonstrativoSimplificado", "Mínimo Anual de <18% / 25%> das Receitas de Impostos na Manutenção e Desenvolvimento do Ensino", "% Mínimo a Aplicar no Exercício", 25),
    ("MinimoAnualDasReceitasDeImpostosNaManutencaoEDesenvolvimentoDoEnsinoDemonstrativoSimplificado", "Mínimo Anual de <18% / 25%> das Receitas de Impostos na Manutenção e Desenvolvimento do Ensino", "% Aplicado Até o Bimestre", 32.39),
    ("MinimoAnualDoFUNDEBNaRemuneracaoDoMagisterioComEducacaoInfantilEnsinoFundamentalEMedioDemonstrativoSimplificado", "Mínimo Anual de 70% do FUNDEB na Remuneração dos Profissionais da Educação Básica", "% Mínimo a Aplicar no Exercício", 70),
    ("MinimoAnualDoFUNDEBNaRemuneracaoDoMagisterioComEducacaoInfantilEnsinoFundamentalEMedioDemonstrativoSimplificado", "Mínimo Anual de 70% do FUNDEB na Remuneração dos Profissionais da Educação Básica", "% Aplicado Até o Bimestre", 71.09),
    ("AplicacaoTotalDasDespesasComAcoesEServicosPublicosDeSaude", "Despesas com Ações e Serviços Públicos de Saúde Executadas com Recursos de Impostos", "% Mínimo a Aplicar no Exercício", 15),
    ("AplicacaoTotalDasDespesasComAcoesEServicosPublicosDeSaude", "Despesas com Ações e Serviços Públicos de Saúde Executadas com Recursos de Impostos", "% Aplicado Até o Bimestre", 27.62),
]
RGF01_SIMPLIFICADO_ABATIA_2025_S2 = [
    ("DespesaComPessoalTotal", "DESPESA TOTAL COM PESSOAL - DTP", "Valor", 21002020.83),
    ("DespesaComPessoalTotal", "DESPESA TOTAL COM PESSOAL - DTP", "% sobre a RCL Ajustada", 48.06),
    ("ReceitaCorrenteLiquidaAjustada", "RECEITA CORRENTE LÍQUIDA AJUSTADA", "Valor", 43698074.11),
    ("LimiteMaximoDespesaComPessoalTotal", "LIMITE MÁXIMO", "Valor", 23596960.02),
    ("LimiteMaximoDespesaComPessoalTotal", "LIMITE MÁXIMO", "% sobre a RCL Ajustada", 54),
    ("LimitePrudencialDespesaComPessoalTotal", "LIMITE PRUDENCIAL", "Valor", 22417112.02),
    ("LimitePrudencialDespesaComPessoalTotal", "LIMITE PRUDENCIAL", "% sobre a RCL Ajustada", 51.3),
    ("LimiteDeAlertaDespesaComPessoalTotal", "LIMITE DE ALERTA", "Valor", 21237264.02),
    ("LimiteDeAlertaDespesaComPessoalTotal", "LIMITE DE ALERTA", "% sobre a RCL Ajustada", 48.6),
]
# DCA 2025 de Abatiá. Anexo I-E: despesa por função (cod_conta "TotalDespesas" em todas as linhas).
DCA_IE_ABATIA_2025 = [
    ("TotalDespesas", "Despesas Exceto Intraorçamentárias", "Despesas Empenhadas", 53785594.64),
    ("TotalDespesas", "Despesas Exceto Intraorçamentárias", "Despesas Liquidadas", 45358837.38),
    ("TotalDespesas", "Despesas Exceto Intraorçamentárias", "Despesas Pagas", 45131899.78),
    ("TotalDespesas", "10 - Saúde", "Despesas Empenhadas", 12966356.27),
    ("TotalDespesas", "10 - Saúde", "Despesas Liquidadas", 11367792.51),
    ("TotalDespesas", "10 - Saúde", "Despesas Pagas", 11328321.28),
    ("TotalDespesas", "12 - Educação", "Despesas Empenhadas", 13782724.5),
    ("TotalDespesas", "12 - Educação", "Despesas Liquidadas", 13414241.05),
    ("TotalDespesas", "12 - Educação", "Despesas Pagas", 13318422.69),
    ("TotalDespesas", "26 - Transporte", "Despesas Empenhadas", 172929.38),
    ("TotalDespesas", "26 - Transporte", "Despesas Liquidadas", 130882.76),
    ("TotalDespesas", "26 - Transporte", "Despesas Pagas", 130882.76),
]
# Anexo I-D: despesa por natureza.
DCA_ID_ABATIA_2025 = [
    ("DO3.0.00.00.00.00", "3.0.00.00.00 - Despesas Correntes", "Despesas Liquidadas", 39777605.78),
    ("DO3.1.00.00.00.00", "3.1.00.00.00 - Pessoal e Encargos Sociais", "Despesas Empenhadas", 23412748.91),
    ("DO3.1.00.00.00.00", "3.1.00.00.00 - Pessoal e Encargos Sociais", "Despesas Liquidadas", 23404431.17),
    ("DO4.0.00.00.00.00", "4.0.00.00.00 - Despesas de Capital", "Despesas Liquidadas", 5581231.6),
    ("DO4.4.00.00.00.00", "4.4.00.00.00 - Investimentos", "Despesas Empenhadas", 10633741.69),
    ("DO4.4.00.00.00.00", "4.4.00.00.00 - Investimentos", "Despesas Liquidadas", 4753866.67),
    ("DO4.4.00.00.00.00", "4.4.00.00.00 - Investimentos", "Despesas Pagas", 4742112.55),
    ("TotalDespesas", "Total Geral da Despesa", "Despesas Liquidadas", 45358837.38),
]

# Extrato de entregas 2025: (instituição, entregável, período, periodicidade, situação).
_PREF_ABATIA, _CAM_ABATIA = "Prefeitura Municipal de Abatiá - PR", "Câmara de Vereadores de Abatiá - PR"
EXTRATO_ABATIA_2025 = [
    (_CAM_ABATIA, "Relatório de Gestão Fiscal Simplificado", 1, "S", "HO"),
    (_CAM_ABATIA, "Relatório de Gestão Fiscal Simplificado", 2, "S", "HO"),
    (_PREF_ABATIA, "Relatório de Gestão Fiscal Simplificado", 1, "S", "HO"),
    (_PREF_ABATIA, "Relatório de Gestão Fiscal Simplificado", 2, "S", "HO"),
] + [(_PREF_ABATIA, "Relatório Resumido de Execução Orçamentária Simplificado", b, "B", "HO") for b in range(1, 7)]
_PREF_GUARA, _CAM_GUARA = "Prefeitura Municipal de Guarapuava - PR", "Câmara de Vereadores de Guarapuava - PR"
EXTRATO_GUARAPUAVA_2025 = (
    [(i, "MSC Agregada", m, "M", None) for i in (_CAM_GUARA, _PREF_GUARA) for m in range(1, 13)]
    + [(_CAM_GUARA, "Relatório de Gestão Fiscal", q, "Q", "HO") for q in range(1, 4)]
    + [(_PREF_GUARA, "Balanço Anual (DCA)", 1, "A", "HO")]
    + [(_PREF_GUARA, "Relatório de Gestão Fiscal", 1, "Q", "HO"), (_PREF_GUARA, "Relatório de Gestão Fiscal", 2, "Q", "HO"),
       (_PREF_GUARA, "Relatório de Gestão Fiscal", 3, "Q", "RE")]
    + [(_PREF_GUARA, "Relatório Resumido de Execução Orçamentária", b, "B", "RE" if b == 6 else "HO") for b in range(1, 7)]
)


def itens_extrato(linhas, cod_ibge, populacao, ano=2025):
    return [{"exercicio": ano, "cod_ibge": cod_ibge, "populacao": populacao, "instituicao": inst, "entregavel": ent,
             "periodo": per, "periodicidade": peri, "status_relatorio": sit, "data_status": None,
             "forma_envio": None, "tipo_relatorio": None} for inst, ent, per, peri, sit in linhas]


# Endpoint `entes`: 4 linhas reais (SP) e uma montada no formato real para Guarapuava.
ENTES = [
    {"cod_ibge": 3503406, "ente": "Arealva", "capital": "0 ", "regiao": "SE", "uf": "SP", "esfera": "M", "exercicio": 2026, "populacao": 8290, "cnpj": "46137428000181"},
    {"cod_ibge": 3503505, "ente": "Areias", "capital": "0 ", "regiao": "SE", "uf": "SP", "esfera": "M", "exercicio": 2026, "populacao": 3617, "cnpj": "45195963000126"},
    {"cod_ibge": 3503604, "ente": "Areiópolis", "capital": "0 ", "regiao": "SE", "uf": "SP", "esfera": "M", "exercicio": 2026, "populacao": 10242, "cnpj": "46634515000144"},
    {"cod_ibge": 3503703, "ente": "Ariranha", "capital": "0 ", "regiao": "SE", "uf": "SP", "esfera": "M", "exercicio": 2026, "populacao": 7621, "cnpj": "45117116000143"},
    {"cod_ibge": 4109401, "ente": "Guarapuava", "capital": "0 ", "regiao": "S", "uf": "PR", "esfera": "M", "exercicio": 2026, "populacao": 189630, "cnpj": "76178037000176"},
]
