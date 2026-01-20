import streamlit as st
import oracledb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

# --- 1. CONFIGURAÇÃO AMBIENTE (WinThor) ---
if 'oracle_client_initialized' not in st.session_state:
    try:
        oracledb.init_oracle_client(lib_dir=r"C:\oracle\instantclient_19_29")
        st.session_state['oracle_client_initialized'] = True
    except Exception as e:
        st.error(f"Erro Client Oracle: {e}")

# --- 2. FUNÇÕES DE APOIO ---
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

def salvar_dados_desossa(dados_dict):
    arquivo = "DESOSSA_HISTORICO.csv"
    df_novo = pd.DataFrame([dados_dict])
    if os.path.exists(arquivo):
        df_hist = pd.read_csv(arquivo)
        df_hist = pd.concat([df_hist, df_novo], ignore_index=True)
    else:
        df_hist = df_novo
    df_hist.to_csv(arquivo, index=False)
    st.success("✅ Lançamento de desossa salvo com sucesso!")

def formatar_br(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def obter_nomes_meses():
    meses_pt = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun", 
                7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}
    hoje = datetime.now()
    lista = []
    for i in range(4):
        m, y = hoje.month - i, hoje.year
        while m <= 0: m += 12; y -= 1
        lista.append(f"{meses_pt[m]}/{str(y)[2:]}")
    return lista

# --- 3. INTERFACE STREAMLIT ---
st.set_page_config(page_title="Dashboard Seridoense", layout="wide")

col_logo, col_tit = st.columns([1, 5])
with col_logo:
    if os.path.exists("MARCA-SERIDOENSE_.png"):
        st.image("MARCA-SERIDOENSE_.png", width=140)
with col_tit:
    st.title("Sistema de Inteligência de Estoque e Desossa")
    st.markdown("*Desenvolvido por: **Paulo Henrique**, Setor Fiscal*")

df = carregar_dados()

if df is not None:
    # --- KPIs ---
    t_kg = df['QTESTGER'].sum()
    t_val = df['Valor em Estoque'].sum()
    col_k1, col_k2, col_k3 = st.columns(3)
    col_k1.metric("Estoque Total (Kg)", f"{formatar_br(t_kg)} Kg")
    col_k2.metric("Valor Imobilizado", f"R$ {formatar_br(t_val)}")
    col_k3.metric(f"Venda {obter_nomes_meses()[0]}", f"{formatar_br(df['QTVENDMES'].sum())} Kg")

    st.markdown("---")

    # --- BLOCO 2: RENDIMENTO E ABAS ---
    st.subheader("🥩 Rendimento e Simulação de Recebimento")
    tab_rend, tab_sim, tab_lancto = st.tabs(["📊 Gráfico de Rendimento", "🧮 Simulador de Carga", "📝 Registro Real Diário"])

    with tab_rend:
        dados_rendimento = {
            "Corte": ["OSSO BOV KG PROD", "COXAO MOLE BOV KG PROD", "CONTRAFILE BOV KG PROD", "COXAO DURO BOV KG PROD", "CARNE BOV PROD (LIMPEZA)", "PATINHO BOV KG PROD", "MUSCULO TRASEIRO BOV KG PROD", "CORACAO ALCATRA BOV KG PROD", "CAPA CONTRA FILE BOV KG PROD", "LOMBO PAULISTA BOV KG PROD", "OSSO BOV SERRA KG PROD", "FRALDA BOV KG PROD", "FILE MIGNON BOV PROD PÇ±1.6 KG", "MAMINHA BOV KG PROD", "PICANHA BOV KG PROD", "COSTELINHA CONTRA FILE KG PROD", "SEBO BOV KG PROD", "OSSO PATINHO BOV KG PROD", "ARANHA BOV KG PROD", "FILEZINHO MOCOTO KG PROD"],
            "Rendimento (%)": [14.56, 13.4, 10.74, 9.32, 8.04, 7.88, 6.68, 5.42, 3.64, 3.60, 3.07, 2.65, 2.37, 2.27, 1.71, 1.69, 1.38, 0.76, 0.63, 0.18]
        }
        df_rend = pd.DataFrame(dados_rendimento)
        col_r1, col_r2 = st.columns([2, 1])
        with col_r1:
            fig_rend = px.bar(df_rend.sort_values("Rendimento (%)", ascending=True), x="Rendimento (%)", y="Corte", orientation='h', color="Rendimento (%)", color_continuous_scale='Reds', text_auto='.2f')
            fig_rend.update_layout(height=450, coloraxis_showscale=False, margin=dict(t=20, b=20))
            st.plotly_chart(fig_rend, use_container_width=True)
        with col_r2:
            st.dataframe(df_rend.sort_values("Rendimento (%)", ascending=False), use_container_width=True, hide_index=True)

    with tab_sim:
        p_entrada = st.number_input("Informe o peso total de entrada (Kg):", min_value=0.0, value=25000.0)
        df_sim = df_rend.copy()
        df_sim['Previsão (Kg)'] = (df_sim['Rendimento (%)'] / 100) * p_entrada
        st.dataframe(df_sim.sort_values('Previsão (Kg)', ascending=False), use_container_width=True, hide_index=True, column_config={"Previsão (Kg)": st.column_config.NumberColumn(format="%.2f Kg")})
        st.success(f"Volume Total Estimado: {formatar_br(df_sim['Previsão (Kg)'].sum())} Kg")

    with tab_lancto:
        with st.form("registro_diario"):
            c1, c2, c3 = st.columns(3)
            f_data = c1.date_input("Data", datetime.now())
            f_forn = c2.selectbox("Fornecedor", ["JBS", "RIO MARIA", "BOI BRANCO S.A", "OUTROS"])
            f_peso = c3.number_input("Peso Carcaça (Kg)", min_value=0.0)
            st.markdown("**Pesos Reais por Corte (Kg):**")
            cortes_completos = ["ARANHA", "CAPA CONTRA FILE", "CHAMBARIL TRASEIRO", "CONTRAFILE", "CORACAO ALCATRA", "COXAO DURO", "COXAO MOLE", "FILE MIGNON", "FRALDA", "LOMBO PAULISTA/LAGARTO", "MAMINHA", "MUSCULO TRASEIRO", "PATINHO", "PICANHA", "CARNE BOVINA (LIMPEZA)", "COSTELINHA CONTRA", "OSSO (Descarte)", "OSSO SERRA", "OSSO PATINHO", "SEBO", "ROJAO DA CAPA", "FILEZINHO DE MOCOTÓ"]
            res_valores = {"DATA": f_data, "FORNECEDOR": f_forn, "ENTRADA": f_peso}
            cols_form = st.columns(2)
            for i, corte in enumerate(cortes_completos):
                with (cols_form[0] if i % 2 == 0 else cols_form[1]):
                    res_valores[corte] = st.number_input(f"{corte}", min_value=0.0, key=f"real_{corte}")
            if st.form_submit_button("💾 Salvar Registro Diário"):
                if f_peso > 0: salvar_dados_desossa(res_valores)
                else: st.error("Peso de entrada obrigatório.")

    st.markdown("---")

    # --- BLOCO 3: GRÁFICO DE ESTOQUE (AUMENTADO) ---
    st.subheader("🥩 Top 20 - Volume Físico em Estoque (kg)")
    df_top20 = df.nlargest(20, 'QTESTGER').sort_values('QTESTGER', ascending=True)
    fig_est = px.bar(df_top20, x='QTESTGER', y='Descrição', orientation='h', color='QTESTGER', color_continuous_scale='Greens', text_auto='.2f')
    
    # Aumentando a altura e as margens para visualização clara
    fig_est.update_layout(
        height=700, 
        margin=dict(l=50, r=100, t=20, b=20),
        coloraxis_showscale=False,
        xaxis_title="Quantidade em Estoque (Kg)",
        yaxis_title=""
    )
    fig_est.update_traces(textposition='outside', textfont=dict(size=12, family="Arial Black"))
    st.plotly_chart(fig_est, use_container_width=True)

    st.markdown("---")

    # --- BLOCO 4: ANÁLISE DE VENDAS (RESTAURADO COM FILTROS) ---
    st.subheader("🏆 Análise de Vendas (KG)")
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
            fig_v = px.bar(df_v, x='QTVENDMES', y='Descrição', orientation='h', color='QTVENDMES', color_continuous_scale='Blues', text_auto='.1f')
            fig_v.update_layout(height=500)
        else:
            df_v = df_vendas_grafico.nlargest(12, 'QTVENDMES')
            fig_v = go.Figure()
            for i, (col_db, nome_label) in enumerate([('QTVENDMES', nomes_meses[0]), ('QTVENDMES1', nomes_meses[1]), ('QTVENDMES2', nomes_meses[2]), ('QTVENDMES3', nomes_meses[3])]):
                fig_v.add_trace(go.Bar(name=nome_label, y=df_v['Descrição'], x=df_v[col_db], orientation='h'))
            fig_v.update_layout(barmode='group', height=600, margin=dict(t=20, b=20))
        st.plotly_chart(fig_v, use_container_width=True)

    st.markdown("---")

    # --- BLOCO 5: PARETO ---
    st.subheader("💰 Pareto: Valor do Estoque Atual (R$)")
    df_p = df.sort_values("Valor em Estoque", ascending=False).copy()
    df_p['% Acc'] = (df_p['Valor em Estoque'] / df_p['Valor em Estoque'].sum() * 100).cumsum()
    fig_p = go.Figure()
    fig_p.add_trace(go.Bar(x=df_p['Descrição'][:10], y=df_p['Valor em Estoque'][:10], name="Valor R$", marker_color='gold'))
    fig_p.add_trace(go.Scatter(x=df_p['Descrição'][:10], y=df_p['% Acc'][:10], name="% Acumulado", yaxis="y2", line=dict(color="red")))
    fig_p.update_layout(yaxis2=dict(overlaying="y", side="right", range=[0, 105]), height=450)
    st.plotly_chart(fig_p, use_container_width=True)

    # --- BLOCO 6: DETALHAMENTO ---
    st.subheader("📋 Detalhamento Geral de Estoque")
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