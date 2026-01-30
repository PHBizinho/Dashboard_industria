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

# --- 2. FUNÇÃO GERADORA DE PDF COM CAPA DE BENCHMARK ---
def gerar_pdf_tecnico(df_filtrado):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # --- PÁGINA 1: CAPA DE BENCHMARK (Se houver mais de 1 registro) ---
    if len(df_filtrado) > 1:
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.set_text_color(204, 0, 0)
        pdf.cell(190, 10, "RESUMO EXECUTIVO - BENCHMARK DE DESOSSA", 0, 1, 'C')
        pdf.ln(5)
        
        # Informações do Período
        pdf.set_font("Arial", 'B', 10)
        pdf.set_text_color(0, 0, 0)
        data_ini = df_filtrado['DATA'].min()
        data_fim = df_filtrado['DATA'].max()
        pdf.cell(190, 7, f"Periodo Analisado: {data_ini} ate {data_fim}", 0, 1, 'L')
        pdf.ln(5)

        # Cálculos de Performance
        df_calc = df_filtrado.copy()
        ignorar = ['DATA', 'NF', 'TIPO', 'FORNECEDOR', 'PECAS', 'ENTRADA']
        df_calc['Soma_Cortes'] = df_calc.drop(columns=ignorar).sum(axis=1)
        df_calc['Rend_%'] = (df_calc['Soma_Cortes'] / df_calc['ENTRADA']) * 100
        
        media_periodo = df_calc['Rend_%'].mean()
        total_kg = df_calc['ENTRADA'].sum()
        melhor_rend = df_calc['Rend_%'].max()
        pior_rend = df_calc['Rend_%'].min()

        # Blocos de Destaque
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(95, 10, f"Peso Total Entrada: {total_kg:.2f} Kg", 1, 0, 'C', True)
        pdf.cell(95, 10, f"Rendimento Medio: {media_periodo:.2f}%", 1, 1, 'C', True)
        pdf.cell(95, 10, f"Melhor Rendimento: {melhor_rend:.2f}%", 1, 0, 'C')
        pdf.cell(95, 10, f"Menor Rendimento: {pior_rend:.2f}%", 1, 1, 'C')
        pdf.ln(10)

        # Tabela de Comparação por Nota/Data
        pdf.set_font("Arial", 'B', 10)
        pdf.set_fill_color(204, 0, 0)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(35, 8, "DATA", 1, 0, 'C', True)
        pdf.cell(35, 8, "NF", 1, 0, 'C', True)
        pdf.cell(60, 8, "FORNECEDOR", 1, 0, 'C', True)
        pdf.cell(60, 8, "RENDIMENTO (%)", 1, 1, 'C', True)
        
        pdf.set_font("Arial", '', 9)
        pdf.set_text_color(0, 0, 0)
        for _, r in df_calc.sort_values('DATA').iterrows():
            pdf.cell(35, 7, str(r['DATA']), 1, 0, 'C')
            pdf.cell(35, 7, str(r['NF']), 1, 0, 'C')
            pdf.cell(60, 7, str(r['FORNECEDOR']), 1, 0, 'C')
            cor_rend = r['Rend_%']
            # Destaque visual se estiver abaixo da média
            status = ""
            if cor_rend < media_periodo: status = " (Abaixo)"
            pdf.cell(60, 7, f"{cor_rend:.2f}%{status}", 1, 1, 'C')
        
        pdf.ln(10)
        pdf.set_font("Arial", 'I', 9)
        pdf.multi_cell(190, 5, "Nota: Este resumo compara a performance de diferentes lotes para identificar variacoes de qualidade entre fornecedores e padronizacao da desossa interna.")

    # --- PÁGINAS INDIVIDUAIS (O que você já tinha) ---
    for _, row in df_filtrado.iterrows():
        pdf.add_page()
        pdf.set_y(15)
        pdf.set_font("Arial", 'B', 16)
        pdf.set_text_color(204, 0, 0) 
        pdf.cell(190, 10, "DETALHAMENTO TECNICO DE DESOSSA", 0, 1, 'C')
        pdf.ln(10) 
        pdf.set_font("Arial", 'B', 9)
        pdf.set_fill_color(235, 235, 235)
        pdf.set_text_color(0, 0, 0)
        # Cabeçalho da Ficha
        pdf.cell(30, 7, "NF:", 1, 0, 'L', True); pdf.cell(65, 7, str(row['NF']), 1, 0, 'L')
        pdf.cell(30, 7, "DATA:", 1, 0, 'L', True); pdf.cell(65, 7, str(row['DATA']), 1, 1, 'L')
        pdf.cell(30, 7, "FORNECEDOR:", 1, 0, 'L', True); pdf.cell(65, 7, str(row['FORNECEDOR']), 1, 0, 'L')
        pdf.cell(30, 7, "TIPO:", 1, 0, 'L', True); pdf.cell(65, 7, str(row['TIPO']), 1, 1, 'L')
        pdf.cell(30, 7, "ENTRADA (Kg):", 1, 0, 'L', True); pdf.cell(65, 7, f"{float(row['ENTRADA']):.2f}", 1, 0, 'L')
        pdf.cell(30, 7, "PECAS:", 1, 0, 'L', True); pdf.cell(65, 7, str(row['PECAS']), 1, 1, 'L')
        pdf.ln(5)
        
        # Tabela de Cortes
        pdf.set_font("Arial", 'B', 10); pdf.set_fill_color(204, 0, 0); pdf.set_text_color(255, 255, 255)
        pdf.cell(130, 8, " CORTE", 1, 0, 'L', True); pdf.cell(60, 8, "PESO LIQUIDO (Kg) ", 1, 1, 'R', True)
        pdf.set_font("Arial", '', 9); pdf.set_text_color(0, 0, 0)
        
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
        
        pdf.ln(2)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(130, 8, "TOTAL PRODUZIDO", 0, 0, 'R'); pdf.cell(60, 8, f"{total_saida:.2f} Kg", 1, 1, 'R', True)
        rend = (total_saida / float(row['ENTRADA'])) * 100 if float(row['ENTRADA']) > 0 else 0
        pdf.cell(130, 8, "RENDIMENTO (%)", 0, 0, 'R'); pdf.cell(60, 8, f"{rend:.2f} %", 1, 1, 'R', True)
        
        pdf.set_y(-25); pdf.set_font("Arial", 'I', 8); pdf.set_text_color(100, 100, 100)
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        pdf.cell(190, 5, f"Relatorio gerado em: {agora}", 0, 1, 'C')
        pdf.cell(190, 5, "Desenvolvido por: Paulo Henrique - Setor Fiscal", 0, 0, 'C')

    return pdf.output(dest='S').encode('latin-1')

# --- 3. FUNÇÕES DE APOIO ---
@st.cache_data(ttl=600)
def carregar_dados_oracle():
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
    st.toast("✅ Desossa salva!", icon='🥩')

def formatar_br(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def obter_nomes_meses():
    meses_pt = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun", 7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}
    hoje = datetime.now()
    return [f"{meses_pt[(hoje.month-i-1)%12+1]}/{str(hoje.year if hoje.month-i > 0 else hoje.year-1)[2:]}" for i in range(4)]

# --- 4. LISTA DE CORTES E RENDIMENTO ---
cortes_lista = ["ARANHA", "CAPA CONTRA FILE", "CHAMBARIL TRASEIRO", "CONTRAFILE", "CORACAO ALCATRA", "COXAO DURO", "COXAO MOLE", "FILE MIGNON", "FRALDA", "LOMBO PAULISTA/LAGARTO", "MAMINHA", "MUSCULO TRASEIRO", "PATINHO", "PICANHA", "CARNE BOVINA (LIMPEZA)", "COSTELINHA CONTRA", "OSSO (Descarte)", "OSSO SERRA", "OSSO PATINHO", "SEBO", "ROJAO DA CAPA", "FILEZINHO DE MOCOTÓ"]

if os.path.exists("DESOSSA_HISTORICO.csv"):
    df_h_real = pd.read_csv("DESOSSA_HISTORICO.csv")
    peso_in = df_h_real['ENTRADA'].sum()
    if peso_in > 0:
        df_rendimento_final = pd.DataFrame([{"Corte": c, "Rendimento (%)": (df_h_real[c].sum()/peso_in)*100} for c in cortes_lista if c in df_h_real.columns])
        modo_dados = "REAL (HISTÓRICO)"
    else:
        df_rendimento_final = pd.DataFrame({"Corte": cortes_lista, "Rendimento (%)": [0.0]*len(cortes_lista)})
        modo_dados = "SEM DADOS"
else:
    df_rendimento_final = pd.DataFrame({"Corte": ["OSSO", "COXAO MOLE", "CONTRAFILE"], "Rendimento (%)": [14.5, 13.4, 10.7]})
    modo_dados = "ESTIMADO"

# --- 5. INTERFACE STREAMLIT ---
col_logo, col_tit = st.columns([1, 5])
with col_logo:
    if os.path.exists("MARCA-SERIDOENSE_.png"): st.image("MARCA-SERIDOENSE_.png", width=120)
with col_tit:
    st.title("Inteligência de Estoque e Benchmark de Desossa")
    st.markdown("*Setor Fiscal - Paulo Henrique*")

df_estoque = carregar_dados_oracle()

if df_estoque is not None:
    # Metricas Topo
    m1, m2, m3 = st.columns(3)
    m1.metric("Estoque Total", f"{formatar_br(df_estoque['QTESTGER'].sum())} Kg")
    m2.metric("Valor Total", f"R$ {formatar_br(df_estoque['Valor em Estoque'].sum())}")
    m3.metric(f"Venda {obter_nomes_meses()[0]}", f"{formatar_br(df_estoque['QTVENDMES'].sum())} Kg")

    tabs = st.tabs(["📊 Rendimento", "🧮 Simulador", "📝 Registro", "🔍 Consulta e PDF", "📈 Benchmark e Evolucao"])

    with tabs[0]:
        fig = px.bar(df_rendimento_final.sort_values("Rendimento (%)"), x="Rendimento (%)", y="Corte", orientation='h', color="Rendimento (%)", color_continuous_scale='Reds', text_auto='.2f')
        st.plotly_chart(fig, use_container_width=True)

    with tabs[1]:
        p_in = st.number_input("Peso Total Entrada (Kg):", min_value=0.0, value=1000.0)
        df_sim = df_rendimento_final.copy()
        df_sim['Previsão (Kg)'] = (df_sim['Rendimento (%)'] / 100) * p_in
        st.dataframe(df_sim.sort_values('Previsão (Kg)', ascending=False), use_container_width=True, hide_index=True)
        st.success(f"**Total Estimado Produzido: {formatar_br(df_sim['Previsão (Kg)'].sum())} Kg**")

    with tabs[2]:
        if st.text_input("Senha:", type="password") == "serido123":
            with st.form("f_des"):
                c1, c2, c3, c4, c5, c6 = st.columns(6)
                res = {"DATA": c1.date_input("Data"), "NF": c2.text_input("NF"), "TIPO": c3.selectbox("Tipo", ["Boi", "Vaca"]), "FORNECEDOR": c4.selectbox("Forn.", ["JBS", "RIO MARIA", "BOI BRANCO", "BOI DOURADO", "OUTROS"]), "PECAS": c5.number_input("Peças", 0), "ENTRADA": c6.number_input("Peso In", 0.0)}
                cols = st.columns(2)
                for i, c in enumerate(cortes_lista):
                    with (cols[0] if i%2==0 else cols[1]): res[c] = st.number_input(f"{c} (kg)", 0.0)
                if st.form_submit_button("Salvar"):
                    if res["NF"] and res["ENTRADA"] > 0: salvar_dados_desossa(res); st.rerun()

    with tabs[3]:
        if os.path.exists("DESOSSA_HISTORICO.csv"):
            df_h = pd.read_csv("DESOSSA_HISTORICO.csv")
            df_h['DATA'] = pd.to_datetime(df_h['DATA']).dt.date
            f1, f2, f3 = st.columns(3)
            p_sel = f1.date_input("Periodo:", [datetime.now().date()-timedelta(7), datetime.now().date()])
            forn_sel = f2.selectbox("Fornecedor:", ["Todos"] + list(df_h['FORNECEDOR'].unique()))
            df_f = df_h.copy()
            if len(p_sel) == 2: df_f = df_f[(df_f['DATA'] >= p_sel[0]) & (df_f['DATA'] <= p_sel[1])]
            if forn_sel != "Todos": df_f = df_f[df_f['FORNECEDOR'] == forn_sel]
            st.dataframe(df_f, use_container_width=True, hide_index=True)
            if not df_f.empty:
                st.download_button("📄 Gerar Relatorio com Benchmark", gerar_pdf_tecnico(df_f), "Relatorio_Desossa.pdf", "application/pdf", use_container_width=True)

    with tabs[4]:
        if os.path.exists("DESOSSA_HISTORICO.csv"):
            df_temp = pd.read_csv("DESOSSA_HISTORICO.csv")
            df_temp['DATA'] = pd.to_datetime(df_temp['DATA'])
            c_alvo = st.selectbox("Corte:", cortes_lista, index=3)
            f_comp = st.multiselect("Comparar:", options=df_temp['FORNECEDOR'].unique(), default=df_temp['FORNECEDOR'].unique()[:2])
            
            df_c = df_temp.copy()
            df_c['Rend_%'] = (df_c[c_alvo]/df_c['ENTRADA'])*100
            m1, m2, m3 = st.columns(3)
            m1.metric("Media Historica", f"{df_c['Rend_%'].mean():.2f}%")
            m2.metric("Ultimo Registro", f"{df_c['Rend_%'].iloc[-1]:.2f}%")
            m3.metric("Desvio", f"{df_c['Rend_%'].iloc[-1]-df_c['Rend_%'].mean():.2f}%", delta=f"{df_c['Rend_%'].iloc[-1]-df_c['Rend_%'].mean():.2f}%")
            
            if f_comp:
                df_ev = df_temp[df_temp['FORNECEDOR'].isin(f_comp)].copy()
                df_ev['Rendimento (%)'] = (df_ev[c_alvo]/df_ev['ENTRADA'])*100
                st.plotly_chart(px.line(df_ev.sort_values('DATA'), x='DATA', y='Rendimento (%)', color='FORNECEDOR', markers=True), use_container_width=True)
                st.markdown("#### Tabela de Benchmark")
                st.dataframe(df_ev.groupby('FORNECEDOR')['Rendimento (%)'].mean().reset_index(), use_container_width=True, hide_index=True)

    # --- ANALISE DE ESTOQUE E VENDAS ---
    st.markdown("---")
    st.subheader("📦 Posicao de Estoque e Vendas")
    s1, s2 = st.columns([1, 4])
    with s1:
        v_mode = st.radio("Filtro Venda:", ["Mes Atual", "Historico"])
        f_prod = st.multiselect("Pesquisar:", sorted(df_estoque['Descrição'].unique()))
    
    df_v = df_estoque.copy()
    if f_prod: df_v = df_v[df_v['Descrição'].isin(f_prod)]
    
    with s2:
        if v_mode == "Mes Atual":
            st.plotly_chart(px.bar(df_v.nlargest(15, 'QTVENDMES'), x='QTVENDMES', y='Descrição', orientation='h', title="Top Vendas (Kg)"), use_container_width=True)
        else:
            fig_v = go.Figure(); m_nomes = obter_nomes_meses(); top10 = df_v.nlargest(10, 'QTVENDMES')
            for i, col in enumerate(['QTVENDMES', 'QTVENDMES1', 'QTVENDMES2', 'QTVENDMES3']):
                fig_v.add_trace(go.Bar(name=m_nomes[i], y=top10['Descrição'], x=top10[col], orientation='h'))
            st.plotly_chart(fig_v.update_layout(barmode='group'), use_container_width=True)

    st.dataframe(df_estoque[['Código', 'Descrição', 'QTESTGER', 'CUSTOREAL', 'Valor em Estoque']], use_container_width=True, hide_index=True)