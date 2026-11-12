"""Portal "Guarapuava em números": navegação entre as páginas."""

import streamlit as st

from despesas import config

cidade = config.NOME_ENTE.split(" - ")[0]
st.set_page_config(page_title=f"{cidade} em números", page_icon=":material/account_balance:", layout="wide")

paginas = [
    st.Page("paginas/indicadores.py", title="Visão geral", icon=":material/monitoring:", default=True),
    st.Page("paginas/receitas.py", title="Receitas", icon=":material/payments:", url_path="receitas"),
    st.Page("paginas/despesa.py", title="Despesas", icon=":material/receipt_long:", url_path="despesa"),
    st.Page("paginas/compras.py", title="Compras", icon=":material/gavel:", url_path="compras"),
    st.Page("paginas/comparar.py", title="Comparar cidades", icon=":material/map:", url_path="comparar"),
    st.Page("paginas/sobre.py", title="Sobre os dados", icon=":material/info:", url_path="sobre"),
]
st.navigation(paginas, position="top").run()
