import streamlit as st
import oracledb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

# --- 1. CONFIGURAÇÃO AMBIENTE (WinThor) ---
if 'oracle_client_initialized' not in st.session_state:
    try:
        # Ajuste o caminho do client de acordo com sua instalação
        oracledb.init_oracle_client(lib_dir=r"C:\oracle\instantclient_19_29")
        st.session_state['oracle_client_initialized'] = True
    except Exception as e:
        st.error(f"Erro Client Oracle: {e}")

# --- 2. FUNÇÕES DE DADOS ---

@st.cache_data(ttl=600)
def carregar_dados_estoque():
    conn_params = {"user": "NUTRICAO", "password": "nutr1125mmf", "dsn": "192.168.222.20:1521/WINT"}
    try:
        conn = oracledb.connect(**conn_params)
        query = """SELECT CODPROD, QTESTGER, QTRESERV, QTBLOQUEADA, QTVENDMES, 
                           QTVENDMES1, QTVENDMES2, QTVENDMES3, CUSTOREAL 
                    FROM MMFRIOS.PCEST WHERE CODFILIAL = 3 AND QTESTGER > 0"""
        df = pd.read_sql(query, conn)
        conn.close()
        
        # Carregando descrições do arquivo Excel
        df_nomes = pd.read_excel("BASE_DESCRICOES_PRODUTOS.xlsx")
        df_nomes.columns = ['Código', 'Descrição']
        df_final = pd.merge(df, df_nomes, left_on="CODPROD", right_on="Código", how="inner")
        
        df_final['Disponível'] = df_final['QTESTGER'] - df_final['QTRESERV'] - df_final['QTBLOQUEADA']
        df_final['Valor em Estoque'] = df_final['QTESTGER'] * df_final['CUSTOREAL']
        return df_final
    except Exception as e:
        st.error(f"Erro ao conectar no banco (Estoque): {e}")
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
    st.success("✅ Lançamento de desossa realizado com sucesso!")

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

# --- 3. INTERFACE STREAMLIT ---
st.set_page_config(page_title="Dashboard Seridoense", layout="wide")

# Cabeçalho
col_logo, col_tit = st.columns([1, 5])
with col_logo:
    if os.path.exists("MARCA-SERIDOENSE_.png"):
        st.image("MARCA-SERIDOENSE_.png", width=140)
with col_tit:
    st.title("Dashboard de Estoque e Rendimento")
    st.markdown("*Desenvolvido por: **Paulo Henrique**, Setor Fiscal*")

# Carregamento de Dados do WinThor
df = carregar_dados_estoque()

if df is not None:
    # --- BLOCO 1: KPIs PRINCIPAIS ---
    t_kg = df['QTESTGER'].sum()
    t_val = df['Valor em Estoque'].sum()
    
    col_k1, col_k2, col_k3 = st.columns(3)
    col_k1.metric("Estoque Total (Kg)", f"{formatar_br(t_kg)} Kg")
    col_k2.metric("Valor Imobilizado", f"R$ {formatar_br(t_val)}")
    col_k3.metric(f"Venda {obter_nomes_meses()[0]}", f"{formatar_br(df['QTVENDMES'].sum())} Kg")

    st.markdown("---")

    # --- BLOCO 2: LANÇAMENTO DE DESOSSA REAL (ENTRADA MANUAL) ---
    st.subheader("📝 Registro de Desossa Diária")
    with st.expander("Clique para abrir o formulário de lançamento"):
        with st.form("input_desossa"):
            c1, c2, c3 = st.columns(3)
            f_data = c1.date_input("Data da Operação", datetime.now())
            f_forn = c2.selectbox("Fornecedor", ["JBS", "RIO MARIA", "BOI BRANCO S.A", "OUTROS"])
            f_peso = c3.number_input("Peso Total Entrada (Kg)", min_value=0.0, step=0.1)
            
            st.write("**Digite os pesos reais obtidos de cada corte (Kg):**")
            # Lista baseada na sua planilha de desossa
            cortes_lista = [
                "COXAO MOLE BOV KG PROD", "CONTRAFILE BOV KG PROD", "COXAO DURO BOV KG PROD",
                "PATINHO BOV KG PROD", "MUSCULO TRASEIRO BOV KG PROD", "CORACAO ALCATRA BOV KG PROD",
                "CAPA CONTRA FILE BOV KG PROD", "LOMBO PAULISTA BOV KG PROD", "FRALDA BOV KG PROD",
                "FILE MIGNON BOV PROD PÇ±1.6 KG", "MAMINHA BOV KG PROD", "PICANHA BOV KG PROD",
                "COSTELINHA CONTRA FILE KG PROD", "SEBO BOV KG PROD", "OSSO BOV KG PROD", 
                "OSSO BOV SERRA KG PROD", "ARANHA BOV KG PROD", "FILEZINHO MOCOTO KG PROD"
            ]
            
            res_valores = {"DATA": f_data, "FORNECEDOR": f_forn, "ENTRADA": f_peso}
            col_esq, col_dir = st.columns(2)
            for i, corte in enumerate(cortes_lista):
                with (col_esq if i % 2 == 0 else col_dir):
                    res_valores[corte] = st.number_input(f"{corte}", min_value=0.0, step=0.1)
            
            if st.form_submit_button("Salvar Desossa no Histórico"):
                if f_peso > 0:
                    salvar_dados_desossa(res_valores)
                else:
                    st.error("O peso total de entrada é obrigatório para calcular o rendimento.")

    # --- BLOCO 3: ANÁLISE DE RENDIMENTO POR FORNECEDOR ---
    if os.path.exists("DESOSSA_HISTORICO.csv"):
        st.markdown("---")
        st.subheader("📊 Performance de Rendimento por Frigorífico")
        df_h = pd.read_csv("DESOSSA_HISTORICO.csv")
        
        # Criar colunas de percentual (%) automaticamente para cada corte
        colunas_cortes = [c for c in df_h.columns if c not in ["DATA", "FORNECEDOR", "ENTRADA"]]
        for c in colunas_cortes:
            df_h[f"{c} (%)"] = (df_h[c] / df_h['ENTRADA']) * 100
        
        # Média por Fornecedor
        df_resumo = df_h.groupby("FORNECEDOR").mean(numeric_only=True).reset_index()
        
        tab_tabela, tab_grafico = st.tabs(["📋 Tabela de Médias", "📈 Gráfico Comparativo"])
        
        with tab_tabela:
            st.dataframe(
                df_resumo[["FORNECEDOR"] + [c for c in df_resumo.columns if "(%)" in c]], 
                use_container_width=True, hide_index=True
            )
        
        with tab_grafico:
            corte_sel = st.selectbox("Selecione o corte para comparar o rendimento real:", colunas_cortes)
            fig_comp = px.bar(
                df_resumo, x='FORNECEDOR', y=f"{corte_sel} (%)", 
                color='FORNECEDOR', text_auto='.2f',
                title=f"Rendimento Médio: {corte_sel} (%)",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            st.plotly_chart(fig_comp, use_container_width=True)

    st.markdown("---")

    # --- BLOCO 4: SIMULADOR E ESTOQUE ATUAL ---
    st.subheader("🥩 Simulador de Carga e Posição de Estoque")
    tab_sim, tab_est = st.tabs(["🧮 Simulador de Carga (Estimado)", "📦 Top Estoque Atual"])
    
    with tab_sim:
        p_entrada = st.number_input("Peso para Simulação (Kg):", value=16000.0, step=500.0)
        dados_rend = {
            "Corte": ["OSSO BOV KG PROD", "COXAO MOLE BOV KG PROD", "CONTRAFILE BOV KG PROD", "COXAO DURO BOV KG PROD", "CARNE BOV PROD (LIMPEZA)", "PATINHO BOV KG PROD", "MUSCULO TRASEIRO BOV KG PROD", "CORACAO ALCATRA BOV KG PROD", "CAPA CONTRA FILE BOV KG PROD", "LOMBO PAULISTA BOV KG PROD", "OSSO BOV SERRA KG PROD", "FRALDA BOV KG PROD", "FILE MIGNON BOV PROD PÇ±1.6 KG", "MAMINHA BOV KG PROD", "PICANHA BOV KG PROD", "COSTELINHA CONTRA FILE KG PROD", "SEBO BOV KG PROD", "OSSO PATINHO BOV KG PROD", "ARANHA BOV KG PROD", "FILEZINHO MOCOTO KG PROD"],
            "Rendimento (%)": [14.56, 13.4, 10.74, 9.32, 8.04, 7.88, 6.68, 5.42, 3.64, 3.60, 3.07, 2.65, 2.37, 2.27, 1.71, 1.69, 1.38, 0.76, 0.63, 0.19]
        }
        df_sim = pd.DataFrame(dados_rend)
        df_sim['Previsão (Kg)'] = (df_sim['Rendimento (%)'] / 100) * p_entrada
        st.dataframe(df_sim.sort_values('Previsão (Kg)', ascending=False), use_container_width=True, hide_index=True)
        st.success(f"Volume Total Estimado: {formatar_br(df_sim['Previsão (Kg)'].sum())} Kg")

    with tab_est:
        df_top20 = df.nlargest(20, 'QTESTGER').sort_values('QTESTGER', ascending=True)
        fig_est = px.bar(df_top20, x='QTESTGER', y='Descrição', orientation='h', 
                         color='QTESTGER', color_continuous_scale='Greens', height=550, text_auto='.2f')
        st.plotly_chart(fig_est, use_container_width=True)

    # Rodapé informativo
    st.info(f"Dashboard Seridoense | Rede Interna: http://192.168.1.19:8502")