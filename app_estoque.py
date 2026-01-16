import streamlit as st
import oracledb
import pandas as pd
import plotly.express as px

# 1. CONEXÃO COM O BANCO (DADOS REAIS)
if 'oracle_client_initialized' not in st.session_state:
    try:
        caminho_client = r"C:\oracle\instantclient_19_29"
        oracledb.init_oracle_client(lib_dir=caminho_client)
        st.session_state['oracle_client_initialized'] = True
    except Exception as e:
        st.error(f"Erro no Oracle Client: {e}")

@st.cache_data(ttl=600)
def carregar_dados():
    conn_params = {"user": "NUTRICAO", "password": "nutr1125mmf", "dsn": "192.168.222.20:1521/WINT"}
    try:
        conn = oracledb.connect(**conn_params)
        query = """SELECT CODPROD AS "Código", QTESTGER AS "Estoque", 
                   (QTESTGER - QTRESERV - QTBLOQUEADA) AS "Estoque Disponível",
                   QTVENDMES AS "Venda Mês" FROM MMFRIOS.PCEST 
                   WHERE CODFILIAL = 3 AND QTESTGER > 0"""
        df_estoque = pd.read_sql(query, conn)
        conn.close()

        # Sua base do Excel com nomes
        df_nomes = pd.read_excel("BASE_DESCRICOES_PRODUTOS.xlsx")
        df_nomes.columns = ['Código', 'Descrição']
        df_final = pd.merge(df_estoque, df_nomes, on="Código", how="left")
        df_final['Descrição'] = df_final['Descrição'].fillna('NÃO CADASTRADO NO EXCEL')
        return df_final
    except Exception as e:
        st.error(f"Erro na integração: {e}")
        return None

# 2. INTERFACE ESTOQUE SERIDOENSE
st.set_page_config(page_title="Estoque Seridoense", layout="wide")
st.title("📦 Estoque Seridoense - Setor Fiscal")
st.markdown("---")

df = carregar_dados()

if df is not None:
    # KPIs
    c1, c2, c3 = st.columns(3)
    c1.metric("Produtos Monitorados", len(df))
    c2.metric("Estoque Disponível (Total)", f"{df['Estoque Disponível'].sum():,.0f} kg")
    c3.metric("Volume de Venda", f"{df['Venda Mês'].sum():,.0f} kg")

    # Gráficos e Tabelas
    col_graf, col_tab = st.columns([1.2, 1])

    with col_graf:
        st.subheader("Top 15 - Ranking de Vendas")
        df_top = df.nlargest(15, 'Venda Mês')
        fig = px.bar(df_top, x='Venda Mês', y='Descrição', orientation='h', color='Venda Mês')
        st.plotly_chart(fig, use_container_width=True)

    with col_tab:
        st.subheader("Curva Pareto (Acumulado)")
        df_p = df.sort_values("Venda Mês", ascending=False).copy()
        df_p['% Acumulado'] = (df_p['Venda Mês'] / df_p['Venda Mês'].sum() * 100).cumsum()
        fig_p = px.line(df_p, x='Descrição', y='% Acumulado')
        st.plotly_chart(fig_p, use_container_width=True)

    st.subheader("📋 Detalhamento Geral")
    st.dataframe(df, use_container_width=True, hide_index=True)