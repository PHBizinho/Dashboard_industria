import pandas as pd
import oracledb
import streamlit as st

def carregar_dados_completos():
    # 1. Conectar ao Banco de Dados para pegar o Estoque Real (Filial 3)
    conn_params = {
        "user": "NUTRICAO",
        "password": "nutr1125mmf",
        "dsn": "192.168.222.20:1521/WINT"
    }
    
    try:
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

        # 2. Carregar os Nomes do seu novo Excel
        df_nomes = pd.read_excel("BASE_DESCRICOES_PRODUTOS.xlsx")
        
        # 3. Unir as duas informações (Merge)
        # O Python vai olhar o código no banco e buscar o nome no seu Excel
        df_final = pd.merge(df_estoque, df_nomes, on="Código", how="left")
        
        # Reorganizar colunas para a Descrição aparecer logo após o Código
        colunas = ['Código', 'Descrição', 'Estoque', 'Estoque Disponível', 
                   'Venda Mês', 'Venda Mês 1', 'Venda Mês 2', 'Venda Mês 3']
        return df_final[colunas]

    except Exception as e:
        st.error(f"Erro na integração: {e}")
        return None

# Chamar a função no corpo do seu App Streamlit
df_vendas = carregar_dados_completos()