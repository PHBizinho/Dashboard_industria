import streamlit as st
import oracledb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os

# --- 1. CONFIGURAÇÃO AMBIENTE E ESTILO DE IMPRESSÃO ---
st.set_page_config(page_title="Dashboard Seridoense", layout="wide")

# CSS PERSONALIZADO: Cores da Seridoense e Ajuste para Impressão Real
st.markdown("""
    <style>
    /* Estilo para a tela */
    .stApp { background-color: #f8f9fa; }
    
    /* Estilo do Relatório (Ficha) */
    .relatorio-container {
        border: 2px solid #CC0000;
        padding: 25px;
        border-radius: 10px;
        background-color: white;
        margin-bottom: 20px;
    }

    @media print {
        /* Esconde menus, botões, barras laterais e abas na hora de imprimir */
        header, [data-testid="stSidebar"], [data-testid="stHeader"], 
        .stActionButton, [data-testid="stWidgetLabel"], 
        button, .stCheckbox, hr, .stTabs, .no-print {
            display: none !important;
        }
        
        /* Remove margens extras do Streamlit */
        .main .block-container {
            padding: 0 !important;
            margin: 0 !important;
        }

        /* Garante que o relatório ocupe a página toda */
        .relatorio-container {
            border: 1px solid #000 !important;
            display: block !important;
            width: 100% !important;
        }
        
        /* Força tabelas a não quebrarem e aparecerem por inteiro */
        table { width: 100% !important; page-break-inside: auto; }
        tr { page-break-inside: avoid; page-break-after: auto; }
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
    except:
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

# --- 3. INTERFACE ---
col_logo, col_tit = st.columns([1, 5])
with col_logo:
    if os.path.exists("MARCA-SERIDOENSE_.png"): st.image("MARCA-SERIDOENSE_.png", width=140)
with col_tit:
    st.title("Sistema de Inteligência de Estoque e Desossa")
    st.markdown("Desenvolvido por: **Paulo Henrique - Setor Fiscal**")

df_estoque = carregar_dados()

if df_estoque is not None:
    st.markdown("---")
    
    # Abas principais
    tab_rend, tab_sim, tab_lancto, tab_consulta = st.tabs([
        "📊 Rendimento", "🧮 Simulador", "📝 Registro Diário", "🔍 Histórico e Relatórios"
    ])

    with tab_consulta:
        if os.path.exists("DESOSSA_HISTORICO.csv"):
            df_h = pd.read_csv("DESOSSA_HISTORICO.csv")
            df_h['DATA'] = pd.to_datetime(df_h['DATA']).dt.date
            
            st.markdown("#### 🔍 Filtre a NF para Gerar a Ficha de Impressão")
            cf1, cf2 = st.columns([1, 1])
            with cf1: sel_nf = st.selectbox("Selecione a Nota Fiscal:", ["Selecione..."] + sorted(df_h['NF'].astype(str).unique().tolist()))
            
            if sel_nf != "Selecione...":
                row = df_h[df_h['NF'].astype(str) == sel_nf].iloc[0]
                
                # Instrução para o usuário
                st.warning("👉 Para salvar o relatório: Pressione **Ctrl + P** e escolha 'Salvar como PDF'.")
                
                # INÍCIO DA ÁREA DE RELATÓRIO (IDENTIDADE SERIDOENSE)
                st.markdown(f"""
                    <div class="relatorio-container">
                        <h2 style='color: #CC0000; margin-top: 0;'>RELATÓRIO DE DESOSSA - SERIDOENSE</h2>
                        <hr style='border: 1px solid #CC0000;'>
                        <p><b>NF:</b> {row['NF']} | <b>FORNECEDOR:</b> {row['FORNECEDOR']} | <b>DATA:</b> {row['DATA']}</p>
                        <p><b>TIPO:</b> {row['TIPO']} | <b>PESO ENTRADA:</b> {row['ENTRADA']} Kg | <b>QTD PEÇAS:</b> {row['PECAS']}</p>
                    </div>
                """, unsafe_allow_html=True)
                
                # Dados para o Gráfico de Pizza e Tabela
                ignorar = ['DATA', 'NF', 'TIPO', 'FORNECEDOR', 'PECAS', 'ENTRADA']
                cortes = {c: float(row[c]) for c in row.index if c not in ignorar and float(row[c]) > 0}
                df_rel = pd.DataFrame(list(cortes.items()), columns=['Corte', 'Peso (Kg)'])
                
                col_tab, col_pizza = st.columns([1, 1])
                
                with col_tab:
                    st.markdown("### 📋 Detalhamento dos Itens")
                    st.table(df_rel) # st.table é obrigatório para sair na impressão
                
                with col_pizza:
                    st.markdown("### 🍕 Distribuição de Rendimento")
                    fig_p = px.pie(df_rel, values='Peso (Kg)', names='Corte', 
                                 hole=0.4, color_discrete_sequence=px.colors.sequential.Reds_r)
                    fig_p.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
                    fig_p.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_p, use_container_width=True)
                
                # Rodapé de Autoria na Ficha
                st.markdown(f"""
                    <div style='text-align: center; margin-top: 50px; border-top: 1px solid #ddd; padding-top: 10px;'>
                        <p style='font-size: 10px; color: gray;'>Relatório gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                        <p><b>Desenvolvido por: Paulo Henrique - Setor Fiscal</b></p>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Nenhum registro encontrado no arquivo DESOSSA_HISTORICO.csv")

    # --- Seção de Estoque e Vendas (Abaixo das abas) ---
    st.markdown("<div class='no-print'>", unsafe_allow_html=True) # Esconde isso na impressão
    st.markdown("---")
    st.subheader("🥩 Top 20 - Volume em Estoque (kg)")
    df_t20 = df_estoque.nlargest(20, 'QTESTGER').sort_values('QTESTGER', ascending=True)
    fig_est = px.bar(df_t20, x='QTESTGER', y='Descrição', orientation='h', 
                    color='QTESTGER', color_continuous_scale='Greens', text_auto='.2f')
    st.plotly_chart(fig_est, use_container_width=True)
    
    st.subheader("📋 Detalhamento Geral de Estoque")
    st.dataframe(df_estoque[['Código', 'Descrição', 'QTESTGER', 'Disponível', 'CUSTOREAL', 'Valor em Estoque']], 
                 use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)