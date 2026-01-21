import streamlit as st
import oracledb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import io

# Importações para o PDF Profissional
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

# --- 1. CONFIGURAÇÃO AMBIENTE ---
st.set_page_config(page_title="Dashboard Seridoense", layout="wide")

if 'oracle_client_initialized' not in st.session_state:
    try:
        oracledb.init_oracle_client(lib_dir=r"C:\oracle\instantclient_19_29")
        st.session_state['oracle_client_initialized'] = True
    except Exception as e:
        st.error(f"Erro Client Oracle: {e}")

# --- 2. FUNÇÃO PARA GERAR PDF PERSONALIZADO ---
def gerar_pdf_seridoense(row, df_cortes):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    elements = []
    styles = getSampleStyleSheet()
    
    # Definição da Cor Seridoense (Vermelho)
    cor_seridoense = colors.Color(0.8, 0, 0)
    
    # Estilos de Texto
    style_header = ParagraphStyle('HeaderSeridoense', parent=styles['Heading1'], fontSize=18, textColor=cor_seridoense, spaceAfter=20)
    style_normal = styles['Normal']
    style_footer = ParagraphStyle('Footer', fontSize=8, textColor=colors.grey, alignment=1)

    # Título do Relatório
    elements.append(Paragraph("RELATÓRIO DE DESOSSA - SERIDOENSE", style_header))
    
    # Tabela de Dados da Carga
    dados_info = [
        [f"NF: {row['NF']}", f"DATA: {row['DATA']}"],
        [f"FORNECEDOR: {row['FORNECEDOR']}", f"TIPO: {row['TIPO']}"],
        [f"PESO ENTRADA: {row['ENTRADA']} Kg", f"PEÇAS: {row['PECAS']}"]
    ]
    t_info = Table(dados_info, colWidths=[9*cm, 9*cm])
    t_info.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,-1), colors.whitesmoke),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 15))

    # Tabela de Cortes
    elements.append(Paragraph("<b>DETALHAMENTO DA PRODUÇÃO</b>", styles['Heading3']))
    data_tabela = [["CORTE / SUBPRODUTO", "PESO (KG)"]]
    for _, r in df_cortes.iterrows():
        data_tabela.append([r['Corte'], f"{r['Peso (Kg)']:,.2f}"])
    
    # Linha de Total
    total_produzido = df_cortes['Peso (Kg)'].sum()
    data_tabela.append(["TOTAL PRODUZIDO", f"{total_produzido:,.2f}"])

    t_cortes = Table(data_tabela, colWidths=[13*cm, 5*cm])
    t_cortes.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), cor_seridoense),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_cortes)
    
    # Rodapé de Autoria
    elements.append(Spacer(1, 4*cm))
    elements.append(Paragraph("________________________________________________", style_footer))
    elements.append(Paragraph(f"Relatório gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}", style_footer))
    elements.append(Paragraph("<b>Desenvolvido por: Paulo Henrique - Setor Fiscal</b>", style_footer))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- 3. FUNÇÕES DE DADOS ---
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
    except:
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
    meses_pt = {1:"Jan", 2:"Fev", 3:"Mar", 4:"Abr", 5:"Mai", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Set", 10:"Out", 11:"Nov", 12:"Dez"}
    hoje = datetime.now()
    return [f"{meses_pt[(hoje.month-i-1)%12+1]}/{str(hoje.year)[2:]}" for i in range(4)]

# --- 4. INTERFACE ---
col_logo, col_tit = st.columns([1, 5])
with col_logo:
    if os.path.exists("MARCA-SERIDOENSE_.png"): st.image("MARCA-SERIDOENSE_.png", width=140)
with col_tit:
    st.title("Sistema de Inteligência de Estoque e Desossa")
    st.markdown("*Responsável: **Paulo Henrique**, Setor Fiscal*")

df_estoque = carregar_dados()

if df_estoque is not None:
    c1, c2, c3 = st.columns(3)
    c1.metric("Estoque Total (Kg)", f"{formatar_br(df_estoque['QTESTGER'].sum())} Kg")
    c2.metric("Valor Imobilizado", f"R$ {formatar_br(df_estoque['Valor em Estoque'].sum())}")
    c3.metric(f"Venda {obter_nomes_meses()[0]}", f"{formatar_br(df_estoque['QTVENDMES'].sum())} Kg")
    st.markdown("---")

    tabs = st.tabs(["📊 Gráfico Rendimento", "🧮 Simulador", "📝 Registro Diário", "🔍 Histórico e Consulta"])

    with tabs[3]: # ABA HISTÓRICO
        if os.path.exists("DESOSSA_HISTORICO.csv"):
            df_h = pd.read_csv("DESOSSA_HISTORICO.csv")
            df_h['DATA'] = pd.to_datetime(df_h['DATA']).dt.date
            
            st.markdown("#### 🔍 Filtros de Busca")
            cf1, cf2 = st.columns(2)
            with cf1: sel_nf = st.selectbox("Selecione a NF para exportar:", ["Todas"] + sorted(df_h['NF'].unique().tolist()))
            
            df_f = df_h.copy()
            if sel_nf != "Todas": df_f = df_f[df_f['NF'] == sel_nf]
            
            st.dataframe(df_f, use_container_width=True, hide_index=True)

            if not df_f.empty:
                st.markdown("### 📋 Gerar Documentos para Diretoria")
                for _, row in df_f.iterrows():
                    with st.expander(f"Relatório NF {row['NF']} - {row['FORNECEDOR']}"):
                        ignorar = ['DATA', 'NF', 'TIPO', 'FORNECEDOR', 'PECAS', 'ENTRADA']
                        cortes_encontrados = {c: float(row[c]) for c in row.index if c not in ignorar and float(row[c]) > 0}
                        df_rel_corte = pd.DataFrame(list(cortes_encontrados.items()), columns=['Corte', 'Peso (Kg)'])
                        
                        col_rel, col_btn = st.columns([2, 1])
                        with col_rel: st.table(df_rel_corte)
                        with col_btn:
                            # GERADOR DE PDF
                            pdf_file = gerar_pdf_seridoense(row, df_rel_corte)
                            st.download_button(
                                label=f"📥 Baixar PDF NF {row['NF']}",
                                data=pdf_file,
                                file_name=f"Relatorio_Desossa_NF_{row['NF']}.pdf",
                                mime="application/pdf",
                                key=f"btn_{row['NF']}"
                            )
        else:
            st.info("Nenhum histórico encontrado.")

    # --- ABAIXO DAS ABAS: GRÁFICOS GERAIS ---
    st.markdown("---")
    st.subheader("🥩 Top 20 - Volume em Estoque (kg)")
    df_t20 = df_estoque.nlargest(20, 'QTESTGER').sort_values('QTESTGER', ascending=True)
    fig_est = px.bar(df_t20, x='QTESTGER', y='Descrição', orientation='h', color='QTESTGER', color_continuous_scale='Greens', text_auto='.2f')
    st.plotly_chart(fig_est, use_container_width=True)

    st.subheader("📋 Detalhamento Geral de Itens")
    st.dataframe(df_estoque[['Código', 'Descrição', 'QTESTGER', 'Disponível', 'CUSTOREAL', 'Valor em Estoque']], use_container_width=True, hide_index=True)
    
    st.info("Dashboard ativo. Autoria: Paulo Henrique - Setor Fiscal.")
    