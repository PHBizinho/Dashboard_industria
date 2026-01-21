import streamlit as st
import oracledb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import base64

# --- 1. CONFIGURAÇÃO AMBIENTE ---
st.set_page_config(page_title="Dashboard Seridoense", layout="wide")

if 'oracle_client_initialized' not in st.session_state:
    try:
        oracledb.init_oracle_client(lib_dir=r"C:\oracle\instantclient_19_29")
        st.session_state['oracle_client_initialized'] = True
    except Exception as e:
        st.error(f"Erro Client Oracle: {e}")

# --- 2. FUNÇÕES DE APOIO ---

@st.cache_data(ttl=600)
def carregar_dados():
    conn_params = {"user": "NUTRICAO", "password": "nutr1125mmf", "dsn": "192.168.222.20:1521/WINT"}
    try:
        conn = oracledb.connect(**conn_params)
        query = """SELECT CODPROD, QTESTGER, QTRESERV, QTBLOQUEADA, QTVENDMES, 
                           QTVENDMES1, QTVENDMES2, QTVENDMES3, CUSTOREAL 
                    FROM MMFRIOS.PCEST WHERE CODFILIAL = 3 AND QTESTGER > 0"""
        df = pd.read_sql(query, conn)
        conn.close()
        df_nomes = pd.read_excel("BASE_DESCRICOES_PRODUTOS.xlsx")
        df_nomes.columns = ['Código', 'Descrição']
        df_final = pd.merge(df, df_nomes, left_on="CODPROD", right_on="Código", how="inner")
        df_final['Disponível'] = df_final['QTESTGER'] - df_final['QTRESERV'] - df_final['QTBLOQUEADA']
        df_final['Valor em Estoque'] = df_final['QTESTGER'] * df_final['CUSTOREAL']
        return df_final
    except Exception as e:
        return None

def salvar_dados_desossa(dados_dict):
    arquivo = "DESOSSA_HISTORICO.csv"
    df_novo = pd.DataFrame([dados_dict])
    if os.path.exists(arquivo):
        df_hist = pd.read_csv(arquivo)
        df_hist = pd.concat([df_hist, df_novo], ignore_index=True)
    else:
        df_hist = df_novo
    df_hist.to_csv(arquivo, index=False)
    st.toast(f"✅ Desossa salva!", icon='🥩')

def formatar_br(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def obter_nomes_meses():
    meses_pt = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun", 
                7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}
    hoje = datetime.now()
    lista = []
    for i in range(4):
        m, y = hoje.month - i, hoje.year
        while m <= 0: m += 12; y -= 1
        lista.append(f"{meses_pt[m]}/{str(y)[2:]}")
    return lista

# --- 3. FUNÇÕES DE IMPRESSÃO (NOVA ABA) ---

def gerar_html_impressao(row, df_cortes):
    """Gera o HTML puro para ser aberto em nova aba"""
    tabela_html = ""
    for _, r in df_cortes.iterrows():
        tabela_html += f"<tr><td>{r['Corte']}</td><td>{r['Peso (Kg)']:,.2f} Kg</td></tr>"

    hoje_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Relatório NF {row['NF']}</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 30px; color: #333; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #cc0000; padding-bottom: 10px; }}
            .logo-text {{ font-size: 24px; font-weight: bold; color: #cc0000; }}
            .info-box {{ background: #f4f4f4; padding: 15px; margin-top: 20px; border-radius: 5px; display: grid; grid-template-columns: 1fr 1fr 1fr; }}
            .info-item {{ margin-bottom: 5px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th {{ background-color: #cc0000; color: white; text-align: left; padding: 12px; }}
            td {{ border-bottom: 1px solid #ddd; padding: 10px; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #888; border-top: 1px solid #ddd; padding-top: 10px; }}
            @media print {{ .no-print {{ display: none; }} }}
        </style>
    </head>
    <body onload="window.print()">
        <div class="header">
            <div class="logo-text">SERIDOENSE - RELATÓRIO DE DESOSSA</div>
            <div>Data de emissão: {hoje_str}</div>
        </div>
        
        <div class="info-box">
            <div class="info-item"><b>Nº NF:</b> {row['NF']}</div>
            <div class="info-item"><b>Data Desossa:</b> {row['DATA']}</div>
            <div class="info-item"><b>Fornecedor:</b> {row['FORNECEDOR']}</div>
            <div class="info-item"><b>Tipo Animal:</b> {row['TIPO']}</div>
            <div class="info-item"><b>Qtd Peças:</b> {row['PECAS']}</div>
            <div class="info-item"><b>Peso Entrada:</b> {row['ENTRADA']} Kg</div>
        </div>

        <table>
            <thead>
                <tr><th>Corte / Subproduto</th><th>Peso Final</th></tr>
            </thead>
            <tbody>
                {tabela_html}
            </tbody>
        </table>

        <div class="footer">
            Relatório gerado pelo Sistema de Inteligência de Estoque - Responsável: Paulo Henrique.
        </div>
        
        <div class="no-print" style="margin-top: 20px; text-align: center;">
            <button onclick="window.print()" style="padding: 10px 20px; cursor: pointer;">Clique aqui se a impressora não abrir</button>
        </div>
    </body>
    </html>
    """
    # Converter para Base64 para abrir via link
    b64 = base64.b64encode(html.encode('utf-8')).decode()
    return f"data:text/html;base64,{b64}"

# --- 4. INTERFACE PRINCIPAL ---

col_logo, col_tit = st.columns([1, 5])
with col_logo:
    if os.path.exists("MARCA-SERIDOENSE_.png"): st.image("MARCA-SERIDOENSE_.png", width=140)
with col_tit:
    st.title("Sistema de Inteligência de Estoque e Desossa")
    st.markdown("*Responsável: **Paulo Henrique**, Setor Fiscal*")

df_estoque = carregar_dados()

if df_estoque is not None:
    # Métricas
    c1, c2, c3 = st.columns(3)
    c1.metric("Estoque Total (Kg)", f"{formatar_br(df_estoque['QTESTGER'].sum())} Kg")
    c2.metric("Valor Imobilizado", f"R$ {formatar_br(df_estoque['Valor em Estoque'].sum())}")
    c3.metric(f"Venda {obter_nomes_meses()[0]}", f"{formatar_br(df_estoque['QTVENDMES'].sum())} Kg")
    st.markdown("---")

    tabs = st.tabs(["📊 Rendimento", "🧮 Simulador", "📝 Registro", "🔍 Histórico e Consulta"])

    with tabs[3]: # Aba Consulta
        if os.path.exists("DESOSSA_HISTORICO.csv"):
            df_h = pd.read_csv("DESOSSA_HISTORICO.csv")
            df_h['DATA'] = pd.to_datetime(df_h['DATA']).dt.date
            
            st.markdown("#### 🔍 Filtros")
            cf1, cf2, cf3 = st.columns([2, 1, 1])
            with cf1: p = st.date_input("Período:", [datetime.now().date() - timedelta(days=7), datetime.now().date()])
            with cf2: nf_sel = st.selectbox("NF:", ["Todas"] + sorted(df_h['NF'].astype(str).unique().tolist()))
            with cf3: forn_sel = st.selectbox("Fornecedor:", ["Todos"] + sorted(df_h['FORNECEDOR'].unique().tolist()))
            
            # Filtro
            df_f = df_h.copy()
            if len(p) == 2: df_f = df_f[(df_f['DATA'] >= p[0]) & (df_f['DATA'] <= p[1])]
            if nf_sel != "Todas": df_f = df_f[df_f['NF'].astype(str) == nf_sel]
            if forn_sel != "Todos": df_f = df_f[df_f['FORNECEDOR'] == forn_sel]
            
            st.dataframe(df_f, use_container_width=True, hide_index=True)

            if not df_f.empty:
                st.markdown("### 📋 Fichas Disponíveis")
                for _, row in df_f.iterrows():
                    with st.expander(f"NF: {row['NF']} - Fornecedor: {row['FORNECEDOR']} ({row['DATA']})"):
                        ignorar = ['DATA', 'NF', 'TIPO', 'FORNECEDOR', 'PECAS', 'ENTRADA']
                        cortes = {c: float(row[c]) for c in row.index if c not in ignorar and float(row[c]) > 0}
                        df_rel = pd.DataFrame(list(cortes.items()), columns=['Corte', 'Peso (Kg)'])
                        
                        col_a, col_b = st.columns([1, 1])
                        with col_a: st.table(df_rel)
                        with col_b:
                            link_html = gerar_html_impressao(row, df_rel)
                            st.markdown(f"""
                                <a href="{link_html}" target="_blank">
                                    <button style="width:100%; height:100px; background-color:#cc0000; color:white; border:none; border-radius:10px; font-weight:bold; cursor:pointer;">
                                        🖨️ CLIQUE AQUI PARA IMPRIMIR<br>ESTA FICHA (NF {row['NF']})
                                    </button>
                                </a>
                            """, unsafe_allow_html=True)
        else:
            st.info("Nenhum histórico encontrado.")

    # --- GRÁFICOS ABAIXO DAS ABAS ---
    st.markdown("---")
    st.subheader("🥩 Top 20 - Volume em Estoque (kg)")
    df_t20 = df_estoque.nlargest(20, 'QTESTGER').sort_values('QTESTGER', ascending=True)
    fig_est = px.bar(df_t20, x='QTESTGER', y='Descrição', orientation='h', color='QTESTGER', color_continuous_scale='Greens', text_auto='.2f')
    fig_est.update_layout(height=700)
    st.plotly_chart(fig_est, use_container_width=True)

    st.markdown("---")
    st.subheader("🏆 Análise de Vendas (KG)")
    # (Restante do seu código de vendas e tabela geral...)
    st.dataframe(df_estoque[['Código', 'Descrição', 'QTESTGER', 'Disponível', 'CUSTOREAL', 'Valor em Estoque']], use_container_width=True)