import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Controle de Estoque - Frigorífico", layout="wide")

st.title("🥩 Dashboard de Estoque - Setor Fiscal")
st.markdown("---")

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

@st.cache_data(show_spinner="Sincronizando bases...")
def carregar_dados():
    df = pd.read_excel("BASE_PILOTO.xlsx")
    df.columns = df.columns.str.strip()
    
    df_class = pd.read_excel("CLASS_D_OU_T.xlsx")
    df_class.columns = df_class.columns.str.strip()
    
    df = pd.merge(df, df_class[['Código', 'Classificação']], on='Código', how='left')
    df['Classificação'] = df['Classificação'].fillna('Não Classificado')
    
    df = df[pd.to_numeric(df['Código'], errors='coerce').notnull()]
    df['Filial'] = df['Filial'].astype(int)
    df['Código'] = df['Código'].astype(int)
    
    codigos_mp = [1228, 6009, 18765, 6010]
    df['Categoria'] = df['Código'].apply(lambda x: 'Matéria-Prima' if x in codigos_mp else 'Cortes/Outros')
    df['Valor Total (R$)'] = df['Estoque'] * df['Custo contábil']
    return df

# --- SIDEBAR ---
st.sidebar.header("⚙️ Painel de Controle")
if st.sidebar.button("🔄 Atualizar Dados"):
    st.cache_data.clear()
    st.rerun()

try:
    df_completo = carregar_dados()
    peca_selecionada = st.sidebar.multiselect(
        "Selecione a Peça:",
        options=sorted(df_completo['Classificação'].unique()),
        default=df_completo['Classificação'].unique()
    )
    df = df_completo[df_completo['Classificação'].isin(peca_selecionada)]

    st.sidebar.markdown("---")
    st.sidebar.markdown("### ✍️ Créditos")
    st.sidebar.write(f"**Desenvolvido por:** Paulo")
    st.sidebar.write("**Setor:** Fiscal")

    # --- KPIs ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Estoque (kg)", f"{df['Estoque'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c2.metric("Valor Total", formatar_moeda(df['Valor Total (R$)'].sum()))
    c3.metric("Itens", len(df))
    c4.metric("Total MP (kg)", f"{df_completo[df_completo['Categoria'] == 'Matéria-Prima']['Estoque'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    st.markdown("---")

    # --- GRÁFICO DE BARRAS COM NÚMEROS ESCUROS ---
    st.subheader("📊 Volume Detalhado (Top 20)")
    top_n = df.nlargest(20, 'Estoque').sort_values('Estoque', ascending=True)
    top_n['Rótulo'] = top_n['Estoque'].apply(lambda x: f"<b>{x:,.2f} kg</b>".replace(",", "X").replace(".", ",").replace("X", "."))
    
    fig_vol = px.bar(
        top_n, x='Estoque', y='Descrição', orientation='h', text='Rótulo',
        color='Classificação',
        color_discrete_map={'TRASEIRO': '#960018', 'DIANTEIRO': '#3274ad', 'EXTRA': '#2ecc71', 'MATERIA PRIMA': '#f39c12', 'SOL': '#9b59b6'},
        height=700 
    )

    # AJUSTE PARA OS NÚMEROS FICAREM ESCUROS E VISÍVEIS
    fig_vol.update_traces(
        textposition='auto',
        textfont=dict(color='black', size=14) # Define a cor preta e aumenta um pouco o tamanho
    )
    
    st.plotly_chart(fig_vol, use_container_width=True)

    # --- PIZZAS ---
    st.markdown("---")
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.subheader("⚖️ Peso por Peça")
        fig1 = px.pie(df, values='Estoque', names='Classificação', hole=0.4, color='Classificação',
                      color_discrete_map={'TRASEIRO': '#960018', 'DIANTEIRO': '#3274ad', 'EXTRA': '#2ecc71', 'MATERIA PRIMA': '#f39c12'})
        st.plotly_chart(fig1, use_container_width=True)
    with col_p2:
        st.subheader("💰 Valor por Peça")
        fig2 = px.pie(df, values='Valor Total (R$)', names='Classificação', hole=0.4, color='Classificação',
                      color_discrete_map={'TRASEIRO': '#960018', 'DIANTEIRO': '#3274ad', 'EXTRA': '#2ecc71', 'MATERIA PRIMA': '#f39c12'})
        st.plotly_chart(fig2, use_container_width=True)

except Exception as e:
    st.error(f"Erro: {e}")
else:
    # Mensagem que aparece enquanto o arquivo não é carregado
    st.info("👋 Bem-vindo! Por favor, utilize a barra lateral à esquerda para carregar o seu arquivo 'BASE_PILOTO.xlsx'.")