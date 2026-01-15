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
    df = pd.read_excel("BASE_PILOTO.xlsx")
    df.columns = df.columns.str.strip()
    
    df_class = pd.read_excel("CLASS_D_OU_T.xlsx")
    df_class.columns = df_class.columns.str.strip()
    
    # Cruzamento de dados
    df = pd.merge(df, df_class[['Código', 'Classificação']], on='Código', how='left')
    df['Classificação'] = df['Classificação'].fillna('Não Classificado')
    
    df = df[pd.to_numeric(df['Código'], errors='coerce').notnull()]
    df['Filial'] = df['Filial'].astype(int)
    df['Código'] = df['Código'].astype(int)
    
    # Mantendo sua regra de categoria original
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

    # Filtros
    peca_selecionada = st.sidebar.multiselect(
        "Selecione a classificação do Corte/Peça:",
        options=sorted(df_completo['Classificação'].unique()),
        default=df_completo['Classificação'].unique()
    )

    df = df_completo[df_completo['Classificação'].isin(peca_selecionada)]

    # ASSINATURA
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ✍️ Créditos")
    st.sidebar.write("**Desenvolvido por:** Paulo")
    st.sidebar.write("**Setor:** Fiscal")
    st.sidebar.caption("Versão 1.2 | Base de Classificação Atualizada")

    # --- KPIs ---
    col1, col2, col3, col4 = st.columns(4)
    total_kg = df['Estoque'].sum()
    total_fin = df['Valor Total (R$)'].sum()
    
    col1.metric("Estoque Filtro (kg)", f"{total_kg:,.2f} kg".replace(",", "X").replace(".", ",").replace("X", "."))
    col2.metric("Valor em estoque", formatar_moeda(total_fin))
    col3.metric("Itens no Filtro", len(df))
    col4.metric("Qtd Total Itens", len(df_completo))

    st.markdown("---")

    # --- GRÁFICOS INTERMEDIÁRIOS (Pizza Lado a Lado) ---
    col_p1, col_p2 = st.columns(2)
    
    with col_p1:
        st.subheader("⚖️ Peso por Classificação")
        fig_pie_kg = px.pie(df, values='Estoque', names='Classificação', hole=0.4,
                            color='Classificação',
                            color_discrete_map={
                                'TRASEIRO': '#960018', 
                                'DIANTEIRO': '#3274ad', 
                                'EXTRA': '#2ecc71',
                                'MATERIA PRIMA': '#f39c12',
                                'SOL': '#9b59b6'
                            })
        st.plotly_chart(fig_pie_kg, use_container_width=True)

    with col_p2:
        st.subheader("💰 Valor por Classificação")
        fig_pie_val = px.pie(df, values='Valor Total (R$)', names='Classificação', hole=0.4,
                             color='Classificação',
                             color_discrete_map={
                                 'TRASEIRO': '#960018', 
                                 'DIANTEIRO': '#3274ad', 
                                 'EXTRA': '#2ecc71',
                                 'MATERIA PRIMA': '#f39c12',
                                 'SOL': '#9b59b6'
                             })
        st.plotly_chart(fig_pie_val, use_container_width=True)

    st.markdown("---")

    # --- GRÁFICO DE BARRAS GRANDE ---
    st.subheader("📊 Volume Detalhado (Top 20)")
    top_n = df.nlargest(20, 'Estoque').sort_values('Estoque', ascending=True)
    top_n['Rótulo_Qtd'] = top_n['Estoque'].apply(lambda x: f"{x:,.2f} kg".replace(",", "X").replace(".", ",").replace("X", "."))
    
    fig_vol = px.bar(
        top_n, x='Estoque', y='Descrição', orientation='h', text='Rótulo_Qtd',
        color='Classificação',
        color_discrete_map={
            'TRASEIRO': '#960018', 
            'DIANTEIRO': '#3274ad', 
            'EXTRA': '#2ecc71',
            'MATERIA PRIMA': '#f39c12'
        },
        height=600 
    )
    st.plotly_chart(fig_vol, use_container_width=True)

    # --- TABELA ---
    with st.expander("Ver Tabela Completa"):
        st.dataframe(df.style.format({'Estoque': '{:.2f} kg', 'Valor Total (R$)': 'R$ {:.2f}'}), use_container_width=True)

except Exception as e:
    st.error(f"Erro: {e}")
else:
    # Mensagem que aparece enquanto o arquivo não é carregado
    st.info("👋 Bem-vindo! Por favor, utilize a barra lateral à esquerda para carregar o seu arquivo 'BASE_PILOTO.xlsx'.")