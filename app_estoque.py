import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="Controle de Estoque - Frigorífico", layout="wide")

st.title("🥩 Dashboard de Estoque - Setor Fiscal")
st.markdown("---")

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

@st.cache_data
def carregar_dados():
    df = pd.read_excel("BASE_PILOTO.xlsx")
    df.columns = df.columns.str.strip()
    df = df[pd.to_numeric(df['Código'], errors='coerce').notnull()]
    
    df['Filial'] = df['Filial'].astype(int)
    df['Código'] = df['Código'].astype(int)
    
    # --- NOVA REGRA DE NEGÓCIO: Classificação de Matéria-Prima ---
    codigos_mp = [1228, 6009, 18765, 6010]
    df['Categoria'] = df['Código'].apply(lambda x: 'Matéria-Prima' if x in codigos_mp else 'Cortes/Outros')
    
    df['Valor Total (R$)'] = df['Estoque'] * df['Custo contábil']
    return df

try:
    df_completo = carregar_dados()

    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.header("Filtros de Visão")
    categoria_selecionada = st.sidebar.multiselect(
        "Selecione a Categoria:",
        options=df_completo['Categoria'].unique(),
        default=df_completo['Categoria'].unique()
    )

    # Filtrando o DataFrame principal com base na seleção
    df = df_completo[df_completo['Categoria'].isin(categoria_selecionada)]

    # --- INDICADORES (KPIs) ---
    col1, col2, col3, col4 = st.columns(4)
    
    total_kg = df['Estoque'].sum()
    total_fin = df['Valor Total (R$)'].sum()
    
    # KPI Específico para Matéria-Prima
    estoque_mp = df_completo[df_completo['Categoria'] == 'Matéria-Prima']['Estoque'].sum()

    col1.metric("Estoque Selecionado (kg)", f"{total_kg:,.2f} kg".replace(",", "X").replace(".", ",").replace("X", "."))
    
    # ALTERAÇÃO AQUI: De "Valor Selecionado" para "Valor em estoque"
    col2.metric("Valor em estoque", formatar_moeda(total_fin))
    
    col3.metric("Estoque MATÉRIA-PRIMA", f"{estoque_mp:,.2f} kg".replace(",", "X").replace(".", ",").replace("X", "."), help="Soma dos códigos 1228, 6009, 18765 e 6010")
    col4.metric("Qtd Itens", len(df))

    st.markdown("---")

    # --- GRÁFICOS ---
    col_esq, col_dir = st.columns(2)

    with col_esq:
        st.subheader("Volume por Corte (kg)")
        # Mostra o top 15 para ter uma visão mais ampla
        top_n = df.nlargest(15, 'Estoque').sort_values('Estoque', ascending=True)
        top_n['Rótulo_Qtd'] = top_n['Estoque'].apply(lambda x: f"{x:,.2f} kg".replace(",", "X").replace(".", ",").replace("X", "."))

        fig_vol = px.bar(top_n, x='Estoque', y='Descrição', 
                         orientation='h', 
                         text='Rótulo_Qtd',
                         color='Categoria', # Cor diferencia MP de Cortes
                         color_discrete_map={'Matéria-Prima': '#960018', 'Cortes/Outros': '#3274ad'})
        
        fig_vol.update_layout(xaxis_title=None, yaxis_title=None, showlegend=True)
        st.plotly_chart(fig_vol, use_container_width=True)

    with col_dir:
        st.subheader("Distribuição Financeira por Categoria")
        # Gráfico de pizza para ver o peso da MP no financeiro total
        fig_pie = px.pie(df, values='Valor Total (R$)', names='Categoria', 
                         hole=0.4,
                         color='Categoria',
                         color_discrete_map={'Matéria-Prima': '#960018', 'Cortes/Outros': '#3274ad'})
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- TABELA ---
    with st.expander("Ver Base de Dados Detalhada"):
        st.dataframe(
            df.style.format({
                'Filial': '{}', 'Código': '{}',
                'Estoque': '{:.2f} kg', 'Reservado': '{:.2f} kg',
                'Disponível': '{:.2f} kg', 'Qt.Avaria': '{:.2f} kg',
                'Custo contábil': 'R$ {:.2f}', 'Valor Total (R$)': 'R$ {:.2f}'
            }), 
            use_container_width=True,
            hide_index=True
        )

except Exception as e:
    st.error(f"Erro no processamento: {e}")