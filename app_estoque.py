import streamlit as st
import oracledb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os

# --- 1. CONFIGURAÇÃO AMBIENTE ---
if 'oracle_client_initialized' not in st.session_state:
    try:
        oracledb.init_oracle_client(lib_dir=r"C:\oracle\instantclient_19_29")
        st.session_state['oracle_client_initialized'] = True
    except Exception as e:
        st.error(f"Erro Client Oracle: {e}")

# --- 2. FUNÇÕES DE APOIO ---
@st.cache_data(ttl=600)
def carregar_dados_oracle():
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
        try:
            df_hist = pd.read_csv(arquivo)
            df_hist = pd.concat([df_hist, df_novo], ignore_index=True)
        except: df_hist = df_novo
    else: df_hist = df_novo
    df_hist.to_csv(arquivo, index=False)
    st.toast("✅ Registro salvo!", icon='🥩')

def formatar_br(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- 3. INTERFACE ---
st.set_page_config(page_title="Dashboard Seridoense", layout="wide")

# Cabeçalho com Logo
c_l, c_t = st.columns([1, 5])
with c_l:
    if os.path.exists("MARCA-SERIDOENSE_.png"): st.image("MARCA-SERIDOENSE_.png", width=130)
with c_t:
    st.title("Sistema de Inteligência Seridoense")
    st.markdown("*Responsável: **Paulo Henrique**, Setor Fiscal*")

df_estoque = carregar_dados_oracle()

if df_estoque is not None:
    tab_rend, tab_sim, tab_lancto, tab_consulta = st.tabs([
        "📊 Rendimento", "🧮 Simulação", "📝 Lançamento", "🔍 Histórico"
    ])

    # --- ABA LANÇAMENTO (Simplificada para o exemplo) ---
    with tab_lancto:
        with st.form("form_desossa", clear_on_submit=True):
            f1, f2, f3 = st.columns(3)
            f_data = f1.date_input("Data", datetime.now())
            f_nf = f2.text_input("Nº NF")
            f_forn = f3.selectbox("Fornecedor", ["JBS", "RIO MARIA", "BOI BRANCO S.A", "OUTROS"])
            if st.form_submit_button("Salvar"):
                salvar_dados_desossa({"DATA": f_data, "NF": f_nf, "FORNECEDOR": f_forn, "ENTRADA": 0, "TIPO": "Boi"})
                st.rerun()

    # --- ABA HISTÓRICO (Onde estava o problema) ---
    with tab_consulta:
        if os.path.exists("DESOSSA_HISTORICO.csv"):
            try:
                df_h = pd.read_csv("DESOSSA_HISTORICO.csv")
                df_h['DATA'] = pd.to_datetime(df_h['DATA']).dt.date
                
                st.markdown("#### 🔍 Filtros de Busca")
                cf1, cf2, cf3 = st.columns([2, 1, 1])
                
                with cf1:
                    hoje = datetime.now().date()
                    periodo = st.date_input("Período (Clique Início e Fim):", [hoje - timedelta(days=30), hoje])
                with cf2:
                    sel_nf = st.selectbox("NF:", ["Todas"] + sorted(df_h['NF'].astype(str).unique().tolist()))
                with cf3:
                    sel_forn = st.selectbox("Fornecedor:", ["Todos"] + sorted(df_h['FORNECEDOR'].unique().tolist()))
                
                # FILTRAGEM SEGURA
                df_f = df_h.copy()
                
                # Se o período estiver completo, filtra. Se não, mostra tudo do mês.
                if isinstance(periodo, (list, tuple)) and len(periodo) == 2:
                    df_f = df_f[(df_f['DATA'] >= periodo[0]) & (df_f['DATA'] <= periodo[1])]
                
                if sel_nf != "Todas":
                    df_f = df_f[df_f['NF'].astype(str) == sel_nf]
                if sel_forn != "Todos":
                    df_f = df_f[df_f['FORNECEDOR'] == sel_forn]

                if not df_f.empty:
                    st.success(f"Exibindo {len(df_f)} registro(s) encontrado(s).")
                    st.dataframe(df_f, use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhum registro encontrado para os filtros selecionados.")
                    
            except Exception as e:
                st.error(f"Erro ao ler arquivo: {e}")
        else:
            st.info("Ainda não existem registros salvos.")

    # --- DASHBOARD DE VENDAS E ESTOQUE (Rodapé) ---
    st.markdown("---")
    st.subheader("🥩 Visão Geral de Estoque")
    st.dataframe(df_estoque[['Descrição', 'QTESTGER', 'Valor em Estoque']], use_container_width=True, hide_index=True)