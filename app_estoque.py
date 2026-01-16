import streamlit as st
import oracledb
import pandas as pd
import os

# 1. CONFIGURAÇÃO DO AMBIENTE (CLIENTE ORACLE)
# Isso deve rodar antes de qualquer tentativa de conexão
if 'oracle_client_initialized' not in st.session_state:
    try:
        # Caminho da pasta que você extraiu no C:
        caminho_client = r"C:\oracle\instantclient_19_29"
        oracledb.init_oracle_client(lib_dir=caminho_client)
        st.session_state['oracle_client_initialized'] = True
        print("Cliente Oracle ativado com sucesso!")
    except Exception as e:
        st.error(f"Erro ao carregar o Instant Client da Oracle: {e}")

# 2. FUNÇÃO PARA BUSCAR DADOS (BANCO + EXCEL)
def carregar_dados_completos():
    conn_params = {
        "user": "NUTRICAO",
        "password": "nutr1125mmf",
        "dsn": "192.168.222.20:1521/WINT"
    }
    
    try:
        # Conexão com o Banco de Dados WinThor
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
        # Carrega o estoque do banco para um DataFrame
        df_estoque = pd.read_sql(query_estoque, conn)
        conn.close()

        # Carregar a sua planilha de nomes
        # Ela deve estar na mesma pasta PILOTO
        df_nomes = pd.read_excel("BASE_DESCRICOES_PRODUTOS.xlsx")
        
        # Forçamos o nome das colunas do Excel para evitar o erro de 'Descrição' not in index
        df_nomes.columns = ['Código', 'Descrição'] 

        # Une (Merge) os dados do banco com os nomes do seu Excel
        df_final = pd.merge(df_estoque, df_nomes, on="Código", how="left")
        
        # Se um código do banco não existir no seu Excel, ele avisa
        df_final['Descrição'] = df_final['Descrição'].fillna('PRODUTO NÃO CADASTRADO NO EXCEL')
        
        # Organiza a ordem das colunas para o Dashboard
        colunas_ordenadas = [
            'Código', 'Descrição', 'Estoque', 'Estoque Disponível', 
            'Venda Mês', 'Venda Mês 1', 'Venda Mês 2', 'Venda Mês 3'
        ]
        return df_final[colunas_ordenadas]

    except Exception as e:
        st.error(f"Erro na conexão ou processamento: {e}")
        return None

# 3. INTERFACE DO DASHBOARD (STREAMLIT)
st.set_page_config(page_title="Dashboard de Estoque - Filial 3", layout="wide")

st.title("📊 Controle de Estoque Real - Setor Fiscal")
st.markdown("---")

# Botão para atualizar os dados manualmente se precisar
if st.button('🔄 Atualizar Dados do WinThor'):
    st.cache_data.clear()

# Chamada da função
df_vendas = carregar_dados_completos()

if df_vendas is not None:
    st.success(f"Dados da Filial 3 carregados! {len(df_vendas)} produtos encontrados.")
    
    # Exibe a tabela formatada
    st.dataframe(
        df_vendas, 
        use_container_width=True,
        hide_index=True
    )
else:
    st.warning("Aguardando conexão com o banco de dados...")