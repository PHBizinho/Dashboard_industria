import streamlit as st
import oracledb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
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
    st.toast(f"✅ Desossa NF {dados_dict['NF']} salva com sucesso!", icon='🥩')

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

# --- 3. INTERFACE ---
st.set_page_config(page_title="Dashboard Seridoense", layout="wide")

col_logo, col_tit = st.columns([1, 5])
with col_logo:
    if os.path.exists("MARCA-SERIDOENSE_.png"):
        st.image("MARCA-SERIDOENSE_.png", width=140)
with col_tit:
    st.title("Sistema de Inteligência de Estoque e Desossa")
    st.markdown("*Responsável: **Paulo Henrique**, Setor Fiscal*")

df = carregar_dados()

if df is not None:
    # --- KPIs ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Estoque Total (Kg)", f"{formatar_br(df['QTESTGER'].sum())} Kg")
    c2.metric("Valor Imobilizado", f"R$ {formatar_br(df['Valor em Estoque'].sum())}")
    c3.metric(f"Venda {obter_nomes_meses()[0]}", f"{formatar_br(df['QTVENDMES'].sum())} Kg")

    st.markdown("---")

    # --- BLOCO RENDIMENTO E DESOSSA ---
    st.subheader("🥩 Rendimento e Simulação de Recebimento")
    tab_rend, tab_sim, tab_lancto, tab_consulta = st.tabs([
        "📊 Gráfico de Rendimento", 
        "🧮 Simulador de Carga", 
        "📝 Registro Real Diário",
        "🔍 Histórico e Consulta"
    ])

    with tab_rend:
        dados_rend = {
            "Corte": ["OSSO BOV KG PROD", "COXAO MOLE BOV KG PROD", "CONTRAFILE BOV KG PROD", "COXAO DURO BOV KG PROD", "CARNE BOV PROD (LIMPEZA)", "PATINHO BOV KG PROD", "MUSCULO TRASEIRO BOV KG PROD", "CORACAO ALCATRA BOV KG PROD", "CAPA CONTRA FILE BOV KG PROD", "LOMBO PAULISTA BOV KG PROD", "OSSO BOV SERRA KG PROD", "FRALDA BOV KG PROD", "FILE MIGNON BOV PROD PÇ±1.6 KG", "MAMINHA BOV KG PROD", "PICANHA BOV KG PROD", "COSTELINHA CONTRA FILE KG PROD", "SEBO BOV KG PROD", "OSSO PATINHO BOV KG PROD", "ARANHA BOV KG PROD", "FILEZINHO MOCOTO KG PROD"],
            "Rendimento (%)": [14.56, 13.4, 10.74, 9.32, 8.04, 7.88, 6.68, 5.42, 3.64, 3.60, 3.07, 2.65, 2.37, 2.27, 1.71, 1.69, 1.38, 0.76, 0.63, 0.18]
        }
        df_rend = pd.DataFrame(dados_rend)
        fig_r = px.bar(df_rend.sort_values("Rendimento (%)", ascending=True), x="Rendimento (%)", y="Corte", orientation='h', color="Rendimento (%)", color_continuous_scale='Reds', text_auto='.2f')
        st.plotly_chart(fig_r, use_container_width=True)

    with tab_sim:
        p_entrada = st.number_input("Informe o peso para simular (Kg):", min_value=0.0, value=25000.0)
        df_sim = df_rend.copy()
        df_sim['Previsão (Kg)'] = (df_sim['Rendimento (%)'] / 100) * p_entrada
        st.dataframe(df_sim.sort_values('Previsão (Kg)', ascending=False), use_container_width=True, hide_index=True)
        
        total_simulado = df_sim['Previsão (Kg)'].sum()
        st.info(f"Total Geral Estimado: {formatar_br(total_simulado)} Kg")

    with tab_lancto:
        with st.form("form_desossa", clear_on_submit=True):
            f1, f2, f3, f4, f5 = st.columns(5)
            f_data = f1.date_input("Data", datetime.now())
            f_nf = f2.text_input("Nº Nota Fiscal")
            f_forn = f3.selectbox("Fornecedor", ["JBS", "RIO MARIA", "BOI BRANCO S.A", "OUTROS"])
            f_pecas = f4.number_input("Qtd Peças", min_value=0)
            f_peso = f5.number_input("Peso total desossado", min_value=0.0)
            
            cortes_lista = ["ARANHA", "CAPA CONTRA FILE", "CHAMBARIL TRASEIRO", "CONTRAFILE", "CORACAO ALCATRA", "COXAO DURO", "COXAO MOLE", "FILE MIGNON", "FRALDA", "LOMBO PAULISTA/LAGARTO", "MAMINHA", "MUSCULO TRASEIRO", "PATINHO", "PICANHA", "CARNE BOVINA (LIMPEZA)", "COSTELINHA CONTRA", "OSSO (Descarte)", "OSSO SERRA", "OSSO PATINHO", "SEBO", "ROJAO DA CAPA", "FILEZINHO DE MOCOTÓ"]
            res_val = {"DATA": f_data, "NF": f_nf, "FORNECEDOR": f_forn, "PECAS": f_pecas, "ENTRADA": f_peso}
            
            c_form = st.columns(2)
            for i, corte in enumerate(cortes_lista):
                with (c_form[0] if i % 2 == 0 else c_form[1]):
                    res_val[corte] = st.number_input(f"{corte}", min_value=0.0, key=f"inp_{corte}")
            
            if st.form_submit_button("💾 Salvar Registro Diário"):
                if f_peso > 0 and f_nf:
                    salvar_dados_desossa(res_val)
                    st.rerun()
                else: st.error("Preencha a NF e o Peso Total.")

    with tab_consulta:
        if os.path.exists("DESOSSA_HISTORICO.csv"):
            df_h = pd.read_csv("DESOSSA_HISTORICO.csv")
            df_h['DATA'] = pd.to_datetime(df_h['DATA']).dt.date
            
            # --- FILTROS DE CONSULTA ---
            st.markdown("#### 🔍 Filtros de Busca")
            cf1, cf2, cf3 = st.columns([2, 1, 1])
            
            with cf1:
                periodo = st.date_input("Período:", [datetime.now() - timedelta(days=7), datetime.now()])
            with cf2:
                sel_nf = st.selectbox("Buscar NF:", ["Todas"] + sorted(df_h['NF'].astype(str).unique().tolist()))
            with cf3:
                sel_forn = st.selectbox("Fornecedor:", ["Todos"] + sorted(df_h['FORNECEDOR'].unique().tolist()))
            
            # Aplicar Filtros
            mask = (df_h['DATA'] >= periodo[0]) & (df_h['DATA'] <= periodo[1])
            df_f = df_h.loc[mask]
            if sel_nf != "Todas": df_f = df_f[df_f['NF'].astype(str) == sel_nf]
            if sel_forn != "Todos": df_f = df_f[df_f['FORNECEDOR'] == sel_forn]
            
            st.dataframe(df_f, use_container_width=True, hide_index=True)
            st.download_button("📥 Baixar Histórico", df_h.to_csv(index=False).encode('utf-8'), "historico_desossa.csv")
        else: st.info("Sem registros.")

    st.markdown("---")

    # --- ESTOQUE E VENDAS ---
    st.subheader("🥩 Top 20 - Volume Físico em Estoque (kg)")
    df_t20 = df.nlargest(20, 'QTESTGER').sort_values('QTESTGER', ascending=True)
    fig_est = px.bar(df_t20, x='QTESTGER', y='Descrição', orientation='h', color='QTESTGER', color_continuous_scale='Greens', text_auto='.2f')
    fig_est.update_layout(height=700)
    st.plotly_chart(fig_est, use_container_width=True)

    st.markdown("---")

    st.subheader("🏆 Análise de Vendas (KG)")
    col_g, col_f = st.columns([4, 1])
    with col_f:
        modo = st.radio("Visão:", ["Mês Atual", "Comparativo"])
        filtro = st.multiselect("Cortes:", sorted(df['Descrição'].unique()))
    
    df_v = df.copy()
    if filtro: df_v = df_v[df_v['Descrição'].isin(filtro)]
    
    with col_g:
        if modo == "Mês Atual":
            fig_v = px.bar(df_v.nlargest(15, 'QTVENDMES'), x='QTVENDMES', y='Descrição', orientation='h', color_continuous_scale='Blues', text_auto='.1f')
        else:
            fig_v = go.Figure()
            meses = obter_nomes_meses()
            for i, c_v in enumerate(['QTVENDMES', 'QTVENDMES1', 'QTVENDMES2', 'QTVENDMES3']):
                fig_v.add_trace(go.Bar(name=meses[i], y=df_v.nlargest(10, 'QTVENDMES')['Descrição'], x=df_v.nlargest(10, 'QTVENDMES')[c_v], orientation='h'))
            fig_v.update_layout(barmode='group', height=500)
        st.plotly_chart(fig_v, use_container_width=True)

    st.subheader("📋 Detalhamento Geral")
    st.dataframe(df[['Código', 'Descrição', 'QTESTGER', 'Disponível', 'CUSTOREAL', 'Valor em Estoque']], use_container_width=True, hide_index=True)

    st.info(f"Dashboard ativo na rede interna: http://192.168.1.19:8502")