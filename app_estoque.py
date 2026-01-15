import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Controle de Estoque - Frigorífico", layout="wide")

st.title("🥩 Dashboard de Estoque - Setor Fiscal")
st.markdown("---")

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

@st.cache_data(show_spinner="Sincronizando bases de dados...")
def carregar_dados():
    # 1. Lê a base de estoque
    df = pd.read_excel("BASE_PILOTO.xlsx")
    df.columns = df.columns.str.strip()
    
    # 2. Lê a nova planilha de classificação (Traseiro/Dianteiro)
    df_class = pd.read_excel("CLASS_D_OU_T.xlsx")
    df_class.columns = df_class.columns.str.strip()
    
    # 3. Faz o cruzamento (Merge) dos dados pelo Código
    df = pd.merge(df, df_class[['Código', 'Classificação']], on='Código', how='left')
    
    # Preenche o que não encontrar como 'Não Classificado'
    df['Classificação'] = df['Classificação'].fillna('Não Classificado')
    
    df = df[pd.to_numeric(df['Código'], errors='coerce').notnull()]
    df['Filial'] = df['Filial'].astype(int)
    df['Código'] = df['Código'].astype(int)
    
    codigos_mp = [1228, 6009, 18765, 6010]
    df['Categoria'] = df['Código'].apply(lambda x: 'Matéria-Prima' if x in codigos_mp else 'Cortes/Outros')
    df['Valor Total (R$)'] = df['Estoque'] * df['Custo contábil']
    return df

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Painel de Controle")
if st.sidebar.button("🔄 Atualizar Dados"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")

try:
    df_completo = carregar_dados()

    # NOVO FILTRO: Classificação de Peça
    peca_selecionada = st.sidebar.multiselect(
        "Selecione a Peça (Traseiro/Dianteiro):",
        options=df_completo['Classificação'].unique(),
        default=df_completo['Classificação'].unique()
    )

    categoria_selecionada = st.sidebar.multiselect(
        "Filtrar Categorias:",
        options=df_completo['Categoria'].unique(),
        default=df_completo['Categoria'].unique()
    )
    
    # Aplicando os filtros
    df = df_completo[
        (df_completo['Classificação'].isin(peca_selecionada)) & 
        (df_completo['Categoria'].isin(categoria_selecionada))
    ]

    # ASSINATURA
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ✍️ Créditos")
    st.sidebar.write("**Desenvolvido por:** Paulo")
    st.sidebar.write("**Setor:** Fiscal")
    st.sidebar.caption("Versão 1.1 | Classificação Traseiro/Dianteiro")

    # --- KPIs ---
    col1, col2, col3, col4 = st.columns(4)
    total_kg = df['Estoque'].sum()
    total_fin = df['Valor Total (R$)'].sum()
    
    col1.metric("Estoque Filtro (kg)", f"{total_kg:,.2f} kg".replace(",", "X").replace(".", ",").replace("X", "."))
    col2.metric("Valor em estoque", formatar_moeda(total_fin))
    col3.metric("Itens no Filtro", len(df))
    col4.metric("Total Matéria-Prima", f"{df_completo[df_completo['Categoria'] == 'Matéria-Prima']['Estoque'].sum():,.2f} kg".replace(",", "X").replace(".", ",").replace("X", "."))

    st.markdown("---")

    # --- GRÁFICO DE BARRAS (Volume por Peça) ---
    st.subheader("📊 Volume por Item e Classificação")
    top_n = df.nlargest(20, 'Estoque').sort_values('Estoque', ascending=True)
    
    fig_vol = px.bar(
        top_n, x='Estoque', y='Descrição', orientation='h', 
        color='Classificação', # Agora as cores mostram se é Traseiro ou Dianteiro
        color_discrete_map={'TRASEIRO': '#960018', 'DIANTEIRO': '#3274ad', 'EXTRA': '#2ecc71'},
        height=600 
    )
    st.plotly_chart(fig_vol, use_container_width=True)

    st.markdown("---")

    # --- TABELA DETALHADA ---
    st.subheader("📋 Detalhes do Estoque com Classificação")
    st.dataframe(
        df[['Filial', 'Código', 'Descrição', 'Classificação', 'Categoria', 'Estoque', 'Valor Total (R$)']].style.format({
            'Filial': '{}', 'Código': '{}', 'Estoque': '{:.2f} kg', 'Valor Total (R$)': 'R$ {:.2f}'
        }), 
        use_container_width=True, hide_index=True
    )

except Exception as e:
    st.error(f"Erro ao processar as planilhas: {e}")
else:
    # Mensagem que aparece enquanto o arquivo não é carregado
    st.info("👋 Bem-vindo! Por favor, utilize a barra lateral à esquerda para carregar o seu arquivo 'BASE_PILOTO.xlsx'.")