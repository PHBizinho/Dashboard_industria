import streamlit as st
import oracledb
import pandas as pd
import plotly.express as px  # Para gráficos mais bonitos

# 1. CONFIGURAÇÃO DO AMBIENTE (CLIENTE ORACLE)
if 'oracle_client_initialized' not in st.session_state:
    try:
        caminho_client = r"C:\oracle\instantclient_19_29"
        oracledb.init_oracle_client(lib_dir=caminho_client)
        st.session_state['oracle_client_initialized'] = True
    except Exception as e:
        st.error(f"Erro ao carregar Instant Client: {e}")

# 2. FUNÇÃO DE DADOS
@st.cache_data(ttl=600) # Atualiza a cada 10 min para não sobrecarregar o banco
def carregar_dados_completos():
    conn_params = {
        "user": "NUTRICAO", "password": "nutr1125mmf",
        "dsn": "192.168.222.20:1521/WINT"
    }
    try:
        conn = oracledb.connect(**conn_params)
        query = """
        SELECT CODPROD AS "Código", QTESTGER AS "Estoque", 
               (QTESTGER - QTRESERV - QTBLOQUEADA) AS "Estoque Disponível",
               QTVENDMES AS "Venda Mês", QTVENDMES1 AS "Venda Mês 1"
        FROM MMFRIOS.PCEST WHERE CODFILIAL = 3 AND QTESTGER > 0
        """
        df_estoque = pd.read_sql(query, conn)
        conn.close()

        # Integração com seu Excel de Nomes
        df_nomes = pd.read_excel("BASE_DESCRICOES_PRODUTOS.xlsx")
        df_nomes.columns = ['Código', 'Descrição']
        df_final = pd.merge(df_estoque, df_nomes, on="Código", how="left")
        df_final['Descrição'] = df_final['Descrição'].fillna('NÃO CADASTRADO NO EXCEL')
        
        return df_final
    except Exception as e:
        st.error(f"Erro no Banco: {e}")
        return None

# 3. INTERFACE VISUAL
st.set_page_config(page_title="Estoque Filial 3", layout="wide")
st.title("📊 Painel de Vendas e Estoque - Filial 3")

df = carregar_dados_completos()

if df is not None:
    # KPIs de Topo
    m1, m2, m3 = st.columns(3)
    m1.metric("Itens em Estoque", len(df))
    m2.metric("Volume Venda (Mês)", f"{df['Venda Mês'].sum():,.0f} kg")
    m3.metric("Estoque Total", f"{df['Estoque'].sum():,.0f} kg")

    tab1, tab2, tab3 = st.tabs(["📈 Gráficos de Venda", "📊 Curva Pareto", "📋 Dados Reais"])

    with tab1:
        st.subheader("Top 15 Produtos por Volume de Venda")
        df_top = df.nlargest(15, 'Venda Mês')
        fig_bar = px.bar(df_top, x='Venda Mês', y='Descrição', orientation='h', 
                         title="Ranking de Vendas (kg)", color='Venda Mês')
        st.plotly_chart(fig_bar, use_container_width=True)

    with tab2:
        st.subheader("Análise de Pareto (Acumulado)")
        df_p = df.sort_values("Venda Mês", ascending=False).copy()
        df_p['%'] = (df_p['Venda Mês'] / df_p['Venda Mês'].sum() * 100).cumsum()
        fig_pareto = px.line(df_p, x='Descrição', y='%', title="Curva ABC de Vendas")
        st.plotly_chart(fig_pareto, use_container_width=True)

    with tab3:
        st.dataframe(df, use_container_width=True, hide_index=True)