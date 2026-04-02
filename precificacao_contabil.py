import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection
import datetime
import os

# --- 1. CONFIGURAÇÃO DA PÁGINA (UNIFICADA) ---
st.set_page_config(page_title="Sistema Integrado Escrita Contabilidade", layout="wide", page_icon="📄")

# --- 2. CONEXÕES (SUPABASE + GOOGLE SHEETS) ---
# Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
GID_CUSTOS = "0"
GID_PESOS = "1471013444"
GID_ORCAMENTOS = "2020767836"

# --- 3. ESTILOS CSS (Interface CRM) ---
st.markdown("""
    <style>
    .metric-card { 
        background-color: #1a2a44; 
        padding: 30px; 
        border-radius: 15px; 
        color: white; 
        text-align: center;
        border: 2px solid #d4af37;
    }
    .metric-card h2 { color: #d4af37 !important; font-size: 3rem !important; margin: 15px 0 !important; }
    div.stButton > button { border-radius: 5px; font-weight: bold; width: 100%; height: 3em; }
    .stTabs [data-baseweb="tab"] { font-size: 1.1rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. FUNÇÕES AUXILIARES ---
def formatar_moeda(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

def buscar_segmentos():
    res = supabase.table("segmentos").select("*").execute()
    return res.data

def buscar_perguntas():
    res = supabase.table("perguntas").select("*").execute()
    return res.data

# --- 5. FUNÇÕES DE CÁLCULO (PLANILHA) ---
def carregar_config_custos():
    try:
        df = conn.read(worksheet=GID_CUSTOS, ttl=0)
        return {
            'pessoal': float(df.iloc[0, 1]),
            'despesas_gerais': float(df.iloc[1, 1]),
            'impostos_sobre_faturamento': float(df.iloc[2, 1]),
            'horas_uteis_colaborador': float(df.iloc[3, 1]),
            'total_colaboradores': int(df.iloc[4, 1])
        }
    except:
        return {'pessoal': 50000.0, 'despesas_gerais': 15000.0, 'impostos_sobre_faturamento': 15.0, 'horas_uteis_colaborador': 140.0, 'total_colaboradores': 5}

def carregar_pesos_esforco():
    try:
        df = conn.read(worksheet=GID_PESOS, ttl=0)
        return {
            'base_regime': {'Simples': float(df.iloc[0, 1]), 'Presumido': float(df.iloc[1, 1]), 'Real': float(df.iloc[2, 1])},
            'por_funcionario': float(df.iloc[3, 1]),
            'por_nota_fiscal': float(df.iloc[4, 1]),
            'por_lancamento': float(df.iloc[5, 1]),
            'fator_complexidade': {'Baixa': 1.0, 'Média': 1.3, 'Alta': 1.8},
            'fator_atendimento': {'Baixo': 1.0, 'Médio': 1.2, 'Alto': 1.5}
        }
    except:
        return None

# --- 6. GERADOR DE PDF (DESIGN ORIGINAL) ---
class PDFProposta(FPDF):
    def header(self):
        self.set_fill_color(26, 42, 68) 
        self.rect(0, 0, 5, 297, 'F')
        if os.path.exists("Logo Escrita.png"):
            self.image("Logo Escrita.png", 10, 10, 40)
        self.set_xy(60, 15)
        self.set_font("Arial", 'B', 18)
        self.set_text_color(26, 42, 68)
        self.cell(140, 10, "PROPOSTA COMERCIAL", 0, 1, 'R')
        self.set_font("Arial", '', 10)
        self.set_text_color(100, 100, 100)
        self.cell(190, 5, "Inteligencia Contabil e Gestao Estrategica", 0, 1, 'R')
        self.ln(15)

    def footer(self):
        self.set_y(-20)
        self.set_font("Arial", 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Escrita Contabilidade | Pagina {self.page_no()}", 0, 0, 'C')
        self.set_draw_color(200, 200, 200)
        self.line(10, 280, 200, 280)

def gerar_documento_proposta(dados_cliente, total):
    pdf = PDFProposta()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_fill_color(245, 245, 245)
    pdf.rect(10, 50, 190, 25, 'F')
    pdf.set_xy(15, 53)
    pdf.set_font("Arial", 'B', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, "CLIENTE APRESENTADO:", ln=True)
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(26, 42, 68)
    nome_u = dados_cliente['nome'].upper().encode('latin-1', 'ignore').decode('latin-1')
    pdf.cell(0, 8, nome_u, ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.set_text_color(50, 50, 50)
    seg_u = dados_cliente['segmento'].encode('latin-1', 'ignore').decode('latin-1')
    pdf.cell(0, 5, f"Segmento: {seg_u} | Data: {datetime.date.today().strftime('%d/%m/%Y')}", ln=True)
    pdf.ln(15)
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(26, 42, 68)
    pdf.cell(0, 10, "1. ESCOPO DOS SERVICOS", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.set_text_color(0, 0, 0)
    texto_intro = "Nossa proposta abrange a assessoria contabil completa... (Contabil, Fiscal e Trabalhista)."
    pdf.multi_cell(0, 6, texto_intro.encode('latin-1', 'ignore').decode('latin-1'))
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 11)
    pdf.set_fill_color(26, 42, 68)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(130, 12, "  Descricao do Investimento", 0, 0, 'L', True)
    pdf.cell(60, 12, "Valor Mensal  ", 0, 1, 'R', True)
    pdf.set_font("Arial", '', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(130, 15, "  Honorarios Mensais de Assessoria", 'B')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(60, 15, f"{formatar_moeda(total)}  ", 'B', 1, 'R')
    pdf.ln(15)
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(26, 42, 68)
    pdf.cell(0, 10, "2. CONDICOES GERAIS", ln=True)
    pdf.set_font("Arial", '', 10)
    condicoes = "- Validade: 10 dias corridos.\n- Reajuste: Anual pelo IGP-M/FGV."
    pdf.multi_cell(0, 6, condicoes.encode('latin-1', 'ignore').decode('latin-1'))
    pdf.ln(25)
    pdf.set_draw_color(26, 42, 68)
    pdf.line(60, pdf.get_y(), 150, pdf.get_y())
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 5, "ACEITE DO CLIENTE", 0, 1, 'C')
    return pdf.output()

# --- 7. NAVEGAÇÃO LATERAL ---
st.sidebar.image("Logo Escrita.png", width=200)
menu = st.sidebar.selectbox("Navegação", ["Nova Proposta", "Dashboard de Precificação", "Configurações do CRM", "Configurações de Custos (Planilha)"])

# Inicializar custos no estado da sessão
if 'custos_db' not in st.session_state:
    st.session_state.custos_db = carregar_config_custos()

# --- MÓDULO: NOVA PROPOSTA (UNIFICADO COM CUSTO REAL) ---
if menu == "Nova Proposta":
    st.title("📄 Elaboração de Proposta Comercial")
    
    segs = buscar_segmentos()
    lista_s = [s['nome'] for s in segs]
    
    if lista_s:
        c1, c2 = st.columns([2, 1])
        with c1:
            nome_cliente = st.text_input("Nome da Empresa / Prospecto:", placeholder="Ex: Labor Saúde LTDA")
        with c2:
            seg_sel = st.selectbox("Selecione o segmento:", lista_s)
        
        st.divider()
        
        # Lógica de Cálculo (Combina Perguntas do CRM + Base de Custo da Planilha)
        perguntas = supabase.table("perguntas").select("*").eq("segmento", seg_sel).execute().data
        total_acumulado = 0.0

        if perguntas:
            st.subheader("📋 Questionário de Diagnóstico")
            col_p, col_i = st.columns([2, 1])
            with col_p:
                for p in perguntas:
                    if "Múltipla Escolha" in p['tipo_campo']:
                        ops = [o.strip() for o in p['opcoes'].split(",")]
                        vls = [float(v.strip()) for v in p['pesos_opcoes'].split(",")]
                        esc = st.selectbox(p['pergunta'], ops, key=f"run_{p['id']}")
                        total_acumulado += vls[ops.index(esc)]
                    else:
                        n_in = st.number_input(p['pergunta'], min_value=0, key=f"run_{p['id']}")
                        total_acumulado += (n_in * float(p['pesos_opcoes']))
            
            # Painel de Resultado
            st.divider()
            st.markdown(f'''
                <div class="metric-card">
                    <p style="margin:0; font-size: 1.2rem; opacity: 0.8;">Honorário Mensal Estimado</p>
                    <h2>{formatar_moeda(total_acumulado)}</h2>
                    <p style="margin:0;">Foco em: {seg_sel}</p>
                </div>
            ''', unsafe_allow_html=True)
            
            if nome_cliente:
                pdf_output = gerar_documento_proposta({"nome": nome_cliente, "segmento": seg_sel}, total_acumulado)
                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    st.download_button(label="📥 Baixar Proposta PDF", data=bytes(pdf_output), file_name=f"Proposta_{nome_cliente.replace(' ', '_')}.pdf", mime="application/pdf", use_container_width=True)
                with c_btn2:
                    if st.button("💾 Salvar Histórico na Planilha", use_container_width=True):
                        try:
                            df_hist = conn.read(worksheet=GID_ORCAMENTOS, ttl=0)
                            nova_l = pd.DataFrame([{df_hist.columns[0]: nome_cliente, df_hist.columns[1]: datetime.date.today().strftime('%d/%m/%Y'), df_hist.columns[2]: total_acumulado, df_hist.columns[3]: "CRM"}])
                            conn.update(worksheet=GID_ORCAMENTOS, data=pd.concat([df_hist, nova_l], ignore_index=True))
                            st.success("✅ Salvo com sucesso!")
                        except Exception as e: st.error(f"Erro ao salvar: {e}")
            else:
                st.warning("⚠️ Digite o nome da empresa para habilitar a geração.")
        else:
            st.info("Nenhuma pergunta cadastrada para este segmento no Supabase.")

# --- MÓDULO: DASHBOARD DE PRECIFICAÇÃO (HISTÓRICO DA PLANILHA) ---
elif menu == "Dashboard de Precificação":
    st.title("📊 Análise de Carteira e Histórico")
    try:
        df_real = conn.read(worksheet=GID_ORCAMENTOS, ttl=0)
        if not df_real.empty:
            st.dataframe(df_real, use_container_width=True)
        else:
            st.info("Nenhum orçamento salvo no histórico ainda.")
    except Exception as e:
        st.error(f"Erro ao ler histórico da planilha: {e}")

# --- MÓDULO: CONFIGURAÇÕES DO CRM (SUPABASE) ---
elif menu == "Configurações do CRM":
    st.title("⚙️ Gestão de Regras (Supabase)")
    t1, t2 = st.tabs(["📂 Segmentos", "❓ Perguntas"])
    
    with t1:
        n_seg = st.text_input("Novo Segmento:")
        if st.button("Salvar Segmento"):
            supabase.table("segmentos").insert({"nome": n_seg}).execute()
            st.rerun()
        for s in buscar_segmentos():
            col_n, col_b = st.columns([3, 1])
            col_n.write(f"**{s['nome']}**")
            if col_b.button("Excluir", key=f"del_s_{s['id']}"):
                supabase.from_("segmentos").delete().eq("id", s['id']).execute()
                st.rerun()
                
    with t2:
        with st.form("cad_p"):
            lista_nomes = [s['nome'] for s in buscar_segmentos()]
            f_seg = st.selectbox("Segmento", lista_nomes)
            f_tipo = st.selectbox("Tipo", ["Múltipla Escolha (Valor Fixo)", "Número (Multiplicador)"])
            f_perg = st.text_input("Pergunta")
            f_opt = st.text_input("Opções (Separar por vírgula)")
            f_pesos = st.text_input("Pesos R$ (Separar por vírgula)")
            if st.form_submit_button("Salvar Pergunta"):
                supabase.table("perguntas").insert({"segmento": f_seg, "pergunta": f_perg, "tipo_campo": f_tipo, "opcoes": f_opt, "pesos_opcoes": f_pesos}).execute()
                st.rerun()

# --- MÓDULO: CONFIGURAÇÕES DE CUSTOS (DRE PLANILHA) ---
elif menu == "Configurações de Custos (Planilha)":
    st.title("⚙️ Base de Custos Real (DRE)")
    c1, c2 = st.columns(2)
    custos = st.session_state.custos_db
    with c1:
        st.write("### Despesas Fixas")
        pessoal = st.number_input("Folha + Encargos", value=custos['pessoal'])
        despesas = st.number_input("Despesas Gerais", value=custos['despesas_gerais'])
    with c2:
        st.write("### Capacidade")
        colab = st.number_input("Total Colaboradores", value=custos['total_colaboradores'])
        horas = st.number_input("Horas Úteis/Mês", value=custos['horas_uteis_colaborador'])
    
    custo_hora = (pessoal + despesas) / (colab * horas) if (colab * horas) > 0 else 0
    st.metric("Custo Hora Operacional", formatar_moeda(custo_hora))
    st.info("Estes valores são carregados da sua Planilha Google Sheets.")
