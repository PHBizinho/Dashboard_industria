import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Controle de Estoque - Frigorífico", layout="wide")

st.title("🥩 Dashboard de Estoque Seridoense - Setor Fiscal")
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
    
    # Cálculo de Representatividade
    total_kg_geral = df['Estoque'].sum()
    total_val_geral = df['Valor Total (R$)'].sum()
    df['% Peso'] = (df['Estoque'] / total_kg_geral) * 100
    df['% Valor'] = (df['Valor Total (R$)'] / total_val_geral) * 100
    
    return df

# --- SIDEBAR ---
st.sidebar.header("⚙️ Painel de Controle")
if st.sidebar.button("🔄 Atualizar Dados"):
    st.cache_data.clear()
    st.rerun()

try:
    df_completo = carregar_dados()
    peca_selecionada = st.sidebar.multiselect(
        "**Selecione a(as) classificação(ões):**",
        options=sorted(df_completo['Classificação'].unique()),
        default=df_completo['Classificação'].unique()
    )
    df = df_completo[df_completo['Classificação'].isin(peca_selecionada)]

    st.sidebar.markdown("---")
    st.sidebar.markdown("### ✍️ Créditos")
    st.sidebar.write(f"**Desenvolvido por:** Paulo Henrique")
    st.sidebar.write("Setor Fiscal")

    # --- KPIs ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Estoque Selecionado (kg)", f"{df['Estoque'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c2.metric("Valor em estoque", formatar_moeda(df['Valor Total (R$)'].sum()))
    c3.metric("Itens no Filtro", len(df))
    total_mp = df_completo[df_completo['Categoria'] == 'Matéria-Prima']['Estoque'].sum()
    c4.metric("Total Matéria-Prima (kg)", f"{total_mp:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    st.markdown("---")

    # --- 1. VOLUME DETALHADO (TOP 20) ---
    st.subheader("📊 Volume Detalhado por Corte (Top 20)")
    top_n = df.nlargest(20, 'Estoque').sort_values('Estoque', ascending=True)
    top_n['Rótulo'] = top_n['Estoque'].apply(lambda x: f"<b>{x:,.2f} kg</b>".replace(",", "X").replace(".", ",").replace("X", "."))
    
    fig_vol = px.bar(
        top_n, x='Estoque', y='Descrição', orientation='h', text='Rótulo',
        color='Classificação',
        color_discrete_map={'TRASEIRO': '#960018', 'DIANTEIRO': '#3274ad', 'EXTRA': '#2ecc71', 'MATERIA PRIMA': '#f39c12', 'SOL': '#9b59b6', 'MOIDA': '#1abc9c'},
        height=700 
    )
    fig_vol.update_traces(textposition='auto', textfont=dict(color='black', size=13))
    st.plotly_chart(fig_vol, use_container_width=True)

    st.markdown("---")

    # --- 2. ANÁLISE DE PARETO FINANCEIRO ---
    st.subheader("🎯 Análise de Pareto: Impacto Financeiro por Corte")
    df_pareto = df.nlargest(15, 'Valor Total (R$)')
    fig_pareto = px.bar(
        df_pareto, x='Descrição', y='% Valor',
        text=df_pareto['% Valor'].apply(lambda x: f"<b>{x:.1f}%</b>"),
        color='% Valor', color_continuous_scale='Reds'
    )
    fig_pareto.update_traces(textposition='outside', textfont=dict(color='black', size=12))
    st.plotly_chart(fig_pareto, use_container_width=True)

    st.markdown("---")

    # --- 3. GRÁFICOS DE PIZZA (RECUPERADOS) ---
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.subheader("⚖️ Distribuição de Peso")
        fig1 = px.pie(df, values='Estoque', names='Classificação', hole=0.4, 
                      color='Classificação', color_discrete_map={'TRASEIRO': '#960018', 'DIANTEIRO': '#3274ad', 'EXTRA': '#2ecc71', 'MATERIA PRIMA': '#f39c12', 'SOL': '#9b59b6'})
        st.plotly_chart(fig1, use_container_width=True)
    with col_p2:
        st.subheader("💰 Distribuição Financeira")
        fig2 = px.pie(df, values='Valor Total (R$)', names='Classificação', hole=0.4, 
                      color='Classificação', color_discrete_map={'TRASEIRO': '#960018', 'DIANTEIRO': '#3274ad', 'EXTRA': '#2ecc71', 'MATERIA PRIMA': '#f39c12', 'SOL': '#9b59b6'})
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")

    # --- 4. TABELA DETALHADA ---
    st.subheader("📋 Detalhes com Representatividade (% Pareto)")
    colunas_exibir = ['Código', 'Descrição', 'Classificação', 'Estoque', '% Peso', 'Valor Total (R$)', '% Valor']
    st.dataframe(
        df[colunas_exibir].sort_values('% Valor', ascending=False).style.format({
            'Código': '{}', 'Estoque': '{:.2f} kg', '% Peso': '{:.2f}%',
            'Valor Total (R$)': 'R$ {:.2f}', '% Valor': '{:.2f}%'
        }), 
        use_container_width=True, hide_index=True
    )

except Exception as e:
    st.error(f"Erro ao processar dados: {e}")
else:
    # Mensagem que aparece enquanto o arquivo não é carregado
    st.info("👋 Bem-vindo! Por favor, utilize a barra lateral à esquerda para carregar o seu arquivo 'BASE_PILOTO.xlsx'.")