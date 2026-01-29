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

# --- 2. FUNÇÃO GERADORA DE PDF ---
def gerar_pdf_tecnico(df_filtrado):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    for _, row in df_filtrado.iterrows():
        pdf.add_page()
        pdf.set_y(15)
        pdf.set_font("Arial", 'B', 16)
        pdf.set_text_color(204, 0, 0) 
        pdf.cell(190, 10, "RELATÓRIO DE DESOSSA", 0, 1, 'C')
        pdf.ln(10) 
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
        pdf.ln(2)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(130, 8, "TOTAL PRODUZIDO", 0, 0, 'R')
        pdf.cell(60, 8, f"{total_saida:.2f} Kg", 1, 1, 'R', True)
        rendimento = (total_saida / float(row['ENTRADA'])) * 100 if float(row['ENTRADA']) > 0 else 0
        pdf.cell(130, 8, "RENDIMENTO (%)", 0, 0, 'R')
        pdf.cell(60, 8, f"{rendimento:.2f} %", 1, 1, 'R', True)
        pdf.set_y(-25)
        pdf.set_font("Arial", 'I', 8)
        pdf.set_text_color(100, 100, 100)
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        pdf.cell(190, 5, f"Relatorio gerado em: {agora}", 0, 1, 'C')
        pdf.set_font("Arial", 'B', 8)
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
    lista = []
    for i in range(4):
        m, y = hoje.month - i, hoje.year
        while m <= 0: m += 12; y -= 1
        lista.append(f"{meses_pt[m]}/{str(y)[2:]}")
    return lista

# --- 4. PREPARAÇÃO DOS DADOS ---
cortes_lista = ["ARANHA", "CAPA CONTRA FILE", "CHAMBARIL TRASEIRO", "CONTRAFILE", "CORACAO ALCATRA", "COXAO DURO", "COXAO MOLE", "FILE MIGNON", "FRALDA", "LOMBO PAULISTA/LAGARTO", "MAMINHA", "MUSCULO TRASEIRO", "PATINHO", "PICANHA", "CARNE BOVINA (LIMPEZA)", "COSTELINHA CONTRA", "OSSO (Descarte)", "OSSO SERRA", "OSSO PATINHO", "SEBO", "ROJAO DA CAPA", "FILEZINHO DE MOCOTÓ"]

if os.path.exists("DESOSSA_HISTORICO.csv"):
    df_h_real = pd.read_csv("DESOSSA_HISTORICO.csv")
    peso_total_entrada = df_h_real['ENTRADA'].sum()
    if peso_total_entrada > 0:
        lista_rend = []
        for corte in cortes_lista:
            if corte in df_h_real.columns:
                perc = (df_h_real[corte].sum() / peso_total_entrada) * 100
                lista_rend.append({"Corte": corte, "Rendimento (%)": perc})
        df_rendimento_final = pd.DataFrame(lista_rend)
        modo_dados = "REAL (HISTÓRICO)"
    else:
        df_rendimento_final = pd.DataFrame({"Corte": cortes_lista, "Rendimento (%)": [0.0]*len(cortes_lista)})
        modo_dados = "SEM DADOS"
else:
    dados_padrao = {"Corte": ["OSSO (Descarte)", "COXAO MOLE", "CONTRAFILE", "COXAO DURO", "CARNE BOVINA (LIMPEZA)", "PATINHO", "MUSCULO TRASEIRO", "CORACAO ALCATRA", "CAPA CONTRA FILE", "LOMBO PAULISTA/LAGARTO"], "Rendimento (%)": [14.56, 13.4, 10.75, 9.32, 8.04, 7.88, 6.68, 5.42, 3.64, 3.60]}
    df_rendimento_final = pd.DataFrame(dados_padrao)
    modo_dados = "ESTIMADO (PADRÃO)"

# --- 5. INTERFACE ---
col_logo, col_tit = st.columns([1, 5])
with col_logo:
    if os.path.exists("MARCA-SERIDOENSE_.png"):
        st.image("MARCA-SERIDOENSE_.png", width=120)

with col_tit:
    st.title("Sistema de Inteligência de Estoque e Desossa")
    st.markdown("*Desenvolvido por: **Paulo Henrique**, Setor Fiscal*")

df_estoque = carregar_dados_oracle()

if df_estoque is not None:
    c1, c2, c3 = st.columns(3)
    c1.metric("Estoque Total (Kg)", f"{formatar_br(df_estoque['QTESTGER'].sum())} Kg")
    c2.metric("Valor Imobilizado", f"R$ {formatar_br(df_estoque['Valor em Estoque'].sum())}")
    c3.metric(f"Venda {obter_nomes_meses()[0]}", f"{formatar_br(df_estoque['QTVENDMES'].sum())} Kg")
    st.markdown("---")

    tab_rend, tab_sim, tab_lancto, tab_consulta, tab_evolucao = st.tabs([
        "📊 Rendimento Geral", "🧮 Simulador", "📝 Registro Diário", "🔍 Consulta", "📈 Benchmark e Evolução"
    ])

    with tab_rend:
        st.subheader(f"Média de Rendimento: {modo_dados}")
        fig_real = px.bar(df_rendimento_final.sort_values("Rendimento (%)", ascending=True), 
                          x="Rendimento (%)", y="Corte", orientation='h', color="Rendimento (%)", 
                          color_continuous_scale='Reds', text_auto='.2f')
        fig_real.update_traces(textfont_size=15, textposition='outside', cliponaxis=False)
        fig_real.update_layout(margin=dict(r=80), height=600)
        st.plotly_chart(fig_real, use_container_width=True)

    with tab_sim:
        st.subheader("Simulador de Produção (Base Real)")
        p_entrada = st.number_input("Peso Total da Carga (Kg):", min_value=0.0, value=1000.0)
        df_sim = df_rendimento_final.copy()
        df_sim['Previsão (Kg)'] = (df_sim['Rendimento (%)'] / 100) * p_entrada
        st.dataframe(df_sim.sort_values('Previsão (Kg)', ascending=False), use_container_width=True, hide_index=True)

    with tab_lancto:
        st.subheader("Novo Registro de Desossa")
        senha_acesso = st.text_input("Senha:", type="password", key="senha_lancto")
        if senha_acesso == "serido123": 
            with st.form("form_desossa", clear_on_submit=True):
                f1, f2, f3, f4, f5, f6 = st.columns(6)
                res_val = {"DATA": f1.date_input("Data"), "NF": f2.text_input("Nº NF"), 
                           "TIPO": f3.selectbox("Tipo", ["Boi", "Vaca"]), 
                           "FORNECEDOR": f4.selectbox("Fornecedor", ["JBS", "RIO MARIA", "BOI BRANCO S.A", "BOI DOURADO", "OUTROS"]), 
                           "PECAS": f5.number_input("Qtd Peças", 0), "ENTRADA": f6.number_input("Peso Entrada", 0.0)}
                c_form = st.columns(2)
                for i, corte in enumerate(cortes_lista):
                    with (c_form[0] if i % 2 == 0 else c_form[1]): 
                        res_val[corte] = st.number_input(f"{corte} (kg)", min_value=0.0, key=f"inp_{corte}")
                if st.form_submit_button("💾 Salvar Dados"):
                    if res_val["ENTRADA"] > 0 and res_val["NF"]: 
                        salvar_dados_desossa(res_val)
                        st.rerun()
                    else: st.error("NF e Peso de Entrada são obrigatórios.")

    with tab_consulta:
        if os.path.exists("DESOSSA_HISTORICO.csv"):
            df_h = pd.read_csv("DESOSSA_HISTORICO.csv")
            df_h['DATA'] = pd.to_datetime(df_h['DATA']).dt.date
            cf1, cf2, cf3, cf4 = st.columns([2, 1, 1, 1])
            with cf1: periodo = st.date_input("Período:", [datetime.now().date() - timedelta(days=7), datetime.now().date()], key="filtro_per")
            with cf2: sel_nf = st.selectbox("NF:", ["Todas"] + sorted(df_h['NF'].astype(str).unique().tolist()))
            with cf3: sel_forn = st.selectbox("Fornecedor:", ["Todos"] + sorted(df_h['FORNECEDOR'].unique().tolist()))
            with cf4: sel_tipo = st.selectbox("Tipo:", ["Todos", "Boi", "Vaca"])
            df_f = df_h.copy()
            if len(periodo) == 2: df_f = df_f[(df_f['DATA'] >= periodo[0]) & (df_f['DATA'] <= periodo[1])]
            if sel_nf != "Todas": df_f = df_f[df_f['NF'].astype(str) == sel_nf]
            if sel_forn != "Todos": df_f = df_f[df_f['FORNECEDOR'] == sel_forn]
            if sel_tipo != "Todos": df_f = df_f[df_f['TIPO'] == sel_tipo]
            st.dataframe(df_f, use_container_width=True, hide_index=True)
            if not df_f.empty:
                st.download_button("📄 Exportar PDFs", gerar_pdf_tecnico(df_f), f"Desossa_{datetime.now().strftime('%d%m%Y')}.pdf", "application/pdf", use_container_width=True)
        else: st.info("Sem histórico.")

    with tab_evolucao:
        if os.path.exists("DESOSSA_HISTORICO.csv"):
            st.subheader("Benchmark de Rendimento Interno e Externo")
            df_temp = pd.read_csv("DESOSSA_HISTORICO.csv")
            df_temp['DATA'] = pd.to_datetime(df_temp['DATA'])
            
            ev_c1, ev_c2 = st.columns([2, 3])
            with ev_c1:
                corte_alvo = st.selectbox("Corte para Benchmark:", cortes_lista, index=3)
            with ev_c2:
                fornecedores_comp = st.multiselect("Comparar Fornecedores:", options=sorted(df_temp['FORNECEDOR'].unique()),
                                                  default=sorted(df_temp['FORNECEDOR'].unique())[:2])
            
            # --- Benchmark Interno ---
            df_corte_geral = df_temp.copy()
            df_corte_geral['Rend_%'] = (df_corte_geral[corte_alvo] / df_corte_geral['ENTRADA']) * 100
            media_historica = df_corte_geral['Rend_%'].mean()
            ultimo_rendimento = df_corte_geral['Rend_%'].iloc[-1]
            variacao = ultimo_rendimento - media_historica

            m1, m2, m3 = st.columns(3)
            m1.metric("Média Histórica (Benchmark)", f"{media_historica:.2f}%")
            m2.metric("Último Rendimento Real", f"{ultimo_rendimento:.2f}%")
            m3.metric("Desvio vs Padrão", f"{variacao:.2f}%", delta=f"{variacao:.2f}%")
            
            st.markdown("---")

            if fornecedores_comp:
                df_ev = df_temp[df_temp['FORNECEDOR'].isin(fornecedores_comp)].copy()
                df_ev[f"Rendimento {corte_alvo} (%)"] = (df_ev[corte_alvo] / df_ev['ENTRADA']) * 100
                df_ev = df_ev.sort_values('DATA')

                # Gráfico de Evolução
                fig_benchmark = px.line(df_ev, x='DATA', y=f"Rendimento {corte_alvo} (%)", color='FORNECEDOR',
                                        markers=True, title=f"Evolução Temporal: {corte_alvo}",
                                        labels={f"Rendimento {corte_alvo} (%)": "Rendimento (%)"})
                fig_benchmark.update_layout(hovermode="x unified")
                st.plotly_chart(fig_benchmark, use_container_width=True)

                # --- TABELA DE COMPARAÇÃO DE FORNECEDORES (RESTAURADA) ---
                st.markdown(f"#### 📊 Comparativo de Médias: {corte_alvo}")
                resumo_comp = df_ev.groupby('FORNECEDOR')[f"Rendimento {corte_alvo} (%)"].mean().reset_index()
                resumo_comp.columns = ['Fornecedor', 'Média de Rendimento (%)']
                
                # Formatação visual da tabela
                st.dataframe(
                    resumo_comp.sort_values('Média de Rendimento (%)', ascending=False).style.format({'Média de Rendimento (%)': '{:.2f}%'}),
                    use_container_width=True,
                    hide_index=True
                )
        else:
            st.info("Aguardando histórico.")

    # --- 6. ANÁLISE DE ESTOQUE ---
    st.markdown("---")
    st.subheader("🥩 Top 20 - Volume em Estoque (kg)")
    fig_est = px.bar(df_estoque.nlargest(20, 'QTESTGER').sort_values('QTESTGER'), 
                     x='QTESTGER', y='Descrição', orientation='h', color='QTESTGER', 
                     color_continuous_scale='Greens', text_auto='.2f')
    fig_est.update_layout(height=700, margin=dict(r=80))
    fig_est.update_traces(textfont_size=14, textposition='outside', cliponaxis=False)
    st.plotly_chart(fig_est, use_container_width=True)

    st.markdown("---")
    st.subheader("🏆 Análise de Vendas (KG)")
    cv1, cv2 = st.columns([4, 1])
    with cv2: 
        v_modo = st.radio("Visão Vendas:", ["Mês Atual", "Comparativo"])
    df_vendas_final = df_estoque.copy()
    with cv1:
        if v_modo == "Mês Atual":
            fig_v_atual = px.bar(df_vendas_final.nlargest(15, 'QTVENDMES'), x='QTVENDMES', y='Descrição', orientation='h', color_continuous_scale='Blues', text_auto='.1f')
            fig_v_atual.update_traces(textfont_size=14, textposition='outside')
            st.plotly_chart(fig_v_atual, use_container_width=True)
        else:
            fig_v = go.Figure(); meses = obter_nomes_meses(); top_10 = df_vendas_final.nlargest(10, 'QTVENDMES')
            for i, c_v in enumerate(['QTVENDMES', 'QTVENDMES1', 'QTVENDMES2', 'QTVENDMES3']):
                fig_v.add_trace(go.Bar(name=meses[i], y=top_10['Descrição'], x=top_10[c_v], orientation='h'))
            st.plotly_chart(fig_v.update_layout(barmode='group', height=500), use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Detalhamento Geral de Itens")
    st.dataframe(df_estoque[['Código', 'Descrição', 'QTESTGER', 'Disponível', 'CUSTOREAL', 'Valor em Estoque']], 
                 use_container_width=True, hide_index=True)