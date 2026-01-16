import streamlit as st
import oracledb
import pandas as pd
import plotly.express as px

# 1. CONFIGURAÇÃO DO AMBIENTE (CLIENTE ORACLE PARA WINDOWS)
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
        # SQL Corrigido: Usando QTAVARIADO (nome técnico padrão no WinThor para evitar erro de identificador)
        query = """SELECT 
                    CODPROD AS "Código", 
                    QTESTGER AS "Estoque", 
                    QTRESERV AS "Reservado",
                    QTAVARIADO AS "Avaria",
                    (QTESTGER - QTRESERV - QTBLOQUEADA) AS "Disponível",
                    CUSTOCONT AS "Custo Contábil",
                    QTVENDMES AS "Venda Mês",
                    QTVENDMES1 AS "Venda Mês 1",
                    QTVENDMES2 AS "Venda Mês 2",
                    QTVENDMES3 AS "Venda Mês 3"
                   FROM MMFRIOS.PCEST 
                   WHERE CODFILIAL = 3 AND QTESTGER > 0"""
        df_estoque = pd.read_sql(query, conn)
        conn.close()

        # Sua base do Excel com nomes
        df_nomes = pd.read_excel("BASE_DESCRICOES_PRODUTOS.xlsx")
        df_nomes.columns = ['Código', 'Descrição']
        
        # Cruzamento de dados e filtro de itens cadastrados
        df_final = pd.merge(df_estoque, df_nomes, on="Código", how="left")
        df_final = df_final.dropna(subset=['Descrição'])
        
        # Ordem das colunas solicitada para o Detalhamento Geral
        colunas_finais = [
            'Código', 'Descrição', 'Estoque', 'Reservado', 'Avaria', 
            'Disponível', 'Custo Contábil', 'Venda Mês', 'Venda Mês 1', 
            'Venda Mês 2', 'Venda Mês 3'
        ]
        return df_final[colunas_finais]
    except Exception as e:
        st.error(f"Erro técnico no banco: {e}")
        return None

# 2. INTERFACE ESTOQUE SERIDOENSE
st.set_page_config(page_title="Estoque Seridoense", layout="wide")
st.title("📦 Estoque Seridoense - Setor Fiscal")
st.markdown("---")

df = carregar_dados()

if df is not None:
    # KPIs principais no topo
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Itens Mapeados", len(df))
    c2.metric("Total Disponível", f"{df['Disponível'].sum():,.0f} kg")
    c3.metric("Total Reservado", f"{df['Reservado'].sum():,.0f} kg")
    c4.metric("Custo Contábil Total", f"R$ {df['Custo Contábil'].sum():,.2f}")

    # --- GRÁFICO GRANDE TOP 20 ESTOQUE ---
    st.subheader("🥩 Top 20 - Maior Volume em Estoque")
    df_top_est = df.nlargest(20, 'Estoque')
    fig_est = px.bar(df_top_est, x='Descrição', y='Estoque', 
                     color='Estoque', color_continuous_scale='Greens',
                     text_auto='.2s')
    st.plotly_chart(fig_est, use_container_width=True)

    st.markdown("---")

    col_graf, col_tab = st.columns([1, 1])
    with col_graf:
        st.subheader("🏆 Ranking de Vendas (Top 15)")
        df_top_venda = df.nlargest(15, 'Venda Mês')
        fig_venda = px.bar(df_top_venda, x='Venda Mês', y='Descrição', orientation='h', 
                           color='Venda Mês', color_continuous_scale='Blues')
        st.plotly_chart(fig_venda, use_container_width=True)

    with col_tab:
        st.subheader("📈 Curva Pareto de Vendas")
        df_p = df.sort_values("Venda Mês", ascending=False).copy()
        df_p['% Acumulado'] = (df_p['Venda Mês'] / df_p['Venda Mês'].sum() * 100).cumsum()
        fig_p = px.line(df_p, x='Descrição', y='% Acumulado', markers=True)
        st.plotly_chart(fig_p, use_container_width=True)

    # DETALHAMENTO GERAL
    st.subheader("📋 Detalhamento Geral")
    st.dataframe(df, use_container_width=True, hide_index=True)