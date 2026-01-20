import streamlit as st
import oracledb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
from fpdf import FPDF

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
    st.toast(f"✅ Desossa {dados_dict['TIPO']} NF {dados_dict['NF']} salva!", icon='🥩')

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

# --- FUNÇÃO PDF REVISADA (SEM NONE) ---
def gerar_pdf_bytes(df_selecionado):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    ignorar = ['DATA', 'NF', 'TIPO', 'FORNECEDOR', 'PECAS', 'ENTRADA']
    
    for _, row in df_selecionado.iterrows():
        pdf.add_page()
        if os.path.exists("MARCA-SERIDOENSE_.png"):
            pdf.image("MARCA-SERIDOENSE_.png", 10, 8, 33)
        
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "Relatorio de Desossa - Seridoense", ln=True, align="C")
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 10, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
        pdf.ln(10)
        
        pdf.set_fill_color(200, 0, 0); pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, f" DADOS DA CARGA - NF: {row['NF']}", 0, ln=True, fill=True)
        
        pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "B", 10); pdf.set_fill_color(245, 245, 245)
        pdf.cell(47, 8, f"Data: {row['DATA']}", 1, 0, 'L', True)
        pdf.cell(47, 8, f"Tipo: {row['TIPO']}", 1, 0, 'L', True)
        pdf.cell(47, 8, f"Pecas: {row['PECAS']}", 1, 0, 'L', True)
        pdf.cell(49, 8, f"Peso Total: {row['ENTRADA']} Kg", 1, 1, 'L', True)
        pdf.cell(0, 8, f"Fornecedor: {row['FORNECEDOR']}", 1, 1, 'L', True)
        pdf.ln(5)
        
        pdf.set_font("Arial", "B", 11); pdf.cell(0, 10, "DETALHAMENTO DA DESOSSA", 0, ln=True)
        pdf.set_fill_color(200, 200, 200)
        pdf.cell(140, 8, "Corte / Subproduto", 1, 0, 'L', True)
        pdf.cell(50, 8, "Peso (Kg)", 1, 1, 'C', True)
        
        pdf.set_font("Arial", "", 10); fill = False
        for col in row.index:
            if col not in ignorar and pd.to_numeric(row[col], errors='coerce') > 0:
                pdf.set_fill_color(245, 245, 245) if fill else pdf.set_fill_color(255, 255, 255)
                pdf.cell(140, 7, f" {col}", 1, 0, 'L', True); pdf.cell(50, 7, f"{float(row[col]):.2f}", 1, 1, 'C', True)
                fill = not fill
        
        pdf.ln(15); pdf.set_font("Arial", "I", 8)
        pdf.cell(0, 10, "______________________________________________________", ln=True, align="C")
        pdf.cell(0, 5, "Assinatura do Responsavel", ln=True, align="C")

    return bytes(pdf.output()) # Convertendo explicitamente para bytes

# --- 3. INTERFACE ---
st.set_page_config(page_title="Dashboard Seridoense", layout="wide")

col_logo, col_tit = st.columns([1, 5])
with col_logo:
    if os.path.exists("MARCA-SERIDOENSE_.png"):
        st.image("MARCA-SERIDOENSE_.png", width=140)
with col_tit:
    st.title("Sistema de Inteligência de Estoque e Desossa")
    st.markdown("*Responsável: **Paulo Henrique**, Setor Fiscal*")

df_estoque = carregar_dados()

if df_estoque is not None:
    # KPIs
    c1, c2, c3 = st.columns(3)
    c1.metric("Estoque Total (Kg)", f"{formatar_br(df_estoque['QTESTGER'].sum())} Kg")
    c2.metric("Valor Imobilizado", f"R$ {formatar_br(df_estoque['Valor em Estoque'].sum())}")
    c3.metric(f"Venda {obter_nomes_meses()[0]}", f"{formatar_br(df_estoque['QTVENDMES'].sum())} Kg")
    st.markdown("---")

    tab_rend, tab_sim, tab_lancto, tab_consulta = st.tabs([
        "📊 Gráfico de Rendimento", "🧮 Simulador de Carga", "📝 Registro Real Diário", "🔍 Histórico e Consulta"
    ])

    with tab_rend:
        dados_rend = {"Corte": ["OSSO BOV KG PROD", "COXAO MOLE BOV KG PROD", "CONTRAFILE BOV KG PROD", "COXAO DURO BOV KG PROD", "CARNE BOV PROD (LIMPEZA)", "PATINHO BOV KG PROD", "MUSCULO TRASEIRO BOV KG PROD", "CORACAO ALCATRA BOV KG PROD", "CAPA CONTRA FILE BOV KG PROD", "LOMBO PAULISTA BOV KG PROD", "OSSO BOV SERRA KG PROD", "FRALDA BOV KG PROD", "FILE MIGNON BOV PROD PÇ±1.6 KG", "MAMINHA BOV KG PROD", "PICANHA BOV KG PROD", "COSTELINHA CONTRA FILE KG PROD", "SEBO BOV KG PROD", "OSSO PATINHO BOV KG PROD", "ARANHA BOV KG PROD", "FILEZINHO MOCOTO KG PROD"], "Rendimento (%)": [14.56, 13.4, 10.74, 9.32, 8.04, 7.88, 6.68, 5.42, 3.64, 3.60, 3.07, 2.65, 2.37, 2.27, 1.71, 1.69, 1.38, 0.76, 0.63, 0.18]}
        df_rend = pd.DataFrame(dados_rend)
        fig_r = px.bar(df_rend.sort_values("Rendimento (%)", ascending=True), x="Rendimento (%)", y="Corte", orientation='h', color="Rendimento (%)", color_continuous_scale='Reds', text_auto='.2f')
        st.plotly_chart(fig_r, use_container_width=True)

    with tab_sim:
        p_entrada = st.number_input("Peso para simular (Kg):", min_value=0.0, value=25000.0)
        df_sim = df_rend.copy()
        df_sim['Previsão (Kg)'] = (df_sim['Rendimento (%)'] / 100) * p_entrada
        st.dataframe(df_sim.sort_values('Previsão (Kg)', ascending=False), use_container_width=True, hide_index=True)
        st.info(f"**Total Geral Estimado: {formatar_br(df_sim['Previsão (Kg)'].sum())} Kg**")

    with tab_lancto:
        with st.form("form_desossa", clear_on_submit=True):
            f1, f2, f3, f4, f5, f6 = st.columns(6)
            f_data = f1.date_input("Data", datetime.now())
            f_nf = f2.text_input("Nº NF")
            f_tipo = f3.selectbox("Tipo", ["Boi", "Vaca"])
            f_forn = f4.selectbox("Fornecedor", ["JBS", "RIO MARIA", "BOI BRANCO S.A", "OUTROS"])
            f_pecas = f5.number_input("Qtd Peças", min_value=0)
            f_peso = f6.number_input("Peso Total", min_value=0.0)
            cortes_lista = ["ARANHA", "CAPA CONTRA FILE", "CHAMBARIL TRASEIRO", "CONTRAFILE", "CORACAO ALCATRA", "COXAO DURO", "COXAO MOLE", "FILE MIGNON", "FRALDA", "LOMBO PAULISTA/LAGARTO", "MAMINHA", "MUSCULO TRASEIRO", "PATINHO", "PICANHA", "CARNE BOVINA (LIMPEZA)", "COSTELINHA CONTRA", "OSSO (Descarte)", "OSSO SERRA", "OSSO PATINHO", "SEBO", "ROJAO DA CAPA", "FILEZINHO DE MOCOTÓ"]
            res_val = {"DATA": f_data, "NF": f_nf, "TIPO": f_tipo, "FORNECEDOR": f_forn, "PECAS": f_pecas, "ENTRADA": f_peso}
            c_form = st.columns(2)
            for i, corte in enumerate(cortes_lista):
                with (c_form[0] if i % 2 == 0 else c_form[1]):
                    res_val[corte] = st.number_input(f"{corte}", min_value=0.0, key=f"inp_{corte}")
            if st.form_submit_button("💾 Salvar Registro Diário"):
                if f_peso > 0 and f_nf:
                    salvar_dados_desossa(res_val); st.rerun()
                else: st.error("Preencha NF e Peso.")

    with tab_consulta:
        if os.path.exists("DESOSSA_HISTORICO.csv"):
            df_h = pd.read_csv("DESOSSA_HISTORICO.csv")
            df_h['DATA'] = pd.to_datetime(df_h['DATA']).dt.date
            
            st.markdown("#### 🔍 Filtros de Busca")
            cf1, cf2, cf3, cf4 = st.columns([2, 1, 1, 1])
            with cf1: periodo = st.date_input("Período:", [datetime.now() - timedelta(days=7), datetime.now()])
            with cf2: sel_nf = st.selectbox("NF:", ["Todas"] + sorted(df_h['NF'].astype(str).unique().tolist()))
            with cf3: sel_forn = st.selectbox("Fornecedor:", ["Todos"] + sorted(df_h['FORNECEDOR'].unique().tolist()))
            with cf4: sel_tipo = st.selectbox("Tipo Animal:", ["Todos", "Boi", "Vaca"])
            
            mask = (df_h['DATA'] >= periodo[0]) & (df_h['DATA'] <= periodo[1])
            df_f = df_h.loc[mask]
            if sel_nf != "Todas": df_f = df_f[df_f['NF'].astype(str) == sel_nf]
            if sel_forn != "Todos": df_f = df_f[df_f['FORNECEDOR'] == sel_forn]
            if sel_tipo != "Todos": df_f = df_f[df_f['TIPO'] == sel_tipo]
            
            st.dataframe(df_f, use_container_width=True, hide_index=True)
            
            # BLOCO DO BOTÃO PDF - ISOLADO PARA EVITAR "NONE"
            if not df_f.empty:
                # O PDF só é gerado quando o usuário clica no botão, evitando processamento em loop
                btn_col, _ = st.columns([1, 4])
                with btn_col:
                    st.download_button(
                        label="📄 Gerar Relatório PDF",
                        data=gerar_pdf_bytes(df_f),
                        file_name=f"Relatorio_Desossa_{datetime.now().strftime('%d_%m_%Y')}.pdf",
                        mime="application/pdf",
                        key="btn_pdf_download"
                    )
        else: st.info("Sem registros.")

    st.markdown("---")
    st.subheader("🥩 Top 20 - Volume Físico em Estoque (kg)")
    df_t20 = df_estoque.nlargest(20, 'QTESTGER').sort_values('QTESTGER', ascending=True)
    fig_est = px.bar(df_t20, x='QTESTGER', y='Descrição', orientation='h', color='QTESTGER', color_continuous_scale='Greens', text_auto='.2f')
    st.plotly_chart(fig_est, use_container_width=True)

    st.subheader("📋 Detalhamento Geral de Estoque")
    st.dataframe(df_estoque[['Código', 'Descrição', 'QTESTGER', 'Disponível', 'CUSTOREAL', 'Valor em Estoque']], use_container_width=True, hide_index=True)

    st.info(f"Dashboard ativo na rede interna: http://192.168.1.19:8502")