import streamlit as st
import oracledb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. CONFIGURAÇÃO AMBIENTE
if 'oracle_client_initialized' not in st.session_state:
    try:
        # Ajuste o caminho conforme seu Instant Client local
        oracledb.init_oracle_client(lib_dir=r"C:\oracle\instantclient_19_29")
        st.session_state['oracle_client_initialized'] = True
    except Exception as e:
        st.error(f"Erro Client: {e}")

@st.cache_data(ttl=600)
def carregar_dados():
    conn_params = {"user": "NUTRICAO", "password": "nutr1125mmf", "dsn": "192.168.222.20:1521/WINT"}
    try:
        conn = oracledb.connect(**conn_params)
        # SQL trazendo estoque, custos e histórico de 4 meses
        query = """SELECT CODPROD, QTESTGER, QTRESERV, QTBLOQUEADA, QTVENDMES, 
                          QTVENDMES1, QTVENDMES2, QTVENDMES3, CUSTOREAL 
                   FROM MMFRIOS.PCEST WHERE CODFILIAL = 3 AND QTESTGER > 0"""
        df = pd.read_sql(query, conn)
        conn.close()
        
        # Cruzamento com sua base Excel de descrições
        df_nomes = pd.read_excel("BASE_DESCRICOES_PRODUTOS.xlsx")
        df_nomes.columns = ['Código', 'Descrição']
        df_final = pd.merge(df, df_nomes, left_on="CODPROD", right_on="Código", how="inner")
        
        # Cálculos de estoque e financeiro
        df_final['Disponível'] = df_final['QTESTGER'] - df_final['QTRESERV'] - df_final['QTBLOQUEADA']
        df_final['Valor em Estoque'] = df_final['QTESTGER'] * df_final['CUSTOREAL']
        
        return df_final
    except Exception as e:
        st.error(f"Erro ao conectar no banco: {e}")
        return None

# 2. INTERFACE ESTOQUE SERIDOENSE
st.set_page_config(page_title="Estoque Seridoense", layout="wide")
st.title("📦 Estoque Seridoense - Setor Fiscal")

df = carregar_dados()

if df is not None:
    # FILTROS NA LATERAL
    st.sidebar.header("Filtros de Análise")
    filtro_nome = st.sidebar.multiselect("Pesquisar Cortes:", options=sorted(df['Descrição'].unique()))
    
    df_filtrado = df.copy()
    if filtro_nome:
        df_filtrado = df_filtrado[df_filtrado['Descrição'].isin(filtro_nome)]

    # --- MUDANÇA 1: GRÁFICO TOP 20 HORIZONTAL ---
    st.subheader("🥩 Top 20 - Volume Físico em Estoque (kg)")
    df_top20 = df.nlargest(20, 'QTESTGER').sort_values('QTESTGER', ascending=True)
    
    # Criando o gráfico horizontal (orientation='h') com números visíveis
    fig_estoque = px.bar(df_top20, 
                         x='QTESTGER', 
                         y='Descrição', 
                         orientation='h',
                         color='QTESTGER', 
                         color_continuous_scale='Greens',
                         text_auto='.2f', # Exibe os números com 2 casas decimais
                         labels={'QTESTGER': 'Estoque (kg)', 'Descrição': 'Produto'})
    
    # Ajuste para os números ficarem fora da barra se ela for muito curta
    fig_estoque.update_traces(textposition='outside')
    fig_estoque.update_layout(height=600, showlegend=False)
    st.plotly_chart(fig_estoque, use_container_width=True)

    st.markdown("---")

    # --- MUDANÇA 2: ANÁLISE DE PERFORMANCE E HISTÓRICO ---
    col1, col2 = st.columns([1.2, 0.8])
    
    with col1:
        st.subheader("🏆 Histórico de Vendas")
        modo_venda = st.radio("Selecione o modo:", ["Mês Atual", "Comparativo 4 Meses"], horizontal=True)
        
        if modo_venda == "Mês Atual":
            df_v = df_filtrado.nlargest(15, 'QTVENDMES')
            fig_v = px.bar(df_v, x='QTVENDMES', y='Descrição', orientation='h', 
                           color='QTVENDMES', color_continuous_scale='Blues', text_auto='.1f')
        else:
            # Gráfico de comparação entre os meses
            df_v = df_filtrado.nlargest(10, 'QTVENDMES')
            fig_v = go.Figure()
            meses_labels = [('QTVENDMES', 'Atual'), ('QTVENDMES1', 'Mês -1'), 
                            ('QTVENDMES2', 'Mês -2'), ('QTVENDMES3', 'Mês -3')]
            for col_v, label_v in meses_labels:
                fig_v.add_trace(go.Bar(name=label_v, y=df_v['Descrição'], x=df_v[col_v], orientation='h'))
            fig_v.update_layout(barmode='group', title="Evolução das Vendas (kg)")
        
        st.plotly_chart(fig_v, use_container_width=True)

    # --- MUDANÇA 3: PARETO POR VALOR FINANCEIRO (R$) ---
    with col2:
        st.subheader("💰 Pareto: Valor Financeiro")
        df_pareto = df.sort_values("Valor em Estoque", ascending=False).copy()
        df_pareto['% Acumulado'] = (df_pareto['Valor em Estoque'] / df_pareto['Valor em Estoque'].sum() * 100).cumsum()
        
        fig_p = go.Figure()
        # Barras representando o valor total em estoque
        fig_p.add_trace(go.Bar(x=df_pareto['Descrição'][:12], y=df_pareto['Valor em Estoque'][:12], 
                               name="Valor R$", marker_color='gold'))
        # Linha da Curva de Pareto
        fig_p.add_trace(go.Scatter(x=df_pareto['Descrição'][:12], y=df_pareto['% Acumulado'][:12], 
                                   name="% Acumulado", yaxis="y2", line=dict(color="red", width=3)))
        
        fig_p.update_layout(title="Impacto Financeiro por Produto",
                            yaxis2=dict(title="% Acumulado", overlaying="y", side="right", range=[0, 105]))
        st.plotly_chart(fig_p, use_container_width=True)

    # DETALHAMENTO GERAL - TABELA FINAL
    st.subheader("📋 Tabela de Dados (Setor Fiscal)")
    # Reordenando para o formato solicitado: Estoque, Reservado, Disponível, Custo, Vendas...
    cols_tabela = ['Código', 'Descrição', 'QTESTGER', 'QTRESERV', 'Disponível', 
                   'CUSTOREAL', 'Valor em Estoque', 'QTVENDMES', 'QTVENDMES1']
    st.dataframe(df_filtrado[cols_tabela], use_container_width=True, hide_index=True)

    st.info(f"Dashboard rodando no endereço Network: http://192.168.1.19:8502")