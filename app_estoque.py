import streamlit as st
import oracledb
import pandas as pd
import plotly.express as px

# 1. CONFIGURAÇÃO DO AMBIENTE (CLIENTE ORACLE)
if 'oracle_client_initialized' not in st.session_state:
    try:
        caminho_client = r"C:\oracle\instantclient_19_29"
        oracledb.init_oracle_client(lib_dir=caminho_client)
        st.session_state['oracle_client_initialized'] = True
    except Exception as e:
        st.error(f"Erro no Oracle Client: {e}")

# 2. FUNÇÃO DE CARREGAMENTO DE DADOS
@st.cache_data(ttl=600)
def carregar_dados():
    conn_params = {"user": "NUTRICAO", "password": "nutr1125mmf", "dsn": "192.168.222.20:1521/WINT"}
    try:
        conn = oracledb.connect(**conn_params)
        
        # Tentativa 1: Usando nomes de colunas padrão para Avaria e Custo
        query = """SELECT 
                    CODPROD, QTESTGER, QTRESERV, QTBLOQUEADA,
                    QTAVARIA, CUSTOREAL,
                    QTVENDMES, QTVENDMES1, QTVENDMES2, QTVENDMES3
                   FROM MMFRIOS.PCEST 
                   WHERE CODFILIAL = 3 AND QTESTGER > 0"""
        
        try:
            df_estoque = pd.read_sql(query, conn)
        except:
            # Tentativa 2: Caso o WinThor use QTAVARIADO e CUSTOCONT
            query_alt = """SELECT 
                            CODPROD, QTESTGER, QTRESERV, QTBLOQUEADA,
                            QTAVARIADO as QTAVARIA, CUSTOCONT as CUSTOREAL,
                            QTVENDMES, QTVENDMES1, QTVENDMES2, QTVENDMES3
                           FROM MMFRIOS.PCEST 
                           WHERE CODFILIAL = 3 AND QTESTGER > 0"""
            df_estoque = pd.read_sql(query_alt, conn)
            
        conn.close()

        # Renomeação das colunas para o Dashboard
        df_estoque.columns = [
            'Código', 'Estoque', 'Reservado', 'Bloqueado', 
            'Avaria', 'Custo Contábil', 'Venda Mês', 
            'Venda Mês 1', 'Venda Mês 2', 'Venda Mês 3'
        ]
        
        # Cálculo da coluna Disponível solicitado (Estoque - Reservado - Bloqueado)
        df_estoque['Disponível'] = df_estoque['Estoque'] - df_estoque['Reservado'] - df_estoque['Bloqueado']

        # Integração com Excel de Nomes
        df_nomes = pd.read_excel("BASE_DESCRICOES_PRODUTOS.xlsx")
        df_nomes.columns = ['Código', 'Descrição']
        
        # Merge e Filtro para não aparecer "NÃO CADASTRADO NO EXCEL"
        df_final = pd.merge(df_estoque, df_nomes, on="Código", how="left")
        df_final = df_final.dropna(subset=['Descrição'])
        
        # Reordenar as colunas conforme solicitado
        ordem_colunas = [
            'Código', 'Descrição', 'Estoque', 'Reservado', 'Avaria', 
            'Disponível', 'Custo Contábil', 'Venda Mês', 'Venda Mês 1', 
            'Venda Mês 2', 'Venda Mês 3'
        ]
        return df_final[ordem_colunas]
    except Exception as e:
        st.error(f"Erro ao conectar no WinThor: {e}")
        return None

# 3. INTERFACE VISUAL - ESTOQUE SERIDOENSE
st.set_page_config(page_title="Estoque Seridoense", layout="wide")
st.title("📦 Estoque Seridoense - Setor Fiscal")
st.markdown("---")

df = carregar_dados()

if df is not None:
    # Indicadores de Topo (KPIs)
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Itens Cadastrados", len(df))
    kpi2.metric("Total Disponível", f"{df['Disponível'].sum():,.0f} kg")
    kpi3.metric("Total Reservado", f"{df['Reservado'].sum():,.0f} kg")
    kpi4.metric("Custo Total", f"R$ {df['Custo Contábil'].sum():,.2f}")

    # --- GRÁFICO GRANDE TOP 20 ESTOQUE ---
    st.subheader("🥩 Top 20 - Maior Volume em Estoque")
    df_top_est = df.nlargest(20, 'Estoque')
    fig_est = px.bar(df_top_est, x='Descrição', y='Estoque', 
                     color='Estoque', color_continuous_scale='Greens',
                     text_auto='.2s')
    st.plotly_chart(fig_est, use_container_width=True)

    st.markdown("---")

    # Gráficos Lado a Lado (Vendas e Pareto)
    col_venda, col_pareto = st.columns(2)
    
    with col_venda:
        st.subheader("🏆 Ranking de Vendas (Top 15)")
        df_v = df.nlargest(15, 'Venda Mês')
        fig_v = px.bar(df_v, x='Venda Mês', y='Descrição', orientation='h', 
                       color='Venda Mês', color_continuous_scale='Blues')
        st.plotly_chart(fig_v, use_container_width=True)
        
    with col_pareto:
        st.subheader("📈 Curva Pareto (Vendas)")
        df_p = df.sort_values("Venda Mês", ascending=False).copy()
        df_p['% Acc'] = (df_p['Venda Mês'] / df_p['Venda Mês'].sum() * 100).cumsum()
        fig_p = px.line(df_p, x='Descrição', y='% Acc', markers=True)
        st.plotly_chart(fig_p, use_container_width=True)

    # DETALHAMENTO GERAL
    st.subheader("📋 Detalhamento Geral")
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Rodapé informativo
    st.info("Os dados acima são atualizados a cada 10 minutos diretamente do banco WinThor.")