import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="Controle de Estoque - Frigorífico", layout="wide")

st.title("🥩 Dashboard de Estoque Seridoense - Setor Fiscal")
st.markdown("---")

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def obter_nomes_meses():
    agora = datetime.now()
    if agora.year < 2026: agora = datetime(2026, agora.month, 1)
    return {
        'Venda Mês': agora.strftime('%b/%y').upper(),
        'Venda Mês 1': (agora - relativedelta(months=1)).strftime('%b/%y').upper(),
        'Venda Mês 2': (agora - relativedelta(months=2)).strftime('%b/%y').upper(),
        'Venda Mês 3': (agora - relativedelta(months=3)).strftime('%b/%y').upper()
    }

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
    
    colunas_vendas = ['Venda Mês', 'Venda Mês 1', 'Venda Mês 2', 'Venda Mês 3']
    df[colunas_vendas] = df[colunas_vendas].fillna(0)
    
    df['Estoque Disponível'] = df['Estoque'] - df['Reservado'] - df['Qt.Avaria']
    df['Valor Total (R$)'] = df['Estoque'] * df['Custo contábil']
    df['Média Vendas (3m)'] = df[['Venda Mês 1', 'Venda Mês 2', 'Venda Mês 3']].mean(axis=1)
    return df

# --- SIDEBAR ---
st.sidebar.header("⚙️ Painel de Controle")
if st.sidebar.button("🔄 Atualizar Dados"):
    st.cache_data.clear()
    st.rerun()

try:
    df_completo = carregar_dados()
    nomes_meses = obter_nomes_meses()
    
    peca_selecionada = st.sidebar.multiselect(
        "**Selecione a(as) classificação(ões):**",
        options=sorted(df_completo['Classificação'].unique()),
        default=df_completo['Classificação'].unique()
    )
    df_global = df_completo[df_completo['Classificação'].isin(peca_selecionada)]
    
    cortes_disponiveis = sorted(df_global['Descrição'].unique())
    corte_selecionado = st.sidebar.multiselect(
        "**Filtrar por Corte (Vendas e Tabela):**",
        options=cortes_disponiveis
    )

    if st.sidebar.button("🗑️ Limpar Filtro de Corte"):
        st.rerun()

    # --- KPIs ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Estoque Selecionado (kg)", f"{df_global['Estoque'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c2.metric("Total Reservado (kg)", f"{df_global['Reservado'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c3.metric("Média Vendas (3m)", f"{df_global['Média Vendas (3m)'].sum():,.2f} kg")
    c4.metric("Valor Total", formatar_moeda(df_global['Valor Total (R$)'].sum()))

    st.markdown("---")

    # --- 1. VOLUME DETALHADO (TOP 20) ---
    st.subheader("📊 Ranking de Volume em Estoque (Top 20)")
    top_n = df_global.nlargest(20, 'Estoque').sort_values('Estoque', ascending=True)
    top_n['Rótulo'] = top_n['Estoque'].apply(lambda x: f"<b>{x:,.2f} kg</b>".replace(",", "X").replace(".", ",").replace("X", "."))
    fig_vol = px.bar(top_n, x='Estoque', y='Descrição', orientation='h', text='Rótulo',
                     color='Classificação', color_discrete_map={'TRASEIRO': '#960018', 'DIANTEIRO': '#3274ad', 'EXTRA': '#2ecc71', 'MATERIA PRIMA': '#f39c12', 'SOL': '#9b59b6', 'MOIDA': '#1abc9c'}, height=600)
    fig_vol.update_traces(textposition='auto', textfont=dict(color='black', size=12))
    st.plotly_chart(fig_vol, use_container_width=True)

    st.markdown("---")

    # --- 2. PARETO FINANCEIRO (RESTAURADO) ---
    st.subheader("🎯 Análise de Pareto: Impacto Financeiro por Corte")
    df_global['% Valor'] = (df_global['Valor Total (R$)'] / df_global['Valor Total (R$)'].sum()) * 100
    df_pareto = df_global.nlargest(15, 'Valor Total (R$)')
    fig_pareto = px.bar(df_pareto, x='Descrição', y='% Valor',
                        text=df_pareto['% Valor'].apply(lambda x: f"<b>{x:.1f}%</b>"),
                        color='% Valor', color_continuous_scale='Reds')
    fig_pareto.update_traces(textposition='outside', textfont=dict(color='black', size=12))
    st.plotly_chart(fig_pareto, use_container_width=True)

    st.markdown("---")

    # --- 3. HISTÓRICO DE VENDAS (FILTRÁVEL) ---
    df_vendas = df_global.copy()
    if corte_selecionado:
        df_vendas = df_vendas[df_vendas['Descrição'].isin(corte_selecionado)]

    st.subheader(f"📈 Histórico de Vendas: {', '.join(corte_selecionado) if corte_selecionado else 'Geral Selecionado'}")
    df_hist = df_vendas[['Venda Mês', 'Venda Mês 1', 'Venda Mês 2', 'Venda Mês 3']].sum().reset_index()
    df_hist.columns = ['Mês_Ref', 'Volume']
    df_hist['Mês_Nome'] = df_hist['Mês_Ref'].map(nomes_meses)
    df_hist = df_hist.iloc[::-1]

    fig_hist = px.bar(df_hist, x='Mês_Nome', y='Volume', 
                      text=df_hist['Volume'].apply(lambda x: f"<b>{x:,.0f} kg</b>".replace(",", ".")),
                      color_discrete_sequence=['#2ecc71'],
                      range_y=[0, df_hist['Volume'].max() * 1.3])
    fig_hist.update_traces(textposition='outside', textfont=dict(color='black', size=14), cliponaxis=False)
    st.plotly_chart(fig_hist, use_container_width=True)

    st.markdown("---")

    # --- 4. TABELA DETALHADA ---
    st.subheader("📋 Detalhamento Geral")
    df_view = df_vendas.rename(columns=nomes_meses)
    colunas = ['Código', 'Descrição', 'Estoque', 'Reservado', 'Qt.Avaria', 'Estoque Disponível', 
              nomes_meses['Venda Mês'], nomes_meses['Venda Mês 1'], nomes_meses['Venda Mês 2'], nomes_meses['Venda Mês 3']]
    st.dataframe(df_view[colunas].sort_values('Estoque', ascending=False).style.format({
        'Estoque': '{:.2f} kg', 'Reservado': '{:.2f} kg', 'Qt.Avaria': '{:.2f} kg', 'Estoque Disponível': '{:.2f} kg'
    }), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Erro: {e}")
else:
    # Mensagem que aparece enquanto o arquivo não é carregado
    st.info("👋 Bem-vindo! Por favor, utilize a barra lateral à esquerda para carregar o seu arquivo 'BASE_PILOTO.xlsx'.")