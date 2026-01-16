import streamlit as st
import oracledb
import pandas as pd
import os

# 1. CONFIGURAÇÃO DO AMBIENTE (CLIENTE ORACLE PARA WINDOWS)
if 'oracle_client_initialized' not in st.session_state:
    try:
        # Caminho exato que você confirmou no seu C:
        caminho_client = r"C:\oracle\instantclient_19_29"
        
        # Inicializa o modo "Thick" necessário para o WinThor
        oracledb.init_oracle_client(lib_dir=caminho_client)
        
        st.session_state['oracle_client_initialized'] = True
        print("Cliente Oracle Windows ativado com sucesso!")
    except Exception as e:
        st.error(f"Erro ao carregar o Instant Client no Windows: {e}")

# 2. FUNÇÃO PARA BUSCAR DADOS (BANCO + EXCEL)
def carregar_dados_completos():
    conn_params = {
        "user": "NUTRICAO",
        "password": "nutr1125mmf",
        "dsn": "192.168.222.20:1521/WINT"
    }
    
    try:
        # Conexão com o Banco de Dados
        conn = oracledb.connect(**conn_params)
        
        query_estoque = """
        SELECT 
            CODPROD AS "Código",
            QTESTGER AS "Estoque",
            QTRESERV AS "Reservado",
            (QTESTGER - QTRESERV - QTBLOQUEADA) AS "Estoque Disponível",
            QTVENDMES AS "Venda Mês",
            QTVENDMES1 AS "Venda Mês 1",
            QTVENDMES2 AS "Venda Mês 2",
            QTVENDMES3 AS "Venda Mês 3"
        FROM MMFRIOS.PCEST
        WHERE CODFILIAL = 3 AND QTESTGER > 0
        """
        df_estoque = pd.read_sql(query_estoque, conn)
        conn.close()

        # Carregar a sua planilha de nomes (PILOTO)
        df_nomes = pd.read_excel("BASE_DESCRICOES_PRODUTOS.xlsx")
        
        # Ajusta as colunas do Excel para garantir o cruzamento
        df_nomes.columns = ['Código', 'Descrição'] 

        # Une Estoque + Nomes
        df_final = pd.merge(df_estoque, df_nomes, on="Código", how="left")
        
        # Preenchimento para códigos novos ou não listados no seu Excel
        df_final['Descrição'] = df_final['Descrição'].fillna('PRODUTO NÃO CADASTRADO NO EXCEL')
        
        colunas_ordenadas = [
            'Código', 'Descrição', 'Estoque', 'Estoque Disponível', 
            'Venda Mês', 'Venda Mês 1', 'Venda Mês 2', 'Venda Mês 3'
        ]
        return df_final[colunas_ordenadas]

    except Exception as e:
        st.error(f"Erro na conexão ou processamento: {e}")
        return None

# 3. INTERFACE DO DASHBOARD
st.set_page_config(page_title="Estoque Filial 3", layout="wide")
st.title("📊 Controle de Estoque Real - Setor Fiscal")
st.markdown("---")

df_vendas = carregar_dados_completos()

if df_vendas is not None:
    st.success(f"Dados carregados! {len(df_vendas)} itens monitorados na Filial 3.")
    st.dataframe(df_vendas, use_container_width=True, hide_index=True)