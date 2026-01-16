import streamlit as st
import oracledb
import pandas as pd
import os

# 1. FORÇAR INICIALIZAÇÃO DO CLIENTE ORACLE (Deve ser o primeiro bloco)
if 'oracle_client_initialized' not in st.session_state:
    try:
        # Ajuste o caminho abaixo se a sua pasta tiver um número de versão diferente
        caminho_client = r"C:\oracle\instantclient_23_0"
        oracledb.init_oracle_client(lib_dir=caminho_client)
        st.session_state['oracle_client_initialized'] = True
        print("Cliente Oracle ativado com sucesso!")
    except Exception as e:
        st.error(f"Erro ao carregar Instant Client: {e}")

# 2. FUNÇÃO DE CARREGAMENTO
def carregar_dados_completos():
    conn_params = {
        "user": "NUTRICAO",
        "password": "nutr1125mmf",
        "dsn": "192.168.222.20:1521/WINT"
    }
    
    try:
        # Agora a conexão usará o "Thick Mode" automaticamente
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

        df_nomes = pd.read_excel("BASE_DESCRICOES_PRODUTOS.xlsx")
        df_final = pd.merge(df_estoque, df_nomes, on="Código", how="left")
        
        colunas = ['Código', 'Descrição', 'Estoque', 'Estoque Disponível', 
                   'Venda Mês', 'Venda Mês 1', 'Venda Mês 2', 'Venda Mês 3']
        return df_final[colunas]

    except Exception as e:
        st.error(f"Erro na conexão com o banco WinThor: {e}")
        return None

# 3. EXECUÇÃO
df_vendas = carregar_dados_completos()

if df_vendas is not None:
    st.success("Dados carregados com sucesso!")
    st.dataframe(df_vendas)