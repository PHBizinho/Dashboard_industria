import streamlit as st
import oracledb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. CONFIGURAÇÃO AMBIENTE
if 'oracle_client_initialized' not in st.session_state:
    try:
        oracledb.init_oracle_client(lib_dir=r"C:\oracle\instantclient_19_29")
        st.session_state['oracle_client_initialized'] = True
    except Exception as e:
        st.error(f"Erro Client: {e}")

@st.cache_data(ttl=600)
def carregar_dados():
    conn_params = {"user": "NUTRICAO", "password": "nutr1125mmf", "dsn": "192.168.222.20:1521/WINT"}
    try:
        conn = oracledb.connect(**conn_params)
        query = """SELECT CODPROD, QTESTGER, QTRESERV, QTBLOQUEADA, QTVENDMES, 
                          QTVENDMES1, QTVENDMES2, QTVENDMES3, CUSTOREAL 
                   FROM MMFRIOS.PCEST WHERE CODFILIAL = 3 AND QTESTGER > 0"""
        df = pd.read_sql(query, conn)
        conn.close()
        
        df_nomes = pd.read_excel("BASE_DESCRICOES_PRODUTOS.xlsx")
        df_nomes.columns = ['Código', 'Descrição']
        df_final = pd.merge(df, df_nomes, left_on="CODPROD", right_on="Código", how="inner")
        
        # Cálculos fundamentais
        df_final['Disponível'] = df_final['QTESTGER'] - df_final['QTRESERV'] - df_final['QTBLOQUEADA']
        df_final['Valor em Estoque'] = df_final['QTESTGER'] * df_final['CUSTOREAL']
        df_final['VENDA_RS'] = df_final['QTVENDMES'] * df_final['CUSTOREAL']
        
        return df_final
    except Exception as e:
        st.error(f"Erro ao conectar no banco: {e}")
        return None

def obter_nomes_meses():
    meses_pt = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun", 
                7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}
    hoje = datetime.now()
    lista_meses = []
    for i in range(4):
        # Lógica para garantir a data correta dos meses anteriores
        data = (hoje.replace(day=1) - timedelta(days=1 if i > 0 else 0))
        if i == 1: data = hoje.replace(day=1) - timedelta(days=1)
        if i == 2: data = (hoje.replace(day=1) - timedelta(days=1)).replace(day=1) - timedelta(days=1)
        if i == 3: data = ((hoje.replace(day=1) - timedelta(days=1)).replace(day=1) - timedelta(days=1)).replace(day=1) - timedelta(days=1)
        
        nome = f"{meses_pt[data.month]}/{str(data.year)[2:]}"
        lista_meses.append(nome)
    return lista_meses

# 2. INTERFACE
st.set_page_config(page_title="Dashboard Estoque - Seridoense", layout="wide")

st.title("📊 Dashboard Estoque - Seridoense")
st.markdown("*Desenvolvido por: **Paulo Henrique**, Setor Fiscal*") #
st.markdown("---")

df = carregar_dados()

if df is not None:
    # --- GRÁFICOS (MANTIDOS CONFORME SOLICITAÇÕES ANTERIORES) ---
    st.subheader("🥩 Top 20 - Volume Físico em Estoque (kg)")
    df_top20 = df.nlargest(20, 'QTESTGER').sort_values('QTESTGER', ascending=True)
    fig_estoque = px.bar(df_top20, x='QTESTGER', y='Descrição', orientation='h',
                         color='QTESTGER', color_continuous_scale='Greens',
                         text_auto='.2f')
    fig_estoque.update_traces(textposition='outside')
    st.plotly_chart(fig_estoque, use_container_width=True)

    st.markdown("---")

    # --- TABELA DETALHAMENTO GERAL COM FORMATAÇÃO SOLICITADA ---
    st.subheader("📋 Detalhamento Geral")
    
    # Preparando os dados para a tabela final
    df_tabela = df[['Código', 'Descrição', 'QTESTGER', 'Disponível', 'CUSTOREAL', 'Valor em Estoque', 'VENDA_RS']].copy()
    
    # Mudança de nomes das colunas conforme solicitado
    df_tabela = df_tabela.rename(columns={
        'QTESTGER': 'Estoque geral',
        'CUSTOREAL': 'Custo Real (R$)',
        'VENDA_RS': 'Venda Mês Atual (R$)'
    })

    # Exibição com formatação de Unidades e Moeda
    st.dataframe(
        df_tabela,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Estoque geral": st.column_config.NumberColumn("Estoque geral", format="%.2f Kg"),
            "Disponível": st.column_config.NumberColumn("Disponível", format="%.2f Kg"),
            "Custo Real (R$)": st.column_config.NumberColumn("Custo Real (R$)", format="R$ %.2f"),
            "Valor em Estoque": st.column_config.NumberColumn("Valor em Estoque", format="R$ %.2f"),
            "Venda Mês Atual (R$)": st.column_config.NumberColumn("Venda Mês Atual (R$)", format="R$ %.2f")
        }
    )

    st.info(f"Link de acesso local: http://192.168.1.19:8502")