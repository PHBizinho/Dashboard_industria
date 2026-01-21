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

# Inicialização do Client Oracle
if 'oracle_client_initialized' not in st.session_state:
    try:
        oracledb.init_oracle_client(lib_dir=r"C:\oracle\instantclient_19_29")
        st.session_state['oracle_client_initialized'] = True
    except Exception as e:
        st.error(f"Erro Client Oracle: {e}")

# --- 2. FUNÇÃO GERADORA DE PDF (VERSÃO FINAL PROFISSIONAL) ---
def gerar_pdf_consolidado(df_filtrado):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    for _, row in df_filtrado.iterrows():
        pdf.add_page()
        
        # 1. LOGO (x=10, y=8, largura=35)
        if os.path.exists("MARCA-SERIDOENSE_.png"):
            pdf.image("MARCA-SERIDOENSE_.png", 10, 8, 35)
        
        # 2. TÍTULO DO RELATÓRIO
        pdf.set_font("Arial", 'B', 14)
        pdf.set_text_color(204, 0, 0) # Vermelho Seridoense
        pdf.cell(190, 10, "RELATORIO TECNICO DE DESOSSA", 0, 1, 'C')
        pdf.ln(8)
        
        # 3. CABEÇALHO DA CARGA
        pdf.set_font("Arial", 'B', 9)
        pdf.set_fill_color(235, 235, 235)
        pdf.set_text_color(0, 0, 0)
        
        pdf.cell(30, 7, "NF:", 1, 0, 'L', True)
        pdf.cell(65, 7, str(row['NF']), 1, 0, 'L')
        pdf.cell(30, 7, "DATA:", 1, 0, 'L', True)
        pdf.cell(65, 7, str(row['DATA']), 1, 1, 'L')
        
        pdf.cell(30, 7, "FORNECEDOR:", 1, 0, 'L', True)
        pdf.cell(65, 7, str(row['FORNECEDOR']), 1, 0, 'L')
        pdf.cell(30, 7, "TIPO:", 1, 0, 'L', True)
        pdf.cell(65, 7, str(row['TIPO']), 1, 1, 'L')
        
        pdf.cell(30, 7, "ENTRADA (Kg):", 1, 0, 'L', True)
        pdf.cell(65, 7, f"{float(row['ENTRADA']):.2f}", 1, 0, 'L')
        pdf.cell(30, 7, "PECAS:", 1, 0, 'L', True)
        pdf.cell(65, 7, str(row['PECAS']), 1, 1, 'L')
        pdf.ln(5)
        
        # 4. TABELA TÉCNICA DE PRODUTOS
        pdf.set_font("Arial", 'B', 10)
        pdf.set_fill_color(204, 0, 0)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(130, 8, " CORTE / PRODUTO", 1, 0, 'L', True)
        pdf.cell(60, 8, "PESO LIQUIDO (Kg) ", 1, 1, 'R', True)
        
        pdf.set_font("Arial", '', 9)
        pdf.set_text_color(0, 0, 0)
        
        # Identificar colunas de cortes (ignorar metadados)
        ignorar = ['DATA', 'NF', 'TIPO', 'FORNECEDOR', 'PECAS', 'ENTRADA']
        cortes = {c: float(row[c]) for c in row.index if c not in ignorar and float(row[c]) > 0}
        
        total_saida_kg = 0
        for corte, peso in cortes.items():
            pdf.cell(130, 6, f" {corte}", 1)
            pdf.cell(60, 6, f"{peso:.2f}  ", 1, 1, 'R')
            total_saida_kg += peso
            
        # 5. RESUMO DE RENDIMENTO
        pdf.ln(2)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(130, 8, "TOTAL PRODUZIDO (SOMA DOS CORTES)", 0, 0, 'R')
        pdf.cell(60, 8, f"{total_saida_kg:.2f} Kg", 1, 1, 'R', True)
        
        rendimento = (total_saida_kg / float(row['ENTRADA'])) * 100 if float(row['ENTRADA']) > 0 else 0
        pdf.cell(130, 8, "RENDIMENTO DA CARGA (%)", 0, 0, 'R')
        pdf.cell(60, 8, f"{rendimento:.2f} %", 1, 1, 'R', True)
        
        # 6. RODAPÉ COM DATA E ASSINATURA
        pdf.set_y(-25)
        pdf.set_font("Arial", 'I', 8)
        pdf.set_text_color(100, 100, 100)
        data_emissao = datetime.now().strftime("%d/%m/%Y %H:%M")
        pdf.cell(190, 5, f"Relatorio gerado em: {data_emissao}", 0, 1, 'C')
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(190, 5, "Desenvolvido por: Paulo Henrique - Setor Fiscal", 0, 0, 'C')

    return pdf.output(dest='S').encode('latin-1')

# --- 3. FUNÇÕES DE DADOS (ORACLE E APOIO) ---
@st.cache_data(ttl=600)
def carregar_dados_estoque():
    params = {"user": "NUTRICAO", "password": "nutr1125mmf", "dsn": "192.168.222.20:1521/WINT"}
    try:
        conn = oracledb.connect(**params)
        query = "SELECT CODPROD, QTESTGER, QTRESERV, QTBLOQUEADA, QTVENDMES, QTVENDMES1, QTVENDMES2, QTVENDMES3, CUSTOREAL FROM MMFRIOS.PCEST WHERE CODFILIAL = 3 AND QTESTGER > 0"
        df = pd.read_sql(query, conn)
        conn.close()
        # Mesclar nomes
        df_nomes = pd.read_excel("BASE_DESCRICOES_PRODUTOS.xlsx")
        df_nomes.columns = ['Código', 'Descrição']
        df_f = pd.merge(df, df_nomes, left_on="CODPROD", right_on="Código", how="inner")
        df_f['Disponível'] = df_f['QTESTGER'] - df_f['QTRESERV'] - df_f['QTBLOQUEADA']
        df_f['Valor em Estoque'] = df_f['QTESTGER'] * df_f['CUSTOREAL']
        return df_f
    except: return None

def formatar_moeda_br(v):
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def nomes_meses_venda():
    meses_pt = {1:"Jan", 2:"Fev", 3:"Mar", 4:"Abr", 5:"Mai", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Set", 10:"Out", 11:"Nov", 12:"Dez"}
    hoje = datetime.now()
    return [f"{meses_pt[(hoje.month-i-1)%12+1]}/{str(hoje.year)[2:]}" for i in range(4)]

# --- 4. INTERFACE STREAMLIT ---
col_logo, col_tit = st.columns([1, 5])
with col_logo:
    if os.path.exists("MARCA-SERIDOENSE_.png"): st.image("MARCA-SERIDOENSE_.png", width=140)
with col_tit:
    st.title("Sistema de Inteligência de Estoque e Desossa")
    st.markdown("*Responsável: **Paulo Henrique**, Setor Fiscal*")

df_est = carregar_dados_estoque()

if df_est is not None:
    # Métricas Principais
    m1, m2, m3 = st.columns(3)
    m1.metric("Estoque Total (Kg)", f"{formatar_moeda_br(df_est['QTESTGER'].sum())} Kg")
    m2.metric("Valor Imobilizado", f"R$ {formatar_moeda_br(df_est['Valor em Estoque'].sum())}")
    m3.metric(f"Venda {nomes_meses_venda()[0]}", f"{formatar_moeda_br(df_est['QTVENDMES'].sum())} Kg")

    st.markdown("---")
    
    # Abas de Operação
    t_rend, t_sim, t_reg, t_hist = st.tabs(["📊 Rendimento Padrao", "🧮 Simulador", "📝 Novo Registro", "🔍 Historico e PDF"])

    with t_rend:
        dados_rend = {"Corte": ["OSSO BOV KG PROD", "COXAO MOLE BOV KG PROD", "CONTRAFILE BOV KG PROD", "COXAO DURO BOV KG PROD", "CARNE BOV PROD (LIMPEZA)", "PATINHO BOV KG PROD", "MUSCULO TRASEIRO BOV KG PROD", "CORACAO ALCATRA BOV KG PROD", "CAPA CONTRA FILE BOV KG PROD", "LOMBO PAULISTA BOV KG PROD", "OSSO BOV SERRA KG PROD", "FRALDA BOV KG PROD", "FILE MIGNON BOV PROD PÇ±1.6 KG", "MAMINHA BOV KG PROD", "PICANHA BOV KG PROD", "COSTELINHA CONTRA FILE KG PROD", "SEBO BOV KG PROD", "OSSO PATINHO BOV KG PROD", "ARANHA BOV KG PROD", "FILEZINHO MOCOTO KG PROD"], "Rendimento (%)": [14.56, 13.4, 10.75, 9.32, 8.04, 7.88, 6.68, 5.42, 3.64, 3.60, 3.07, 2.65, 2.37, 2.27, 1.71, 1.69, 1.38, 0.76, 0.63, 0.18]}
        st.plotly_chart(px.bar(pd.DataFrame(dados_rend).sort_values("Rendimento (%)", ascending=True), x="Rendimento (%)", y="Corte", orientation='h', color="Rendimento (%)", color_continuous_scale='Reds', text_auto='.2f'), use_container_width=True)

    with t_sim:
        entrada = st.number_input("Simular Carga (Kg):", min_value=0.0, value=25000.0)
        df_sim = pd.DataFrame(dados_rend); df_sim['Previsão (Kg)'] = (df_sim['Rendimento (%)']/100)*entrada
        st.dataframe(df_sim.sort_values('Previsão (Kg)', ascending=False), use_container_width=True, hide_index=True)

    with t_reg:
        with st.form("form_lancto", clear_on_submit=True):
            f1, f2, f3, f4, f5, f6 = st.columns(6)
            res = {"DATA": f1.date_input("Data"), "NF": f2.text_input("NF"), "TIPO": f3.selectbox("Tipo", ["Boi", "Vaca"]), "FORNECEDOR": f4.selectbox("Forn.", ["JBS", "RIO MARIA", "BOI BRANCO", "OUTROS"]), "PECAS": f5.number_input("Peças", 0), "ENTRADA": f6.number_input("Peso Total", 0.0)}
            cortes_l = ["ARANHA", "CAPA CONTRA FILE", "CHAMBARIL TRASEIRO", "CONTRAFILE", "CORACAO ALCATRA", "COXAO DURO", "COXAO MOLE", "FILE MIGNON", "FRALDA", "LOMBO PAULISTA/LAGARTO", "MAMINHA", "MUSCULO TRASEIRO", "PATINHO", "PICANHA", "CARNE BOVINA (LIMPEZA)", "COSTELINHA CONTRA", "OSSO (Descarte)", "OSSO SERRA", "OSSO PATINHO", "SEBO", "ROJAO DA CAPA", "FILEZINHO DE MOCOTÓ"]
            c_col = st.columns(2)
            for i, c in enumerate(cortes_l):
                with (c_col[0] if i%2==0 else c_col[1]): res[c] = st.number_input(c, 0.0, key=f"in_{c}")
            if st.form_submit_button("💾 SALVAR DESOSSA"):
                pd.DataFrame([res]).to_csv("DESOSSA_HISTORICO.csv", mode='a', index=False, header=not os.path.exists("DESOSSA_HISTORICO.csv"))
                st.success("Registro Salvo!"); st.rerun()

    with t_hist:
        if os.path.exists("DESOSSA_HISTORICO.csv"):
            df_h = pd.read_csv("DESOSSA_HISTORICO.csv")
            st.markdown("#### Filtros")
            h1, h2 = st.columns(2)
            with h1: p_datas = st.date_input("Período:", [datetime.now().date()-timedelta(days=7), datetime.now().date()])
            with h2: nfs_sel = st.multiselect("NFs:", df_h['NF'].unique())
            
            df_final_h = df_h.copy()
            if len(p_datas)==2: df_final_h = df_final_h[(pd.to_datetime(df_final_h['DATA']).dt.date >= p_datas[0]) & (pd.to_datetime(df_final_h['DATA']).dt.date <= p_datas[1])]
            if nfs_sel: df_final_h = df_final_h[df_final_h['NF'].isin(nfs_sel)]
            
            st.dataframe(df_final_h, use_container_width=True, hide_index=True)
            if not df_final_h.empty:
                # Gerar e oferecer download do PDF
                btn_pdf = gerar_pdf_consolidado(df_final_h)
                st.download_button("📄 BAIXAR RELATÓRIO PDF CONSOLIDADO", btn_pdf, f"Relatorio_Desossa_{datetime.now().strftime('%d%m%Y')}.pdf", "application/pdf", use_container_width=True)
                
                st.markdown("---")
                # Gráfico de Pizza VISUAL (Só na tela)
                if st.checkbox("Ver Distribuição Visual (Pizza) na tela"):
                    for _, r in df_final_h.iterrows():
                        cortes_r = {c: float(r[c]) for c in r.index if c not in ignorar and float(r[c]) > 0}
                        st.plotly_chart(px.pie(pd.DataFrame(list(cortes_r.items()), columns=['C','P']), values='P', names='C', title=f"NF {r['NF']}", hole=0.4), use_container_width=True)
        else:
            st.info("Ainda não há registros no histórico.")

    # --- SEÇÃO FIXA (GRÁFICOS DE ESTOQUE E VENDAS) ---
    st.markdown("---")
    st.subheader("🥩 Top 20 - Volume em Estoque (kg)")
    st.plotly_chart(px.bar(df_est.nlargest(20, 'QTESTGER').sort_values('QTESTGER'), x='QTESTGER', y='Descrição', orientation='h', color='QTESTGER', color_continuous_scale='Greens', text_auto='.2f').update_layout(height=700), use_container_width=True)
    
    st.subheader("🏆 Análise de Vendas (KG)")
    cv1, cv2 = st.columns([4, 1])
    with cv2: v_modo = st.radio("Visão:", ["Mês Atual", "Comparativo"])
    with cv1:
        if v_modo == "Mês Atual":
            st.plotly_chart(px.bar(df_est.nlargest(15, 'QTVENDMES'), x='QTVENDMES', y='Descrição', orientation='h', color_continuous_scale='Blues', text_auto='.1f'), use_container_width=True)
        else:
            fig_v = go.Figure(); m_nomes = nomes_meses_venda()
            for i, c_v in enumerate(['QTVENDMES', 'QTVENDMES1', 'QTVENDMES2', 'QTVENDMES3']):
                fig_v.add_trace(go.Bar(name=m_nomes[i], y=df_est.nlargest(10, 'QTVENDMES')['Descrição'], x=df_est.nlargest(10, 'QTVENDMES')[c_v], orientation='h'))
            st.plotly_chart(fig_v.update_layout(barmode='group'), use_container_width=True)

    st.subheader("📋 Detalhamento Geral de Estoque")
    st.dataframe(df_est[['Código', 'Descrição', 'QTESTGER', 'Disponível', 'CUSTOREAL', 'Valor em Estoque']], use_container_width=True, hide_index=True)

    st.info(f"Dashboard Seridoense - Desenvolvido por Paulo Henrique")