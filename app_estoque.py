import streamlit as st
import oracledb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
from fpdf import FPDF

# --- 1. CONFIGURAÇÃO AMBIENTE E ESTILO ---
st.set_page_config(page_title="Dashboard Seridoense", layout="wide")

# CSS para esconder elementos desnecessários na impressão manual
st.markdown("""
    <style>
    @media print {
        header, [data-testid="stSidebar"], [data-testid="stHeader"], 
        .stActionButton, [data-testid="stWidgetLabel"], 
        button, .stCheckbox, hr {
            display: none !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

if 'oracle_client_initialized' not in st.session_state:
    try:
        oracledb.init_oracle_client(lib_dir=r"C:\oracle\instantclient_19_29")
        st.session_state['oracle_client_initialized'] = True
    except Exception as e:
        st.error(f"Erro Client Oracle: {e}")

# --- 2. FUNÇÃO GERADORA DE PDF (SEM LOGO - FOCO NO TEXTO) ---
def gerar_pdf_tecnico(df_filtrado):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    for _, row in df_filtrado.iterrows():
        pdf.add_page()
        
        # TÍTULO CENTRALIZADO NO TOPO
        pdf.set_y(15)
        pdf.set_font("Arial", 'B', 16)
        pdf.set_text_color(204, 0, 0) # Vermelho Seridoense
        pdf.cell(190, 10, "RELATORIO TECNICO DE DESOSSA", 0, 1, 'C')
        
        # Espaço entre título e dados
        pdf.ln(10) 
        
        # 3. CABEÇALHO DA FICHA (Tabela Cinza)
        pdf.set_font("Arial", 'B', 9)
        pdf.set_fill_color(235, 235, 235)
        pdf.set_text_color(0, 0, 0)
        
        # Linha 1
        pdf.cell(30, 7, "NF:", 1, 0, 'L', True)
        pdf.cell(65, 7, str(row['NF']), 1, 0, 'L')
        pdf.cell(30, 7, "DATA:", 1, 0, 'L', True)
        pdf.cell(65, 7, str(row['DATA']), 1, 1, 'L')
        
        # Linha 2
        pdf.cell(30, 7, "FORNECEDOR:", 1, 0, 'L', True)
        pdf.cell(65, 7, str(row['FORNECEDOR']), 1, 0, 'L')
        pdf.cell(30, 7, "TIPO:", 1, 0, 'L', True)
        pdf.cell(65, 7, str(row['TIPO']), 1, 1, 'L')
        
        # Linha 3
        pdf.cell(30, 7, "ENTRADA (Kg):", 1, 0, 'L', True)
        pdf.cell(65, 7, f"{float(row['ENTRADA']):.2f}", 1, 0, 'L')
        pdf.cell(30, 7, "PECAS:", 1, 0, 'L', True)
        pdf.cell(65, 7, str(row['PECAS']), 1, 1, 'L')
        pdf.ln(5)
        
        # 4. TABELA DE CORTES
        pdf.set_font("Arial", 'B', 10)
        pdf.set_fill_color(204, 0, 0)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(130, 8, " CORTE", 1, 0, 'L', True)
        pdf.cell(60, 8, "PESO LIQUIDO (Kg) ", 1, 1, 'R', True)
        
        pdf.set_font("Arial", '', 9)
        pdf.set_text_color(0, 0, 0)
        ignorar = ['DATA', 'NF', 'TIPO', 'FORNECEDOR', 'PECAS', 'ENTRADA']
        total_saida = 0
        
        for c in row.index:
            if c not in ignorar:
                try:
                    valor = float(row[c])
                    if valor > 0:
                        pdf.cell(130, 6, f" {c}", 1)
                        pdf.cell(60, 6, f"{valor:.2f}  ", 1, 1, 'R')
                        total_saida += valor
                except: continue
        
        # 5. RESUMO DE RENDIMENTO
        pdf.ln(2)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(130, 8, "TOTAL PRODUZIDO (SOMA DOS CORTES)", 0, 0, 'R')
        pdf.cell(60, 8, f"{total_saida:.2f} Kg", 1, 1, 'R', True)
        
        rendimento = (total_saida / float(row['ENTRADA'])) * 100 if float(row['ENTRADA']) > 0 else 0
        pdf.cell(130, 8, "RENDIMENTO DA CARGA (%)", 0, 0, 'R')
        pdf.cell(60, 8, f"{rendimento:.2f} %", 1, 1, 'R', True)
        
        # 6. RODAPÉ (Data e Desenvolvedor)
        pdf.set_y(-25)
        pdf.set_font("Arial", 'I', 8)
        pdf.set_text_color(100, 100, 100)
        data_geracao = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        pdf.cell(190, 5, f"Relatorio gerado em: {data_geracao}", 0, 1, 'C')
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(190, 5, "Desenvolvido por: Paulo Henrique - Setor Fiscal", 0, 0, 'C')
        
    return pdf.output(dest='S').encode('latin-1')

# --- 3. FUNÇÕES DE DADOS E APOIO ---
@st.cache_data(ttl=600)
def carregar_dados():
    conn_params = {"user": "NUTRICAO", "password": "nutr1125mmf", "dsn": "192.168.222.20:1521/WINT"}
    try:
        conn = oracledb.connect(**conn_params)
        query = "SELECT CODPROD, QTESTGER, QTRESERV, QTBLOQUEADA, QTVENDMES, QTVENDMES1, QTVENDMES2, QTVENDMES3, CUSTOREAL FROM MMFRIOS.PCEST WHERE CODFILIAL = 3 AND QTESTGER > 0"
        df = pd.read_sql(query, conn)
        conn.close()
        df_nomes = pd.read_excel("BASE_DESCRICOES_PRODUTOS.xlsx")
        df_nomes.columns = ['Código', 'Descrição']
        df_f = pd.merge(df, df_nomes, left_on="CODPROD", right_on="Código", how="inner")
        df_f['Disponível'] = df_f['QTESTGER'] - df_f['QTRESERV'] - df_f['QTBLOQUEADA']
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
    st.toast("✅ Desossa salva no histórico!", icon='🥩')

def formatar_br(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def obter_nomes_meses():
    meses_pt = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun", 7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}
    hoje = datetime.now()
    lista = []
    for i in range(4):
        m, y = hoje.month - i, hoje.year
        while m <= 0: m += 12; y -= 1
        lista.append(f"{meses_pt[m]}/{str(y)[2:]}")
    return lista

# --- 4. INTERFACE PRINCIPAL ---
st.title("Sistema de Inteligência de Estoque e Desossa")
st.markdown("*Responsável: **Paulo Henrique**, Setor Fiscal*")

df_estoque = carregar_dados()

if df_estoque is not None:
    c1, c2, c3 = st.columns(3)
    c1.metric("Estoque Total (Kg)", f"{formatar_br(df_estoque['QTESTGER'].sum())} Kg")
    c2.metric("Valor Imobilizado", f"R$ {formatar_br(df_estoque['Valor em Estoque'].sum())}")
    c3.metric(f"Venda {obter_nomes_meses()[0]}", f"{formatar_br(df_estoque['QTVENDMES'].sum())} Kg")
    st.markdown("---")

    tab_rend, tab_sim, tab_lancto, tab_consulta = st.tabs([
        "📊 Gráfico de Rendimento", "🧮 Simulador de Carga", "📝 Registro Real Diário", "🔍 Histórico e Consulta"
    ])

    with tab_rend:
        dados_rend = {"Corte": ["OSSO BOV KG PROD", "COXAO MOLE BOV KG PROD", "CONTRAFILE BOV KG PROD", "COXAO DURO BOV KG PROD", "CARNE BOV PROD (LIMPEZA)", "PATINHO BOV KG PROD", "MUSCULO TRASEIRO BOV KG PROD", "CORACAO ALCATRA BOV KG PROD", "CAPA CONTRA FILE BOV KG PROD", "LOMBO PAULISTA BOV KG PROD", "OSSO BOV SERRA KG PROD", "FRALDA BOV KG PROD", "FILE MIGNON BOV PROD PÇ±1.6 KG", "MAMINHA BOV KG PROD", "PICANHA BOV KG PROD", "COSTELINHA CONTRA FILE KG PROD", "SEBO BOV KG PROD", "OSSO PATINHO BOV KG PROD", "ARANHA BOV KG PROD", "FILEZINHO MOCOTO KG PROD"], "Rendimento (%)": [14.56, 13.4, 10.75, 9.32, 8.04, 7.88, 6.68, 5.42, 3.64, 3.60, 3.07, 2.65, 2.37, 2.27, 1.71, 1.69, 1.38, 0.76, 0.63, 0.18]}
        st.plotly_chart(px.bar(pd.DataFrame(dados_rend).sort_values("Rendimento (%)", ascending=True), x="Rendimento (%)", y="Corte", orientation='h', color="Rendimento (%)", color_continuous_scale='Reds', text_auto='.2f'), use_container_width=True)

    with tab_sim:
        p_entrada = st.number_input("Peso para simular (Kg):", min_value=0.0, value=25000.0)
        df_sim = pd.DataFrame(dados_rend)
        df_sim['Previsão (Kg)'] = (df_sim['Rendimento (%)'] / 100) * p_entrada
        st.dataframe(df_sim.sort_values('Previsão (Kg)', ascending=False), use_container_width=True, hide_index=True)

    with tab_lancto:
        with st.form("form_desossa", clear_on_submit=True):
            f1, f2, f3, f4, f5, f6 = st.columns(6)
            res_val = {"DATA": f1.date_input("Data"), "NF": f2.text_input("Nº NF"), "TIPO": f3.selectbox("Tipo", ["Boi", "Vaca"]), "FORNECEDOR": f4.selectbox("Fornecedor", ["JBS", "RIO MARIA", "BOI BRANCO S.A", "OUTROS"]), "PECAS": f5.number_input("Qtd Peças", 0), "ENTRADA": f6.number_input("Peso Total", 0.0)}
            cortes_lista = ["ARANHA", "CAPA CONTRA FILE", "CHAMBARIL TRASEIRO", "CONTRAFILE", "CORACAO ALCATRA", "COXAO DURO", "COXAO MOLE", "FILE MIGNON", "FRALDA", "LOMBO PAULISTA/LAGARTO", "MAMINHA", "MUSCULO TRASEIRO", "PATINHO", "PICANHA", "CARNE BOVINA (LIMPEZA)", "COSTELINHA CONTRA", "OSSO (Descarte)", "OSSO SERRA", "OSSO PATINHO", "SEBO", "ROJAO DA CAPA", "FILEZINHO DE MOCOTÓ"]
            c_form = st.columns(2)
            for i, corte in enumerate(cortes_lista):
                with (c_form[0] if i % 2 == 0 else c_form[1]): res_val[corte] = st.number_input(f"{corte}", min_value=0.0, key=f"inp_{corte}")
            if st.form_submit_button("💾 Salvar Registro Diário"):
                if res_val["ENTRADA"] > 0 and res_val["NF"]: salvar_dados_desossa(res_val); st.rerun()
                else: st.error("Erro: NF e Peso de Entrada são obrigatórios.")

    with tab_consulta:
        if os.path.exists("DESOSSA_HISTORICO.csv"):
            df_h = pd.read_csv("DESOSSA_HISTORICO.csv")
            df_h['DATA'] = pd.to_datetime(df_h['DATA']).dt.date
            
            st.markdown("#### 🔍 Filtros de Consulta")
            cf1, cf2, cf3, cf4 = st.columns([2, 1, 1, 1])
            with cf1: periodo = st.date_input("Período:", [datetime.now().date() - timedelta(days=7), datetime.now().date()])
            with cf2: sel_nf = st.selectbox("Filtrar NF:", ["Todas"] + sorted(df_h['NF'].astype(str).unique().tolist()))
            with cf3: sel_forn = st.selectbox("Fornecedor:", ["Todos"] + sorted(df_h['FORNECEDOR'].unique().tolist()))
            with cf4: sel_tipo = st.selectbox("Tipo:", ["Todos", "Boi", "Vaca"])
            
            df_f = df_h.copy()
            if len(periodo) == 2: df_f = df_f[(df_f['DATA'] >= periodo[0]) & (df_f['DATA'] <= periodo[1])]
            if sel_nf != "Todas": df_f = df_f[df_f['NF'].astype(str) == sel_nf]
            if sel_forn != "Todos": df_f = df_f[df_f['FORNECEDOR'] == sel_forn]
            if sel_tipo != "Todos": df_f = df_f[df_f['TIPO'] == sel_tipo]
            
            st.dataframe(df_f, use_container_width=True, hide_index=True)

            if not df_f.empty:
                st.download_button("📄 Baixar Relatórios Técnicos (PDF)", gerar_pdf_tecnico(df_f), f"Desossa_Seridoense_{datetime.now().strftime('%d%m%Y')}.pdf", "application/pdf", use_container_width=True)
                
                if st.checkbox("📑 Visualizar Distribuição (Gráficos na tela)"):
                    for _, row in df_f.iterrows():
                        with st.container(border=True):
                            st.write(f"**NF: {row['NF']} | {row['FORNECEDOR']}**")
                            ignorar = ['DATA', 'NF', 'TIPO', 'FORNECEDOR', 'PECAS', 'ENTRADA']
                            cortes_enc = {c: float(row[c]) for c in row.index if c not in ignorar and float(row[c]) > 0}
                            st.plotly_chart(px.pie(pd.DataFrame(list(cortes_enc.items()), columns=['C','P']), values='P', names='C', hole=0.4), use_container_width=True)
        else: st.info("Nenhum histórico encontrado.")

    # --- SEÇÃO FIXA: ESTOQUE E VENDAS ---
    st.markdown("---")
    st.subheader("🥩 Top 20 - Volume em Estoque (kg)")
    st.plotly_chart(px.bar(df_estoque.nlargest(20, 'QTESTGER').sort_values('QTESTGER'), x='QTESTGER', y='Descrição', orientation='h', color='QTESTGER', color_continuous_scale='Greens', text_auto='.2f').update_layout(height=700), use_container_width=True)

    st.markdown("---")
    st.subheader("🏆 Análise de Vendas (KG)")
    cv1, cv2 = st.columns([4, 1])
    with cv2: v_modo = st.radio("Modo de Visão:", ["Mês Atual", "Comparativo"])
    with cv1:
        if v_modo == "Mês Atual":
            st.plotly_chart(px.bar(df_estoque.nlargest(15, 'QTVENDMES'), x='QTVENDMES', y='Descrição', orientation='h', color_continuous_scale='Blues', text_auto='.1f'), use_container_width=True)
        else:
            fig_v = go.Figure(); meses = obter_nomes_meses()
            for i, c_v in enumerate(['QTVENDMES', 'QTVENDMES1', 'QTVENDMES2', 'QTVENDMES3']):
                fig_v.add_trace(go.Bar(name=meses[i], y=df_estoque.nlargest(10, 'QTVENDMES')['Descrição'], x=df_estoque.nlargest(10, 'QTVENDMES')[c_v], orientation='h'))
            st.plotly_chart(fig_v.update_layout(barmode='group', height=500), use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Detalhamento Geral de Itens")
    st.dataframe(df_estoque[['Código', 'Descrição', 'QTESTGER', 'Disponível', 'CUSTOREAL', 'Valor em Estoque']], use_container_width=True, hide_index=True)

    st.info("Dashboard Seridoense - Desenvolvido por Paulo Henrique (Setor Fiscal)")