import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página para ocupar a tela toda
st.set_page_config(page_title="Controle de Estoque - Frigorífico", layout="wide")

st.title("🥩 Dashboard de Estoque - Setor Fiscal")
st.markdown("---")

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Função para carregar dados com cache
@st.cache_data(show_spinner="Carregando base de dados...")
def carregar_dados():
    # Lê o arquivo diretamente do seu repositório GitHub
    df = pd.read_excel("BASE_PILOTO.xlsx")
    df.columns = df.columns.str.strip()
    df = df[pd.to_numeric(df['Código'], errors='coerce').notnull()]
    
    df['Filial'] = df['Filial'].astype(int)
    df['Código'] = df['Código'].astype(int)
    
    # Definição de Matéria-Prima (conforme conversamos)
    codigos_mp = [1228, 6009, 18765, 6010]
    df['Categoria'] = df['Código'].apply(lambda x: 'Matéria-Prima' if x in codigos_mp else 'Cortes/Outros')
    df['Valor Total (R$)'] = df['Estoque'] * df['Custo contábil']
    return df

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Painel de Controle")

# BOTÃO DE ATUALIZAR (Limpa o cache)
if st.sidebar.button("🔄 Atualizar Dados"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")

try:
    df_completo = carregar_dados()

    # Filtros para os usuários
    categoria_selecionada = st.sidebar.multiselect(
        "Filtrar Categorias:",
        options=df_completo['Categoria'].unique(),
        default=df_completo['Categoria'].unique()
    )
    df = df_completo[df_completo['Categoria'].isin(categoria_selecionada)]

    # --- KPIs (Indicadores) ---
    col1, col2, col3, col4 = st.columns(4)
    total_kg = df['Estoque'].sum()
    total_fin = df['Valor Total (R$)'].sum()
    estoque_mp = df_completo[df_completo['Categoria'] == 'Matéria-Prima']['Estoque'].sum()

    col1.metric("Estoque Selecionado (kg)", f"{total_kg:,.2f} kg".replace(",", "X").replace(".", ",").replace("X", "."))
    col2.metric("Valor em estoque", formatar_moeda(total_fin))
    col3.metric("Estoque MATÉRIA-PRIMA", f"{estoque_mp:,.2f} kg".replace(",", "X").replace(".", ",").replace("X", "."))
    col4.metric("Qtd Itens", len(df))

    st.markdown("---")

    # --- GRÁFICO DE BARRAS GRANDE (Ocupando a largura total) ---
    st.subheader("📊 Volume Total por Item (Top 20)")
    # Selecionando os 20 maiores para não poluir demais, mas com gráfico grande
    top_n = df.nlargest(20, 'Estoque').sort_values('Estoque', ascending=True)
    top_n['Rótulo_Qtd'] = top_n['Estoque'].apply(lambda x: f"{x:,.2f} kg".replace(",", "X").replace(".", ",").replace("X", "."))
    
    fig_vol = px.bar(
        top_n, 
        x='Estoque', 
        y='Descrição', 
        orientation='h', 
        text='Rótulo_Qtd',
        color='Categoria', 
        color_discrete_map={'Matéria-Prima': '#960018', 'Cortes/Outros': '#3274ad'},
        height=700 # Altura aumentada para o gráfico ficar grande
    )
    fig_vol.update_layout(margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig_vol, use_container_width=True)

    st.markdown("---")

    # --- GRÁFICO DE PIZZA E TABELA ---
    col_abaixo_1, col_abaixo_2 = st.columns([1, 2])
    
    with col_abaixo_1:
        st.subheader("💰 Divisão Financeira")
        fig_pie = px.pie(df, values='Valor Total (R$)', names='Categoria', hole=0.4,
                         color='Categoria', color_discrete_map={'Matéria-Prima': '#960018', 'Cortes/Outros': '#3274ad'})
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_abaixo_2:
        st.subheader("📋 Detalhes do Estoque")
        st.dataframe(df.style.format({
            'Filial': '{}', 'Código': '{}', 'Estoque': '{:.2f} kg', 'Custo contábil': 'R$ {:.2f}', 'Valor Total (R$)': 'R$ {:.2f}'
        }), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Erro ao carregar os dados: {e}")
    st.info("Certifique-se de que o arquivo 'BASE_PILOTO.xlsx' foi enviado para o seu GitHub.")
else:
    # Mensagem que aparece enquanto o arquivo não é carregado
    st.info("👋 Bem-vindo! Por favor, utilize a barra lateral à esquerda para carregar o seu arquivo 'BASE_PILOTO.xlsx'.")