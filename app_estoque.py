import streamlit as st
import oracledb
import pandas as pd
import plotly.express as px

# 1. CONEXÃO COM O BANCO (DADOS REAIS DA FILIAL 3)
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
        
        # Cruzamento de dados (JOIN)
        df_final = pd.merge(df_estoque, df_nomes, on="Código", how="left")
        
        # AJUSTE 1: Remover quem não está no Excel
        df_final = df_final.dropna(subset=['Descrição'])
        
        # AJUSTE 2: Reordenar colunas (Descrição ao lado de Código)
        colunas = ['Código', 'Descrição', 'Estoque', 'Estoque Disponível', 'Venda Mês']
        return df_final[colunas]
    except Exception as e:
        st.error(f"Erro na integração: {e}")
        return None

# 2. INTERFACE ESTOQUE SERIDOENSE
st.set_page_config(page_title="Estoque Seridoense", layout="wide")
st.title("📦 Estoque Seridoense - Setor Fiscal")
st.markdown("---")

df = carregar_dados()

if df is not None:
    # KPIs principais
    c1, c2, c3 = st.columns(3)
    c1.metric("Produtos Cadastrados", len(df))
    c2.metric("Estoque Disponível", f"{df['Estoque Disponível'].sum():,.0f} kg")
    c3.metric("Volume de Venda", f"{df['Venda Mês'].sum():,.0f} kg")

    # Gráficos
    col_graf, col_tab = st.columns([1.2, 1])

    with col_graf:
        st.subheader("Top 15 - Ranking de Vendas")
        df_top = df.nlargest(15, 'Venda Mês')
        fig = px.bar(df_top, x='Venda Mês', y='Descrição', orientation='h', 
                     color='Venda Mês', color_continuous_scale='Blues')
        st.plotly_chart(fig, use_container_width=True)

    with col_tab:
        st.subheader("Análise de Pareto (Curva de Venda)")
        df_p = df.sort_values("Venda Mês", ascending=False).copy()
        df_p['% Acumulado'] = (df_p['Venda Mês'] / df_p['Venda Mês'].sum() * 100).cumsum()
        fig_p = px.line(df_p, x='Descrição', y='% Acumulado', markers=True)
        st.plotly_chart(fig_p, use_container_width=True)

    # Detalhamento Geral com os ajustes solicitados
    st.subheader("📋 Detalhamento Geral (Apenas itens do Excel)")
    st.dataframe(df, use_container_width=True, hide_index=True)