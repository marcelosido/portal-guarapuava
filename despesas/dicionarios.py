"""Tabelas de descrição dos códigos usados na MSC.

A MSC traz apenas códigos. As descrições abaixo seguem a Portaria Interministerial
STN/SOF nº 163/2001 (natureza da despesa) e a Portaria MOG nº 42/1999 (funções),
com suas alterações. Códigos ausentes aparecem como "Elemento 99", "Modalidade 99"
etc. – confira com o Ementário da Despesa vigente antes de completar as tabelas.
"""

from __future__ import annotations

# Natureza da despesa: C.G.MM.EE.DD (categoria, grupo, modalidade, elemento, desdobramento)

CATEGORIA = {
    "3": "Despesas Correntes",
    "4": "Despesas de Capital",
    "7": "Reserva do RPPS",
    "9": "Reserva de Contingência",
}

GRUPO = {
    "1": "Pessoal e Encargos Sociais",
    "2": "Juros e Encargos da Dívida",
    "3": "Outras Despesas Correntes",
    "4": "Investimentos",
    "5": "Inversões Financeiras",
    "6": "Amortização da Dívida",
    "7": "Reserva do RPPS",
    "9": "Reserva de Contingência",
}

MODALIDADE = {
    "20": "Transferências à União",
    "30": "Transferências a Estados e ao Distrito Federal",
    "31": "Transferências a Estados e ao Distrito Federal - Fundo a Fundo",
    "40": "Transferências a Municípios",
    "41": "Transferências a Municípios - Fundo a Fundo",
    "50": "Transferências a Instituições Privadas sem Fins Lucrativos",
    "60": "Transferências a Instituições Privadas com Fins Lucrativos",
    "70": "Transferências a Instituições Multigovernamentais",
    "71": "Transferências a Consórcios Públicos mediante contrato de rateio",
    "72": "Execução Orçamentária Delegada a Consórcios Públicos",
    "80": "Transferências ao Exterior",
    "90": "Aplicações Diretas",
    "91": "Aplicação Direta Decorrente de Operação entre Órgãos, Fundos e Entidades "
    "Integrantes dos Orçamentos Fiscal e da Seguridade Social",
    "99": "A Definir",
}

ELEMENTO = {
    "00": "Não detalhado (nível de modalidade)",
    "01": "Aposentadorias do RPPS, Reserva Remunerada e Reformas dos Militares",
    "03": "Pensões do RPPS e do Militar",
    "04": "Contratação por Tempo Determinado",
    "05": "Outros Benefícios Previdenciários do Servidor ou do Militar",
    "07": "Contribuição a Entidades Fechadas de Previdência",
    "08": "Outros Benefícios Assistenciais do Servidor e do Militar",
    "09": "Salário-Família",
    "11": "Vencimentos e Vantagens Fixas - Pessoal Civil",
    "12": "Vencimentos e Vantagens Fixas - Pessoal Militar",
    "13": "Obrigações Patronais",
    "14": "Diárias - Civil",
    "16": "Outras Despesas Variáveis - Pessoal Civil",
    "18": "Auxílio Financeiro a Estudantes",
    "20": "Auxílio Financeiro a Pesquisadores",
    "21": "Juros sobre a Dívida por Contrato",
    "22": "Outros Encargos sobre a Dívida por Contrato",
    "30": "Material de Consumo",
    "31": "Premiações Culturais, Artísticas, Científicas, Desportivas e Outras",
    "32": "Material, Bem ou Serviço para Distribuição Gratuita",
    "33": "Passagens e Despesas com Locomoção",
    "34": "Outras Despesas de Pessoal Decorrentes de Contratos de Terceirização",
    "35": "Serviços de Consultoria",
    "36": "Outros Serviços de Terceiros - Pessoa Física",
    "37": "Locação de Mão de Obra",
    "38": "Arrendamento Mercantil",
    "39": "Outros Serviços de Terceiros - Pessoa Jurídica",
    "40": "Serviços de Tecnologia da Informação e Comunicação - Pessoa Jurídica",
    "41": "Contribuições",
    "42": "Auxílios",
    "43": "Subvenções Sociais",
    "45": "Subvenções Econômicas",
    "46": "Auxílio-Alimentação",
    "47": "Obrigações Tributárias e Contributivas",
    "48": "Outros Auxílios Financeiros a Pessoas Físicas",
    "49": "Auxílio-Transporte",
    "51": "Obras e Instalações",
    "52": "Equipamentos e Material Permanente",
    "61": "Aquisição de Imóveis",
    "65": "Constituição ou Aumento de Capital de Empresas",
    "66": "Concessão de Empréstimos e Financiamentos",
    "70": "Rateio pela Participação em Consórcio Público",
    "71": "Principal da Dívida Contratual Resgatado",
    "81": "Distribuição Constitucional ou Legal de Receitas",
    "84": "Despesas Decorrentes da Participação em Fundos, Organismos ou Entidades Assemelhadas",
    "85": "Contrato de Gestão",
    "91": "Sentenças Judiciais",
    "92": "Despesas de Exercícios Anteriores",
    "93": "Indenizações e Restituições",
    "94": "Indenizações e Restituições Trabalhistas",
    "96": "Ressarcimento de Despesas de Pessoal Requisitado",
    "97": "Aporte para Cobertura do Déficit Atuarial do RPPS",
    "99": "A Classificar",
}

# Classificação funcional (Portaria MOG nº 42/1999)
FUNCAO = {
    "01": "Legislativa",
    "02": "Judiciária",
    "03": "Essencial à Justiça",
    "04": "Administração",
    "05": "Defesa Nacional",
    "06": "Segurança Pública",
    "07": "Relações Exteriores",
    "08": "Assistência Social",
    "09": "Previdência Social",
    "10": "Saúde",
    "11": "Trabalho",
    "12": "Educação",
    "13": "Cultura",
    "14": "Direitos da Cidadania",
    "15": "Urbanismo",
    "16": "Habitação",
    "17": "Saneamento",
    "18": "Gestão Ambiental",
    "19": "Ciência e Tecnologia",
    "20": "Agricultura",
    "21": "Organização Agrária",
    "22": "Indústria",
    "23": "Comércio e Serviços",
    "24": "Comunicações",
    "25": "Energia",
    "26": "Transporte",
    "27": "Desporto e Lazer",
    "28": "Encargos Especiais",
    "99": "Reserva de Contingência",
}

# Poder/órgão da MSC. Rótulos INFERIDOS a partir dos dados de Guarapuava (ago/2026):
# 10132 só tem funções 09 e 04 (aposentadorias, pensões e reserva) -> RPPS;
# 20231 só tem função 01 (Legislativa) -> Câmara; 10131 concentra o restante,
# inclusive fundos e fundações. Confirme com a tabela de Poder/Órgão da STN.
PODER_ORGAO = {
    "10131": "Executivo (Prefeitura, fundos e fundações)",
    "10132": "RPPS (Guarapuava Prev)",
    "20231": "Legislativo (Câmara Municipal)",
}

NOMES_MES = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}
SIGLAS_MES = {m: n[:3] for m, n in NOMES_MES.items()}


def descrever(tabela: dict[str, str], codigo: str, rotulo: str) -> str:
    """Devolve a descrição do código ou um rótulo genérico ("Elemento 77")."""
    return tabela.get(codigo, f"{rotulo} {codigo}")
