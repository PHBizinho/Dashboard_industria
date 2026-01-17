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
        
        df_final['Disponível'] = df_final['QTESTGER'] - df_final['QTRESERV'] - df_final['QTBLOQUEADA']
        df_final['Valor em Estoque'] = df_final['QTESTGER'] * df_final['CUSTOREAL']
        
        return df_final
    except Exception as e:
        st.error(f"Erro ao conectar no banco: {e}")
        return None

# Função para pegar nomes dos meses dinamicamente
def obter_nomes_meses():
    meses_pt = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun", 
                7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}
    
    hoje = datetime.now()
    lista_meses = []
    
    for i in range(4):
        # Calcula a data retroativa mês a mês
        data_retroativa = hoje.replace(day=1) - timedelta(days=i*30)
        # Ajuste para garantir que pegamos o mês correto mesmo com meses de 30/31 dias
        data_final = hoje.replace(day=1) if i == 0 else (hoje.replace(day=1) - timedelta(days=1)).replace(day=1)
        if i == 1: data_final = hoje.replace(day=1) - timedelta(days=1)
        if i == 2: data_final = (hoje.replace(day=1) - timedelta(days=1)).replace(day=1) - timedelta(days=1)
        if i == 3: data_final = ((hoje.replace(day=1) - timedelta(days=1)).replace(day=1) - timedelta(days=1)).replace(day=1) - timedelta(days=1)
        
        nome = f"{meses_pt[data_final.month]}/{str(data_final.year)[2:]}"
        lista_meses.append(nome)
        
    return lista_meses

# 2. INTERFACE
st.set_page_config(page_title="Estoque Seridoense", layout="wide")
st.title("📦 Estoque Seridoense - Setor Fiscal")
st.markdown("---")

df = carregar_dados()

if df is not None:
    # --- GRÁFICO 1: TOP 20 ESTOQUE ---
    st.subheader("🥩 Top 20 - Volume Físico em Estoque (kg)")
    df_top20 = df.nlargest(20, 'QTESTGER').sort_values('QTESTGER', ascending=True)
    
    fig_estoque = px.bar(df_top20, x='QTESTGER', y='Descrição', orientation='h',
                         color='QTESTGER', color_continuous_scale='Greens',
                         text_auto='.2f', labels={'QTESTGER': 'Estoque (kg)'})
    
    fig_estoque.update_traces(textposition='outside')
    fig_estoque.update_layout(height=500, showlegend=False)
    st.plotly_chart(fig_estoque, use_container_width=True)

    st.markdown("---")

    # --- ANÁLISE DE VENDAS COM NOMES DE MESES REAIS ---
    st.subheader("🏆 Análise de Performance e Histórico de Vendas")
    
    col_grafico, col_filtros = st.columns([4, 1])
    
    nomes_meses = obter_nomes_meses() # Pega os nomes como ['Jan/26', 'Dez/25', 'Nov/25', 'Out/25']

    with col_filtros:
        st.markdown("#### 🔍 Filtros")
        modo_venda = st.radio("Período:", ["Mês Atual", "Comparativo 4 Meses"])
        filtro_nome = st.multiselect("Pesquisar Cortes:", options=sorted(df['Descrição'].unique()))
    
    df_v_filt = df.copy()
    if filtro_nome:
        df_v_filt = df_v_filt[df_v_filt['Descrição'].isin(filtro_nome)]
    
    with col_grafico:
        if modo_venda == "Mês Atual":
            df_v = df_v_filt.nlargest(15, 'QTVENDMES')
            fig_v = px.bar(df_v, x='QTVENDMES', y='Descrição', orientation='h', 
                           color='QTVENDMES', color_continuous_scale='Blues', text_auto='.1f',
                           title=f"Ranking de Vendas - {nomes_meses[0]}")
        else:
            df_v = df_v_filt.nlargest(12, 'QTVENDMES')
            fig_v = go.Figure()
            
            # Mapeamento das colunas do banco para os nomes amigáveis calculados
            meses_config = [
                ('QTVENDMES', nomes_meses[0]),
                ('QTVENDMES1', nomes_meses[1]),
                ('QTVENDMES2', nomes_meses[2]),
                ('QTVENDMES3', nomes_meses[3])
            ]
            
            for col_db, nome_label in meses_config:
                fig_v.add_trace(go.Bar(name=nome_label, y=df_v['Descrição'], x=df_v[col_db], orientation='h'))
            
            fig_v.update_layout(barmode='group', title="Evolução das Vendas (Histórico Real)", height=600)
            fig_v.update_layout(legend_title_text='Período')
        
        st.plotly_chart(fig_v, use_container_width=True)

    st.markdown("---")

    # --- PARETO E TABELA ---
    c_pareto, c_tabela_resumo = st.columns([2, 1])
    with c_pareto:
        st.subheader("💰 Pareto: Impacto Financeiro (R$)")
        df_pareto = df.sort_values("Valor em Estoque", ascending=False).copy()
        df_pareto['% Acc'] = (df_pareto['Valor em Estoque'] / df_pareto['Valor em Estoque'].sum() * 100).cumsum()
        
        fig_p = go.Figure()
        fig_p.add_trace(go.Bar(x=df_pareto['Descrição'][:10], y=df_pareto['Valor em Estoque'][:10], name="Valor R$", marker_color='gold'))
        fig_p.add_trace(go.Scatter(x=df_pareto['Descrição'][:10], y=df_pareto['% Acc'][:10], name="% Acumulado", yaxis="y2", line=dict(color="red")))
        fig_p.update_layout(yaxis2=dict(overlaying="y", side="right", range=[0, 105]), height=400)
        st.plotly_chart(fig_p, use_container_width=True)

    st.subheader("📋 Detalhamento Geral")
    st.dataframe(df_v_filt[['Código', 'Descrição', 'QTESTGER', 'Disponível', 'CUSTOREAL', 'Valor em Estoque', 'QTVENDMES', 'QTVENDMES1']], 
                 use_container_width=True, hide_index=True)

    st.info(f"Link de acesso: http://192.168.1.19:8502 | Referência Atual: {nomes_meses[0]}")