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
    df['Código'] = df['Código'].astype(int)
    
    # Cálculos de Vendas e Estoque Real
    df['Média Vendas (3m)'] = df[['Venda Mês 1', 'Venda Mês 2', 'Venda Mês 3']].mean(axis=1)
    df['Estoque Disponível'] = df['Estoque'] - df['Reservado'] - df['Qt.Avaria']
    
    # Valor Total e Perda Financeira
    df['Valor Total (R$)'] = df['Estoque'] * df['Custo contábil']
    df['Valor Avaria (R$)'] = df['Qt.Avaria'] * df['Custo contábil']
    
    total_val_geral = df['Valor Total (R$)'].sum()
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
    c1.metric("Estoque Total (kg)", f"{df['Estoque'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c2.metric("Total Reservado (kg)", f"{df['Reservado'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    # KPI de Avaria com destaque para perda
    total_avaria = df['Qt.Avaria'].sum()
    valor_avaria = df['Valor Avaria (R$)'].sum()
    c3.metric("Qtde Avaria (kg)", f"{total_avaria:,.2f} kg", delta=formatar_moeda(valor_avaria), delta_color="inverse")
    
    c4.metric("Valor Total em Estoque", formatar_moeda(df['Valor Total (R$)'].sum()))

    st.markdown("---")

    # --- 1. VOLUME DETALHADO (TOP 20) ---
    st.subheader("📊 Volume em Estoque (Top 20)")
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
    st.subheader("🎯 Impacto Financeiro (R$) por Corte")
    df_pareto = df.nlargest(15, 'Valor Total (R$)')
    fig_pareto = px.bar(
        df_pareto, x='Descrição', y='% Valor',
        text=df_pareto['% Valor'].apply(lambda x: f"<b>{x:.1f}%</b>"),
        color='% Valor', color_continuous_scale='Reds'
    )
    fig_pareto.update_traces(textposition='outside', textfont=dict(color='black', size=12))
    st.plotly_chart(fig_pareto, use_container_width=True)

    st.markdown("---")

    # --- 3. TABELA DETALHADA (FOCO EM DISPONIBILIDADE) ---
    st.subheader("📋 Detalhes: Reservado, Avaria e Disponibilidade")
    colunas_exibir = ['Código', 'Descrição', 'Estoque', 'Reservado', 'Qt.Avaria', 'Estoque Disponível', 'Venda Mês', 'Valor Total (R$)']
    
    st.dataframe(
        df[colunas_exibir].sort_values('Qt.Avaria', ascending=False).style.format({
            'Código': '{}', 
            'Estoque': '{:.2f} kg', 
            'Reservado': '{:.2f} kg',
            'Qt.Avaria': '{:.2f} kg',
            'Estoque Disponível': '{:.2f} kg',
            'Venda Mês': '{:.2f} kg',
            'Valor Total (R$)': 'R$ {:.2f}'
        }), 
        use_container_width=True, hide_index=True
    )

except Exception as e:
    st.error(f"Erro ao processar dados: {e}")
else:
    # Mensagem que aparece enquanto o arquivo não é carregado
    st.info("👋 Bem-vindo! Por favor, utilize a barra lateral à esquerda para carregar o seu arquivo 'BASE_PILOTO.xlsx'.")