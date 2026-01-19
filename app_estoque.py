import streamlit as st
import oracledb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

# 1. CONFIGURAÇÃO AMBIENTE (WinThor)
if 'oracle_client_initialized' not in st.session_state:
    try:
        # Ajuste o caminho do client de acordo com sua instalação
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
        
        # Carregando descrições do arquivo Excel
        df_nomes = pd.read_excel("BASE_DESCRICOES_PRODUTOS.xlsx")
        df_nomes.columns = ['Código', 'Descrição']
        df_final = pd.merge(df, df_nomes, left_on="CODPROD", right_on="Código", how="inner")
        
        # Cálculos de estoque
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
        m = hoje.month - i
        y = hoje.year
        while m <= 0: m += 12; y -= 1
        nome = f"{meses_pt[m]}/{str(y)[2:]}"
        lista_meses.append(nome)
    return lista_meses

def formatar_br(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# 2. INTERFACE
st.set_page_config(page_title="Dashboard Estoque - Seridoense", layout="wide")

# Cabeçalho: Logo ao lado do Título
col_logo, col_titulo = st.columns([1, 5])
with col_logo:
    nome_arquivo_logo = "MARCA-SERIDOENSE_.png" 
    if os.path.exists(nome_arquivo_logo):
        st.image(nome_arquivo_logo, width=150)
    else:
        st.info("Logo Seridoense")

with col_titulo:
    st.title("Dashboard Estoque - Seridoense")
    st.markdown("*Desenvolvido por: **Paulo Henrique**, Setor Fiscal*")

st.markdown("---")

df = carregar_dados()

if df is not None:
    # --- BLOCO 1: KPI CARDS ---
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

    # --- BLOCO 2: RENDIMENTO E SIMULADOR DE DESOSSA ---
    st.subheader("🥩 Rendimento e Simulação de Recebimento")
    
    dados_rendimento = {
        "Corte": [
            "OSSO BOV KG PROD", "COXAO MOLE BOV KG PROD", "CONTRAFILE BOV KG PROD", "COXAO DURO BOV KG PROD", "CARNE BOV PROD (LIMPEZA)", "PATINHO BOV KG PROD", "MUSCULO TRASEIRO BOV KG PROD", "CORACAO ALCATRA BOV KG PROD", "CAPA CONTRA FILE BOV KG PROD", "LOMBO PAULISTA BOV KG PROD", "OSSO BOV SERRA KG PROD", "FRALDA BOV KG PROD", "FILE MIGNON BOV PROD PÇ±1.6 KG", "MAMINHA BOV KG PROD", "PICANHA BOV KG PROD", "COSTELINHA CONTRA FILE KG PROD", "SEBO BOV KG PROD", "OSSO PATINHO BOV KG PROD", "ARANHA BOV KG PROD", "FILEZINHO MOCOTO KG PROD"
        ],
        "Rendimento (%)": [14.56, 13.40, 10.74, 9.32, 8.04, 7.88, 6.68, 5.42, 3.64, 3.60, 3.07, 2.65, 2.37, 2.27, 1.71, 1.69, 1.38, 0.76, 0.63, 0.18]
    }
    df_rend = pd.DataFrame(dados_rendimento)

    # Organização em abas para economizar espaço vertical
    tab_rend, tab_sim = st.tabs(["📊 Gráfico de Rendimento", "🧮 Simulador de Carga"])

    with tab_rend:
        col_r1, col_r2 = st.columns([2, 1])
        with col_r1:
            fig_rend = px.bar(
                df_rend.sort_values("Rendimento (%)", ascending=True),
                x="Rendimento (%)", y="Corte",
                orientation='h',
                color="Rendimento (%)",
                color_continuous_scale='Reds',
                text_auto='.2f'
            )
            fig_rend.update_layout(height=450, margin=dict(t=20, b=20), coloraxis_showscale=False)
            st.plotly_chart(fig_rend, use_container_width=True)
        with col_r2:
            st.dataframe(
                df_rend.sort_values("Rendimento (%)", ascending=False),
                use_container_width=True, hide_index=True,
                column_config={"Rendimento (%)": st.column_config.NumberColumn(format="%.2f%%")}
            )

    with tab_sim:
        st.markdown("#### Simular Cortes por Carga Recebida")
        # Campo digitável para simulação
        peso_entrada = st.number_input("Informe o peso total de entrada (Kg):", min_value=0.0, value=16000.0, step=500.0)
        
        if peso_entrada > 0:
            df_sim = df_rend.copy()
            df_sim['Previsão (Kg)'] = (df_sim['Rendimento (%)'] / 100) * peso_entrada
            
            st.write(f"**Estimativa de desossa para {formatar_br(peso_entrada)} Kg:**")
            st.dataframe(
                df_sim.sort_values('Previsão (Kg)', ascending=False),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Rendimento (%)": st.column_config.NumberColumn(format="%.2f%%"),
                    "Previsão (Kg)": st.column_config.NumberColumn(format="%.2f Kg")
                }
            )
            total_calc = df_sim['Previsão (Kg)'].sum()
            st.success(f"Volume Total Estimado: {formatar_br(total_calc)} Kg")

    st.markdown("---")

    # --- BLOCO 3: GRÁFICO DE ESTOQUE (Altura 550) ---
    st.subheader("🥩 Top 20 - Volume Físico em Estoque (kg)")
    df_top20 = df.nlargest(20, 'QTESTGER').sort_values('QTESTGER', ascending=True)
    
    fig_estoque = px.bar(df_top20, x='QTESTGER', y='Descrição', orientation='h',
                         color='QTESTGER', color_continuous_scale='Greens',
                         text_auto='.2f')
    
    fig_estoque.update_traces(
        textposition='outside',
        textfont=dict(size=14, color='black', family="Arial Black")
    )
    
    fig_estoque.update_layout(
        height=550, 
        margin=dict(l=50, r=120, t=50, b=50),
        xaxis_title="Quantidade em Estoque (Kg)",
        yaxis_title="",
        coloraxis_showscale=False
    )
    st.plotly_chart(fig_estoque, use_container_width=True)

    st.markdown("---")

    # --- BLOCO 4: ANÁLISE DE VENDAS ---
    st.subheader("🏆 Análise de vendas (KG)")
    nomes_meses = obter_nomes_meses()
    col_grafico, col_filtros = st.columns([4, 1])
    
    with col_filtros:
        st.markdown("#### 🔍 Filtros")
        modo_venda = st.radio("Período:", ["Mês Atual", "Comparativo 4 Meses"])
        filtro_venda = st.multiselect("Pesquisar Cortes:", options=sorted(df['Descrição'].unique()))
    
    df_vendas_grafico = df.copy()
    if filtro_venda:
        df_vendas_grafico = df_vendas_grafico[df_vendas_grafico['Descrição'].isin(filtro_venda)]
    
    with col_grafico:
        if modo_venda == "Mês Atual":
            df_v = df_vendas_grafico.nlargest(15, 'QTVENDMES')
            fig_v = px.bar(df_v, x='QTVENDMES', y='Descrição', orientation='h', 
                           color='QTVENDMES', color_continuous_scale='Blues',
                           text_auto='.1f')
        else:
            df_v = df_vendas_grafico.nlargest(12, 'QTVENDMES')
            fig_v = go.Figure()
            for col_db, nome_label in [('QTVENDMES', nomes_meses[0]), ('QTVENDMES1', nomes_meses[1]),
                                       ('QTVENDMES2', nomes_meses[2]), ('QTVENDMES3', nomes_meses[3])]:
                fig_v.add_trace(go.Bar(name=nome_label, y=df_v['Descrição'], x=df_v[col_db], orientation='h'))
            fig_v.update_layout(barmode='group', height=500)
        st.plotly_chart(fig_v, use_container_width=True)

    st.markdown("---")

    # --- BLOCO 5: PARETO FINANCEIRO ---
    st.subheader("💰 Pareto: Valor do Estoque Atual (R$)")
    df_pareto = df.sort_values("Valor em Estoque", ascending=False).copy()
    df_pareto['% Acc'] = (df_pareto['Valor em Estoque'] / df_pareto['Valor em Estoque'].sum() * 100).cumsum()
    
    fig_p = go.Figure()
    fig_p.add_trace(go.Bar(x=df_pareto['Descrição'][:10], y=df_pareto['Valor em Estoque'][:10], name="Valor R$", marker_color='gold'))
    fig_p.add_trace(go.Scatter(x=df_pareto['Descrição'][:10], y=df_pareto['% Acc'][:10], name="% Acumulado", yaxis="y2", line=dict(color="red")))
    fig_p.update_layout(yaxis2=dict(overlaying="y", side="right", range=[0, 105]), height=400)
    st.plotly_chart(fig_p, use_container_width=True)

    # --- BLOCO 6: TABELA DE DETALHAMENTO ---
    st.subheader("📋 Detalhamento Geral")
    st.dataframe(
        df[['Código', 'Descrição', 'QTESTGER', 'Disponível', 'CUSTOREAL', 'Valor em Estoque', 'QTVENDMES']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "QTESTGER": st.column_config.NumberColumn("Estoque (Kg)", format="%.2f"),
            "CUSTOREAL": st.column_config.NumberColumn("Custo (R$)", format="R$ %.2f"),
            "Valor em Estoque": st.column_config.NumberColumn("Total (R$)", format="R$ %.2f")
        }
    )

    st.info(f"Dashboard ativo na rede interna: http://192.168.1.19:8502")