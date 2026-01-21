import streamlit as st
import oracledb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os

# --- 1. CONFIGURAÇÃO AMBIENTE E ESTILO DE IMPRESSÃO ---
st.set_page_config(page_title="Dashboard Seridoense", layout="wide")

# CSS Avançado para Impressão: Esconde tudo, exceto o conteúdo do relatório detalhado
st.markdown("""
    <style>
    @media print {
        /* Esconde menus, botões, abas e rodapés do Streamlit */
        header, [data-testid="stSidebar"], [data-testid="stHeader"], 
        .stActionButton, [data-testid="stWidgetLabel"], 
        button, .stCheckbox, hr, [data-testid="stTabs"] {
            display: none !important;
        }
        /* Remove espaços em branco no topo */
        .main .block-container {
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
        }
        /* Garante que o conteúdo ocupe a página toda */
        .main {
            width: 100% !important;
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
    st.toast(f"✅ Desossa salva!", icon='🥩')

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
col_logo, col_tit = st.columns([1, 5])
with col_logo:
    if os.path.exists("MARCA-SERIDOENSE_.png"): st.image("MARCA-SERIDOENSE_.png", width=140)
with col_tit:
    st.title("Sistema de Inteligência de Estoque e Desossa")
    st.markdown("*Responsável: **Paulo Henrique**, Setor Fiscal*")

df_estoque = carregar_dados()

if df_estoque is not None:
    # Métricas principais (escondidas na impressão pelo CSS acima se necessário)
    c1, c2, c3 = st.columns(3)
    c1.metric("Estoque Total (Kg)", f"{formatar_br(df_estoque['QTESTGER'].sum())} Kg")
    c2.metric("Valor Imobilizado", f"R$ {formatar_br(df_estoque['Valor em Estoque'].sum())}")
    c3.metric(f"Venda {obter_nomes_meses()[0]}", f"{formatar_br(df_estoque['QTVENDMES'].sum())} Kg")
    st.markdown("---")

    tab_rend, tab_sim, tab_lancto, tab_consulta = st.tabs([
        "📊 Rendimento", "🧮 Simulador", "📝 Registro Diário", "🔍 Histórico e Consulta"
    ])

    with tab_consulta:
        if os.path.exists("DESOSSA_HISTORICO.csv"):
            df_h = pd.read_csv("DESOSSA_HISTORICO.csv")
            df_h['DATA'] = pd.to_datetime(df_h['DATA']).dt.date
            
            st.markdown("#### 🔍 Filtros de Busca")
            cf1, cf2, cf3, cf4 = st.columns([2, 1, 1, 1])
            with cf1: 
                periodo = st.date_input("Período:", [datetime.now().date() - timedelta(days=7), datetime.now().date()], key="filtro_data")
            with cf2: 
                sel_nf = st.selectbox("NF:", ["Todas"] + sorted(df_h['NF'].astype(str).unique().tolist()))
            with cf3: 
                sel_forn = st.selectbox("Fornecedor:", ["Todos"] + sorted(df_h['FORNECEDOR'].unique().tolist()))
            with cf4: 
                sel_tipo = st.selectbox("Tipo Animal:", ["Todos", "Boi", "Vaca"])
            
            # --- FILTRAGEM DINÂMICA SEGURA ---
            df_f = df_h.copy()
            if isinstance(periodo, (list, tuple)) and len(periodo) == 2:
                df_f = df_f[(df_f['DATA'] >= periodo[0]) & (df_f['DATA'] <= periodo[1])]
            
            if sel_nf != "Todas": df_f = df_f[df_f['NF'].astype(str) == sel_nf]
            if sel_forn != "Todos": df_f = df_f[df_f['FORNECEDOR'] == sel_forn]
            if sel_tipo != "Todos": df_f = df_f[df_f['TIPO'] == sel_tipo]
            
            st.dataframe(df_f, use_container_width=True, hide_index=True)

            if not df_f.empty:
                show_report = st.checkbox("📑 GERAR FICHAS PARA IMPRESSÃO (Marque aqui e use Ctrl+P)")
                
                if show_report:
                    st.markdown("---")
                    for _, row in df_f.iterrows():
                        # Cada ficha dentro de um container que vira uma "página"
                        with st.container():
                            st.write(f"### Relatório de Desossa - NF: {row['NF']}")
                            c_rel1, c_rel2 = st.columns([1, 2])
                            with c_rel1:
                                if os.path.exists("MARCA-SERIDOENSE_.png"): st.image("MARCA-SERIDOENSE_.png", width=150)
                            with c_rel2:
                                st.write(f"**Fornecedor:** {row['FORNECEDOR']}")
                                st.write(f"**Data:** {row['DATA']} | **Tipo:** {row['TIPO']}")
                            
                            st.info(f"**Peso Entrada:** {row['ENTRADA']} Kg | **Qtd Peças:** {row['PECAS']}")
                            
                            ignorar = ['DATA', 'NF', 'TIPO', 'FORNECEDOR', 'PECAS', 'ENTRADA']
                            cortes_encontrados = {c: float(row[c]) for c in row.index if c not in ignorar and float(row[c]) > 0}
                            df_rel_corte = pd.DataFrame(list(cortes_encontrados.items()), columns=['Corte', 'Peso (Kg)'])
                            
                            col_tab, col_graph = st.columns([1, 1])
                            with col_tab: 
                                st.table(df_rel_corte)
                            with col_graph:
                                fig_pizza = px.pie(df_rel_corte, values='Peso (Kg)', names='Corte', hole=0.3, color_discrete_sequence=px.colors.sequential.Reds_r)
                                fig_pizza.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
                                fig_pizza.update_traces(textposition='inside', textinfo='percent+label')
                                st.plotly_chart(fig_pizza, use_container_width=True)
                            st.markdown('<div style="page-break-after: always;"></div>', unsafe_allow_html=True) # Quebra de página para impressão
        else:
            st.info("Ainda não há registros.")

    # Os demais gráficos de Estoque e Vendas ficam abaixo das abas
    # Eles serão escondidos na impressão se você imprimir enquanto a aba "Consulta" estiver aberta
    # com o checkbox "GERAR FICHAS" marcado.

    st.markdown("---")
    st.subheader("🥩 Volume em Estoque")
    df_t20 = df_estoque.nlargest(20, 'QTESTGER').sort_values('QTESTGER', ascending=True)
    fig_est = px.bar(df_t20, x='QTESTGER', y='Descrição', orientation='h', color='QTESTGER', color_continuous_scale='Greens', text_auto='.2f')
    st.plotly_chart(fig_est, use_container_width=True)