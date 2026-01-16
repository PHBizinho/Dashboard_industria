import streamlit as st
import oracledb
import pandas as pd
import plotly.express as px

# 1. CONFIGURAÇÃO DO AMBIENTE
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
        
        # SQL Seguro: Trazemos apenas o que é garantido existir primeiro
        query = """SELECT 
                    CODPROD, QTESTGER, QTRESERV, QTBLOQUEADA,
                    QTVENDMES, QTVENDMES1, QTVENDMES2, QTVENDMES3
                   FROM MMFRIOS.PCEST 
                   WHERE CODFILIAL = 3 AND QTESTGER > 0"""
        
        df_estoque = pd.read_sql(query, conn)
        
        # Tentativa de buscar Custo e Avaria separadamente para não travar o código todo
        try:
            df_extra = pd.read_sql("SELECT CODPROD, CUSTOCONT, QTAVARIADO FROM MMFRIOS.PCEST WHERE CODFILIAL = 3", conn)
            df_estoque = pd.merge(df_estoque, df_extra, on="CODPROD", how="left")
        except:
            # Se falhar, criamos colunas vazias para o app não dar erro de "identificador inválido"
            df_estoque['CUSTOCONT'] = 0
            df_estoque['QTAVARIADO'] = 0
            
        conn.close()

        # Renomeação amigável
        df_estoque.columns = [
            'Código', 'Estoque', 'Reservado', 'Bloqueado', 'Venda Mês', 
            'Venda Mês 1', 'Venda Mês 2', 'Venda Mês 3', 'Custo Contábil', 'Avaria'
        ]
        
        # Cálculo da coluna Disponível solicitado
        df_estoque['Disponível'] = df_estoque['Estoque'] - df_estoque['Reservado'] - df_estoque['Bloqueado']

        # Integração com Excel
        df_nomes = pd.read_excel("BASE_DESCRICOES_PRODUTOS.xlsx")
        df_nomes.columns = ['Código', 'Descrição']
        
        df_final = pd.merge(df_estoque, df_nomes, on="Código", how="left")
        df_final = df_final.dropna(subset=['Descrição'])
        
        # Ordem final das colunas solicitada
        ordem = [
            'Código', 'Descrição', 'Estoque', 'Reservado', 'Avaria', 
            'Disponível', 'Custo Contábil', 'Venda Mês', 'Venda Mês 1', 
            'Venda Mês 2', 'Venda Mês 3'
        ]
        return df_final[ordem]
    except Exception as e:
        st.error(f"Erro ao acessar dados: {e}")
        return None

# 2. INTERFACE
st.set_page_config(page_title="Estoque Seridoense", layout="wide")
st.title("📦 Estoque Seridoense - Setor Fiscal")
st.markdown("---")

df = carregar_dados()

if df is not None:
    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Produtos Mapeados", len(df))
    c2.metric("Total Disponível", f"{df['Disponível'].sum():,.0f} kg")
    c3.metric("Total Reservado", f"{df['Reservado'].sum():,.0f} kg")
    c4.metric("Custo Total", f"R$ {df['Custo Contábil'].sum():,.2f}")

    # Top 20 Estoque (Verde)
    st.subheader("🥩 Top 20 - Maior Volume em Estoque")
    df_top_est = df.nlargest(20, 'Estoque')
    fig_est = px.bar(df_top_est, x='Descrição', y='Estoque', color='Estoque', color_continuous_scale='Greens')
    st.plotly_chart(fig_est, use_container_width=True)

    st.markdown("---")

    # Ranking e Pareto
    col_venda, col_pareto = st.columns(2)
    with col_venda:
        st.subheader("🏆 Ranking de Vendas (Top 15)")
        df_v = df.nlargest(15, 'Venda Mês')
        st.plotly_chart(px.bar(df_v, x='Venda Mês', y='Descrição', orientation='h', color='Venda Mês'), use_container_width=True)
    with col_pareto:
        st.subheader("📈 Curva Pareto")
        df_p = df.sort_values("Venda Mês", ascending=False).copy()
        df_p['% Acc'] = (df_p['Venda Mês'] / df_p['Venda Mês'].sum() * 100).cumsum()
        st.plotly_chart(px.line(df_p, x='Descrição', y='% Acc', markers=True), use_container_width=True)

    st.subheader("📋 Detalhamento Geral")
    st.dataframe(df, use_container_width=True, hide_index=True)