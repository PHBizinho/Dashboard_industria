import streamlit as st
import oracledb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
from fpdf import FPDF

# --- 1. CONFIGURAÇÃO AMBIENTE ---
st.set_page_config(page_title="Dashboard Seridoense", layout="wide")

st.markdown("""
    <style>
    @media print {
        header, [data-testid="stSidebar"], [data-testid="stHeader"], 
        .stActionButton, [data-testid="stWidgetLabel"], 
        button, .stCheckbox, hr { display: none !important; }
    }
    </style>
""", unsafe_allow_html=True)

if 'oracle_client_initialized' not in st.session_state:
    try:
        oracledb.init_oracle_client(lib_dir=r"C:\oracle\instantclient_19_29")
        st.session_state['oracle_client_initialized'] = True
    except Exception as e:
        st.error(f"Erro Client Oracle: {e}")

# --- 2. FUNÇÃO GERADORA DE PDF (FOCO EM CARNE LIMPA) ---
def gerar_pdf_tecnico(df_filtrado):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Se houver mais de 1 registro, cria uma CAPA DE APROVEITAMENTO
    if len(df_filtrado) > 1:
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.set_text_color(204, 0, 0)
        pdf.cell(190, 10, "RESUMO DE APROVEITAMENTO DE CARNE", 0, 1, 'C')
        pdf.ln(5)
        
        pdf.set_font("Arial", 'B', 10); pdf.set_text_color(0, 0, 0)
        pdf.cell(190, 7, f"Periodo: {df_filtrado['DATA'].min()} ate {df_filtrado['DATA'].max()}", 0, 1, 'L')
        pdf.ln(5)

        # Cálculo focado em "Carne Limpa" (Subtraindo Ossos e Sebo)
        df_calc = df_filtrado.copy()
        itens_descarte = ['OSSO (Descarte)', 'OSSO SERRA', 'OSSO PATINHO', 'SEBO']
        cols_carne = [c for c in cortes_lista if c not in itens_descarte]
        
        df_calc['Carne_Limpa'] = df_calc[cols_carne].sum(axis=1)
        df_calc['%_Carne'] = (df_calc['Carne_Limpa'] / df_calc['ENTRADA']) * 100
        
        media_carne = df_calc['%_Carne'].mean()
        
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(190, 10, f"Media de Aproveitamento de Carne Limpa no Periodo: {media_carne:.2f}%", 1, 1, 'C', True)
        pdf.ln(5)

        # Tabela Comparativa
        pdf.set_fill_color(204, 0, 0); pdf.set_text_color(255, 255, 255)
        pdf.cell(30, 8, "DATA", 1, 0, 'C', True)
        pdf.cell(30, 8, "NF", 1, 0, 'C', True)
        pdf.cell(65, 8, "FORNECEDOR", 1, 0, 'C', True)
        pdf.cell(65, 8, "APROVEITAMENTO CARNE (%)", 1, 1, 'C', True)
        
        pdf.set_font("Arial", '', 9); pdf.set_text_color(0, 0, 0)
        for _, r in df_calc.sort_values('DATA').iterrows():
            pdf.cell(30, 7, str(r['DATA']), 1, 0, 'C')
            pdf.cell(30, 7, str(r['NF']), 1, 0, 'C')
            pdf.cell(65, 7, str(r['FORNECEDOR']), 1, 0, 'C')
            pdf.cell(65, 7, f"{r['%_Carne']:.2f}%", 1, 1, 'C')
        pdf.ln(10)

    # Páginas Individuais (Fichas Técnicas)
    for _, row in df_filtrado.iterrows():
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16); pdf.set_text_color(204, 0, 0) 
        pdf.cell(190, 10, "DETALHAMENTO DA DESOSSA", 0, 1, 'C')
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 9); pdf.set_fill_color(235, 235, 235); pdf.set_text_color(0, 0, 0)
        pdf.cell(30, 7, "NF:", 1, 0, 'L', True); pdf.cell(65, 7, str(row['NF']), 1, 0, 'L')
        pdf.cell(30, 7, "DATA:", 1, 0, 'L', True); pdf.cell(65, 7, str(row['DATA']), 1, 1, 'L')
        pdf.cell(30, 7, "FORNECEDOR:", 1, 0, 'L', True); pdf.cell(65, 7, str(row['FORNECEDOR']), 1, 0, 'L')
        pdf.cell(30, 7, "ENTRADA (Kg):", 1, 0, 'L', True); pdf.cell(65, 7, f"{float(row['ENTRADA']):.2f}", 1, 1, 'L')
        pdf.ln(5)
        
        pdf.set_font("Arial", 'B', 10); pdf.set_fill_color(204, 0, 0); pdf.set_text_color(255, 255, 255)
        pdf.cell(130, 8, " CORTE / ITEM", 1, 0, 'L', True); pdf.cell(60, 8, "PESO (Kg)", 1, 1, 'R', True)
        pdf.set_font("Arial", '', 9); pdf.set_text_color(0, 0, 0)
        
        ignorar = ['DATA', 'NF', 'TIPO', 'FORNECEDOR', 'PECAS', 'ENTRADA']
        total_saida = 0
        for c in row.index:
            if c not in ignorar:
                try:
                    v = float(row[c])
                    if v > 0:
                        pdf.cell(130, 6, f" {c}", 1); pdf.cell(60, 6, f"{v:.2f} ", 1, 1, 'R')
                        total_saida += v
                except: continue
        pdf.ln(2)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(130, 8, "TOTAL PROCESSADO", 0, 0, 'R'); pdf.cell(60, 8, f"{total_saida:.2f} Kg", 1, 1, 'R', True)

    return pdf.output(dest='S').encode('latin-1')

# --- 3. FUNÇÕES DE APOIO ---
@st.cache_data(ttl=600)
def carregar_dados_oracle():
    conn_params = {"user": "NUTRICAO", "password": "nutr1125mmf", "dsn": "192.168.222.20:1521/WINT"}
    try:
        conn = oracledb.connect(**conn_params)
        df = pd.read_sql("SELECT CODPROD, QTESTGER, QTRESERV, QTBLOQUEADA, QTVENDMES, QTVENDMES1, QTVENDMES2, QTVENDMES3, CUSTOREAL FROM MMFRIOS.PCEST WHERE CODFILIAL = 3 AND QTESTGER > 0", conn)
        conn.close()
        df_nomes = pd.read_excel("BASE_DESCRICOES_PRODUTOS.xlsx")
        df_nomes.columns = ['Código', 'Descrição']
        df_f = pd.merge(df, df_nomes, left_on="CODPROD", right_on="Código", how="inner")
        df_f['Valor em Estoque'] = df_f['QTESTGER'] * df_f['CUSTOREAL']
        return df_f
    except: return None

def salvar_dados_desossa(dados_dict):
    arquivo = "DESOSSA_HISTORICO.csv"
    df_novo = pd.DataFrame([dados_dict])
    if os.path.exists(arquivo):
        df_hist = pd.read_csv(arquivo)
        df_hist = pd.concat([df_hist, df_novo], ignore_index=True)
    else: df_hist = df_novo
    df_hist.to_csv(arquivo, index=False)
    st.toast("✅ Dados salvos com sucesso!")

def formatar_br(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- 4. LISTA DE CORTES ---
cortes_lista = ["ARANHA", "CAPA CONTRA FILE", "CHAMBARIL TRASEIRO", "CONTRAFILE", "CORACAO ALCATRA", "COXAO DURO", "COXAO MOLE", "FILE MIGNON", "FRALDA", "LOMBO PAULISTA/LAGARTO", "MAMINHA", "MUSCULO TRASEIRO", "PATINHO", "PICANHA", "CARNE BOVINA (LIMPEZA)", "COSTELINHA CONTRA", "OSSO (Descarte)", "OSSO SERRA", "OSSO PATINHO", "SEBO", "ROJAO DA CAPA", "FILEZINHO DE MOCOTÓ"]

if os.path.exists("DESOSSA_HISTORICO.csv"):
    df_h_real = pd.read_csv("DESOSSA_HISTORICO.csv")
    peso_in = df_h_real['ENTRADA'].sum()
    df_rendimento_final = pd.DataFrame([{"Corte": c, "Rendimento (%)": (df_h_real[c].sum()/peso_in)*100} for c in cortes_lista])
    modo_dados = "REAL"
else:
    df_rendimento_final = pd.DataFrame({"Corte": ["CARNE", "OSSO"], "Rendimento (%)": [80.0, 20.0]})
    modo_dados = "PADRÃO"

# --- 5. INTERFACE ---
st.title("Sistema de Controle de Estoque e Desossa - Seridoense")

df_estoque = carregar_dados_oracle()
if df_estoque is not None:
    # Metricas
    c1, c2, c3 = st.columns(3)
    c1.metric("Estoque (Kg)", f"{formatar_br(df_estoque['QTESTGER'].sum())}")
    c2.metric("Valor (R$)", f"{formatar_br(df_estoque['Valor em Estoque'].sum())}")
    c3.metric("Vendas Mês", f"{formatar_br(df_estoque['QTVENDMES'].sum())}")

    tabs = st.tabs(["📊 Aproveitamento Médio", "🧮 Simulador", "📝 Lançar Desossa", "🔍 Consultar e PDF", "📈 Evolução de Qualidade"])

    with tabs[0]:
        st.plotly_chart(px.bar(df_rendimento_final.sort_values("Rendimento (%)"), x="Rendimento (%)", y="Corte", orientation='h', color_continuous_scale='Reds'), use_container_width=True)

    with tabs[1]:
        entrada = st.number_input("Peso para Simular (Kg):", value=1000.0)
        df_sim = df_rendimento_final.copy()
        df_sim['Previsão (Kg)'] = (df_sim['Rendimento (%)']/100) * entrada
        st.dataframe(df_sim, use_container_width=True, hide_index=True)
        st.success(f"**Total Estimado: {formatar_br(df_sim['Previsão (Kg)'].sum())} Kg**")

    with tabs[2]:
        if st.text_input("Acesso:", type="password") == "serido123":
            with st.form("form_d"):
                f1, f2, f3 = st.columns(3)
                res = {"DATA": f1.date_input("Data"), "NF": f2.text_input("NF"), "FORNECEDOR": f3.selectbox("Fornecedor", ["JBS", "RIO MARIA", "BOI DOURADO", "OUTROS"]), "ENTRADA": st.number_input("Peso Total Entrada", 0.0)}
                cols = st.columns(2)
                for i, c in enumerate(cortes_lista):
                    with (cols[0] if i%2==0 else cols[1]): res[c] = st.number_input(f"{c} (Kg)", 0.0)
                if st.form_submit_button("Salvar"): salvar_dados_desossa(res); st.rerun()

    with tabs[3]:
        if os.path.exists("DESOSSA_HISTORICO.csv"):
            df_h = pd.read_csv("DESOSSA_HISTORICO.csv")
            df_f = df_h.copy()
            st.dataframe(df_f, use_container_width=True)
            st.download_button("📄 Baixar PDF das Desossas", gerar_pdf_tecnico(df_f), "Relatorio_Seridoense.pdf", use_container_width=True)

    with tabs[4]:
        if os.path.exists("DESOSSA_HISTORICO.csv"):
            df_ev = pd.read_csv("DESOSSA_HISTORICO.csv")
            corte_v = st.selectbox("Escolha o Corte para analisar:", cortes_lista, index=3)
            df_ev['Rendimento (%)'] = (df_ev[corte_v] / df_ev['ENTRADA']) * 100
            st.plotly_chart(px.line(df_ev, x='DATA', y='Rendimento (%)', color='FORNECEDOR', markers=True), use_container_width=True)

    # --- VENDAS ---
    st.markdown("---")
    st.subheader("Análise de Vendas")
    busca = st.multiselect("Pesquisar Produto:", sorted(df_estoque['Descrição'].unique()))
    df_v = df_estoque.copy()
    if busca: df_v = df_v[df_v['Descrição'].isin(busca)]
    st.plotly_chart(px.bar(df_v.nlargest(15, 'QTVENDMES'), x='QTVENDMES', y='Descrição', orientation='h'), use_container_width=True)