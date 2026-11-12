"""Portal de indicadores fiscais do município (Streamlit).

Rode `python coletar.py` antes, para gerar a pasta data/, e depois:
    streamlit run app.py
"""

import streamlit as st

from despesas import config

cidade = config.NOME_ENTE.split(" - ")[0]
st.set_page_config(page_title=f"{cidade} em números", page_icon=":material/account_balance:", layout="wide")

paginas = [
    st.Page("paginas/indicadores.py", title="Indicadores", icon=":material/monitoring:", default=True),
    st.Page("paginas/despesa.py", title="Despesa detalhada", icon=":material/table_chart:", url_path="despesa"),
]
st.navigation(paginas, position="top").run()
