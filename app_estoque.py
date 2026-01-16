# 3. INTERFACE DO DASHBOARD
st.set_page_config(page_title="Estoque Filial 3", layout="wide")
st.title("📊 Controle de Estoque Real - Setor Fiscal")
st.markdown("---")

df_vendas = carregar_dados_completos()

if df_vendas is not None:
    # --- INDICADORES DE TOPO (KPIs) ---
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Itens", len(df_vendas))
    with col2:
        venda_total = df_vendas['Venda Mês'].sum()
        st.metric("Volume Venda Mês", f"{venda_total:,.2f} kg")
    with col3:
        estoque_total = df_vendas['Estoque Disponível'].sum()
        st.metric("Estoque Disponível Total", f"{estoque_total:,.2f} kg")

    st.markdown("---")

    # --- GRÁFICOS ---
    tab1, tab2, tab3 = st.tabs(["📊 Ranking de Volume", "📈 Análise de Pareto", "📋 Tabela de Dados"])

    with tab1:
        st.subheader("Top 15 Produtos por Venda no Mês")
        # Criar gráfico de barras
        df_ranking = df_vendas.nlargest(15, 'Venda Mês')
        st.bar_chart(data=df_ranking, x='Descrição', y='Venda Mês')

    with tab2:
        st.subheader("Curva Pareto (Acumulado de Vendas)")
        # Lógica do Pareto
        df_pareto = df_vendas.sort_values(by='Venda Mês', ascending=False).copy()
        df_pareto['Venda Acumulada'] = df_pareto['Venda Mês'].cumsum()
        total_vendas = df_pareto['Venda Mês'].sum()
        df_pareto['% Acumulada'] = (df_pareto['Venda Acumulada'] / total_vendas) * 100
        
        # Exibir gráfico de linha para o acumulado
        st.line_chart(data=df_pareto, x='Descrição', y='% Acumulada')
        st.info("Os produtos que atingem até 80% da curva representam sua Curva A.")

    with tab3:
        st.success(f"Dados carregados! {len(df_vendas)} itens monitorados.")
        st.dataframe(df_vendas, use_container_width=True, hide_index=True)