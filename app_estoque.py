import streamlit as st
import oracledb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. CONFIGURAÇÃO AMBIENTE (WinThor)
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
        # Ajuste dinâmico dos meses
        m = hoje.month - i
        y = hoje.year
        while m <= 0: m += 12; y -= 1
        nome = f"{meses_pt[m]}/{str(y)[2:]}"
        lista_meses.append(nome)
    return lista_meses

# Função para formatar números no padrão PT-BR (1.234,56)
def formatar_br(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# 2. INTERFACE
st.set_page_config(page_title="Dashboard Estoque - Seridoense", layout="wide")

# Título e Assinatura
st.title("📊 Dashboard Estoque - Seridoense")
st.markdown("*Desenvolvido por: **Paulo Henrique**, Setor Fiscal*")
st.markdown("---")

df = carregar_dados()

if df is not None:
    # --- KPI CARDS COM FORMATAÇÃO BRASILEIRA ---
    total_kg = df['QTESTGER'].sum()
    total_valor = df['Valor em Estoque'].sum()
    total_venda_mes = df['QTVENDMES'].sum()
    
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    with col_kpi1:
        st.metric("Total de Estoque (Kg)", f"{formatar_br(total_kg)} Kg")
    with col_kpi2:
        st.metric("Valor Total Imobilizado", f"R$ {formatar_br(total_valor)}")
    with col_kpi3:
        st.metric(f"Venda Total {obter_nomes_meses()[0]}", f"{formatar_br(total_venda_mes)} Kg")
    
    st.markdown("---")

    # --- GRÁFICO 1: VOLUME EM ESTOQUE ---
    st.subheader("🥩 Top 20 - Volume Físico em Estoque (kg)")
    df_top20 = df.nlargest(20, 'QTESTGER').sort_values('QTESTGER', ascending=True)
    fig_estoque = px.bar(df_top20, x='QTESTGER', y='Descrição', orientation='h',
                         color='QTESTGER', color_continuous_scale='Greens',
                         text_auto='.2f')
    fig_estoque.update_traces(textposition='outside')
    st.plotly_chart(fig_estoque, use_container_width=True)

    st.markdown("---")

    # --- GRÁFICO 2: ANÁLISE DE VENDAS (KG) - FILTRO ISOLADO ---
    st.subheader("🏆 Análise de vendas (KG)")
    nomes_meses = obter_nomes_meses()
    col_grafico, col_filtros = st.columns([4, 1])
    
    with col_filtros:
        st.markdown("#### 🔍 Filtros do Gráfico")
        modo_venda = st.radio("Período:", ["Mês Atual", "Comparativo 4 Meses"])
        # Filtro que afeta apenas o gráfico abaixo
        filtro_venda = st.multiselect("Pesquisar Cortes no Gráfico:", options=sorted(df['Descrição'].unique()))
    
    df_vendas_grafico = df.copy()
    if filtro_venda:
        df_vendas_grafico = df_vendas_grafico[df_vendas_grafico['Descrição'].isin(filtro_venda)]
    
    with col_grafico:
        if modo_venda == "Mês Atual":
            df_v = df_vendas_grafico.nlargest(15, 'QTVENDMES')
            fig_v = px.bar(df_v, x='QTVENDMES', y='Descrição', orientation='h', 
                           color='QTVENDMES', color_continuous_scale='Blues',
                           text_auto='.1f', title=f"Vendas (kg) - {nomes_meses[0]}")
        else:
            df_v = df_vendas_grafico.nlargest(12, 'QTVENDMES')
            fig_v = go.Figure()
            meses_config = [('QTVENDMES', nomes_meses[0]), ('QTVENDMES1', nomes_meses[1]),
                            ('QTVENDMES2', nomes_meses[2]), ('QTVENDMES3', nomes_meses[3])]
            for col_db, nome_label in meses_config:
                fig_v.add_trace(go.Bar(name=nome_label, y=df_v['Descrição'], x=df_v[col_db], orientation='h'))
            fig_v.update_layout(barmode='group', title="Evolução de Vendas (kg)", height=600)
        st.plotly_chart(fig_v, use_container_width=True)

    st.markdown("---")

    # --- GRÁFICO 3: PARETO FINANCEIRO ---
    col_p, _ = st.columns([2, 1])
    with col_p:
        st.subheader("💰 Pareto: Valor do Estoque Atual (R$)") #
        df_pareto = df.sort_values("Valor em Estoque", ascending=False).copy()
        df_pareto['% Acc'] = (df_pareto['Valor em Estoque'] / df_pareto['Valor em Estoque'].sum() * 100).cumsum()
        fig_p = go.Figure()
        fig_p.add_trace(go.Bar(x=df_pareto['Descrição'][:10], y=df_pareto['Valor em Estoque'][:10], name="Valor R$", marker_color='gold'))
        fig_p.add_trace(go.Scatter(x=df_pareto['Descrição'][:10], y=df_pareto['% Acc'][:10], name="% Acumulado", yaxis="y2", line=dict(color="red")))
        fig_p.update_layout(yaxis2=dict(overlaying="y", side="right", range=[0, 105]), height=400, yaxis_tickprefix='R$ ')
        st.plotly_chart(fig_p, use_container_width=True)

    # --- TABELA FINAL: DETALHAMENTO GERAL (COMPLETA) ---
    st.subheader("📋 Detalhamento Geral") #
    st.dataframe(
        df[['Código', 'Descrição', 'QTESTGER', 'Disponível', 'CUSTOREAL', 'Valor em Estoque', 'QTVENDMES']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "QTESTGER": st.column_config.NumberColumn("Estoque geral", format="%.2f Kg"),
            "Disponível": st.column_config.NumberColumn("Disponível", format="%.2f Kg"),
            "CUSTOREAL": st.column_config.NumberColumn("Custo Real (R$)", format="R$ %.2f"),
            "Valor em Estoque": st.column_config.NumberColumn("Valor em Estoque", format="R$ %.2f"),
            "QTVENDMES": st.column_config.NumberColumn("Venda Mês Atual (kg)", format="%.2f Kg")
        }
    )

    st.info(f"Dashboard ativo na rede interna: http://192.168.1.19:8502")