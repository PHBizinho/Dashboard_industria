import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="Controle de Estoque - Frigorífico", layout="wide")

st.title("🥩 Dashboard de Estoque - Setor Fiscal")
st.markdown("---")

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- INTERFACE DE UPLOAD NA BARRA LATERAL ---
st.sidebar.header("Configurações")
arquivo_carregado = st.sidebar.file_uploader("Carregue a base Excel (BASE_PILOTO)", type=["xlsx"])

if arquivo_carregado is not None:
    try:
        # Lendo o arquivo que o usuário subiu pelo navegador
        df_completo = pd.read_excel(arquivo_carregado)
        df_completo.columns = df_completo.columns.str.strip()
        df_completo = df_completo[pd.to_numeric(df_completo['Código'], errors='coerce').notnull()]
        
        df_completo['Filial'] = df_completo['Filial'].astype(int)
        df_completo['Código'] = df_completo['Código'].astype(int)
        
        # Regra de Matéria-Prima
        codigos_mp = [1228, 6009, 18765, 6010]
        df_completo['Categoria'] = df_completo['Código'].apply(lambda x: 'Matéria-Prima' if x in codigos_mp else 'Cortes/Outros')
        df_completo['Valor Total (R$)'] = df_completo['Estoque'] * df_completo['Custo contábil']

        # Filtros
        categoria_selecionada = st.sidebar.multiselect(
            "Selecione a Categoria:",
            options=df_completo['Categoria'].unique(),
            default=df_completo['Categoria'].unique()
        )
        df = df_completo[df_completo['Categoria'].isin(categoria_selecionada)]

        # --- KPIs ---
        col1, col2, col3, col4 = st.columns(4)
        total_kg = df['Estoque'].sum()
        total_fin = df['Valor Total (R$)'].sum()
        estoque_mp = df_completo[df_completo['Categoria'] == 'Matéria-Prima']['Estoque'].sum()

        col1.metric("Estoque Selecionado (kg)", f"{total_kg:,.2f} kg".replace(",", "X").replace(".", ",").replace("X", "."))
        col2.metric("Valor em estoque", formatar_moeda(total_fin))
        col3.metric("Estoque MATÉRIA-PRIMA", f"{estoque_mp:,.2f} kg".replace(",", "X").replace(".", ",").replace("X", "."))
        col4.metric("Qtd Itens", len(df))

        st.markdown("---")

        # --- GRÁFICOS ---
        col_esq, col_dir = st.columns(2)
        with col_esq:
            st.subheader("Volume por Corte (kg)")
            top_n = df.nlargest(15, 'Estoque').sort_values('Estoque', ascending=True)
            top_n['Rótulo_Qtd'] = top_n['Estoque'].apply(lambda x: f"{x:,.2f} kg".replace(",", "X").replace(".", ",").replace("X", "."))
            fig_vol = px.bar(top_n, x='Estoque', y='Descrição', orientation='h', text='Rótulo_Qtd',
                             color='Categoria', color_discrete_map={'Matéria-Prima': '#960018', 'Cortes/Outros': '#3274ad'})
            st.plotly_chart(fig_vol, use_container_width=True)

        with col_dir:
            st.subheader("Distribuição Financeira por Categoria")
            fig_pie = px.pie(df, values='Valor Total (R$)', names='Categoria', hole=0.4,
                             color='Categoria', color_discrete_map={'Matéria-Prima': '#960018', 'Cortes/Outros': '#3274ad'})
            st.plotly_chart(fig_pie, use_container_width=True)

        with st.expander("Ver Base de Dados Detalhada"):
            st.dataframe(df.style.format({
                'Filial': '{}', 'Código': '{}', 'Estoque': '{:.2f} kg', 'Reservado': '{:.2f} kg',
                'Disponível': '{:.2f} kg', 'Qt.Avaria': '{:.2f} kg', 'Custo contábil': 'R$ {:.2f}', 'Valor Total (R$)': 'R$ {:.2f}'
            }), use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
else:
    # Mensagem que aparece enquanto o arquivo não é carregado
    st.info("👋 Bem-vindo! Por favor, utilize a barra lateral à esquerda para carregar o seu arquivo 'BASE_PILOTO.xlsx'.")