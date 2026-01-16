import streamlit as st
import oracledb
import pandas as pd
import plotly.express as px

# 1. CONFIGURAÇÃO DO AMBIENTE
if 'oracle_client_initialized' not in st.session_state:
    try:
        # Ajuste para o seu caminho local do Instant Client
        caminho_client = r"C:\oracle\instantclient_19_29"
        oracledb.init_oracle_client(lib_dir=caminho_client)
        st.session_state['oracle_client_initialized'] = True
    except Exception as e:
        st.error(f"Erro no Oracle Client: {e}")

# 2. CARREGAMENTO DE DADOS COM TRATAMENTO DE ERRO DE COLUNA
@st.cache_data(ttl=600)
def carregar_dados():
    conn_params = {"user": "NUTRICAO", "password": "nutr1125mmf", "dsn": "192.168.222.20:1521/WINT"}
    try:
        conn = oracledb.connect(**conn_params)
        
        # SQL com as colunas que TEMOS CERTEZA que existem
        query = """SELECT 
                    CODPROD, QTESTGER, QTRESERV, QTBLOQUEADA,
                    QTVENDMES, QTVENDMES1, QTVENDMES2, QTVENDMES3
                   FROM MMFRIOS.PCEST 
                   WHERE CODFILIAL = 3 AND QTESTGER > 0"""
        
        df = pd.read_sql(query, conn)
        
        # Tentativa de buscar Avaria e Custo de forma isolada para não quebrar o app
        # Testamos QTAVARIA (comum no WinThor) e CUSTOFIN
        try:
            extra_query = "SELECT CODPROD, QTAVARIA, CUSTOFIN FROM MMFRIOS.PCEST WHERE CODFILIAL = 3"
            df_extra = pd.read_sql(extra_query, conn)
            df = pd.merge(df, df_extra, on="CODPROD", how="left")
        except:
            # Se der erro de "invalid identifier", criamos as colunas com 0 manualmente
            df['QTAVARIA'] = 0
            df['CUSTOFIN'] = 0
            
        conn.close()

        # Renomeação para o Dashboard
        df.columns = [
            'Código', 'Estoque', 'Reservado', 'Bloqueado', 'Venda Mês', 
            'Venda Mês 1', 'Venda Mês 2', 'Venda Mês 3', 'Avaria', 'Custo Contábil'
        ]
        
        # Cálculo do Disponível solicitado
        df['Disponível'] = df['Estoque'] - df['Reservado'] - df['Bloqueado']

        # Cruzamento com sua base Excel
        df_nomes = pd.read_excel("BASE_DESCRICOES_PRODUTOS.xlsx")
        df_nomes.columns = ['Código', 'Descrição']
        
        df_final = pd.merge(df, df_nomes, on="Código", how="left")
        
        # AJUSTE: Remove quem não está no Excel para manter o foco
        df_final = df_final.dropna(subset=['Descrição'])
        
        ordem = ['Código', 'Descrição', 'Estoque', 'Reservado', 'Avaria', 'Disponível', 
                 'Custo Contábil', 'Venda Mês', 'Venda Mês 1', 'Venda Mês 2', 'Venda Mês 3']
        
        return df_final[ordem]
    except Exception as e:
        st.error(f"Erro na conexão com o banco WinThor: {e}")
        return None

# 3. INTERFACE VISUAL - ESTOQUE SERIDOENSE
st.set_page_config(page_title="Estoque Seridoense", layout="wide")
st.title("📦 Estoque Seridoense - Setor Fiscal")
st.markdown("---")

df = carregar_dados()

if df is not None:
    # KPIs de resumo
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Itens Monitorados", len(df))
    c2.metric("Total Disponível", f"{df['Disponível'].sum():,.0f} kg")
    c3.metric("Total Reservado", f"{df['Reservado'].sum():,.0f} kg")
    c4.metric("Custo Total", f"R$ {df['Custo Contábil'].sum():,.2f}")

    # Gráfico Top 20 Estoque
    st.subheader("🥩 Top 20 - Maior Volume em Estoque")
    df_top_est = df.nlargest(20, 'Estoque')
    fig_est = px.bar(df_top_est, x='Descrição', y='Estoque', color='Estoque', color_continuous_scale='Greens')
    st.plotly_chart(fig_est, use_container_width=True)

    st.markdown("---")

    col_v, col_p = st.columns(2)
    with col_v:
        st.subheader("🏆 Ranking de Vendas (Top 15)")
        df_v = df.nlargest(15, 'Venda Mês')
        st.plotly_chart(px.bar(df_v, x='Venda Mês', y='Descrição', orientation='h', color='Venda Mês'), use_container_width=True)
    with col_p:
        st.subheader("📈 Curva Pareto")
        df_pa = df.sort_values("Venda Mês", ascending=False).copy()
        df_pa['% Acc'] = (df_pa['Venda Mês'] / df_pa['Venda Mês'].sum() * 100).cumsum()
        st.plotly_chart(px.line(df_pa, x='Descrição', y='% Acc', markers=True), use_container_width=True)

    # Tabela detalhada
    st.subheader("📋 Detalhamento Geral")
    st.dataframe(df, use_container_width=True, hide_index=True)
    