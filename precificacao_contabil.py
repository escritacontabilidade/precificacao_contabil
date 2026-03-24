import streamlit as st
import pandas as pd
import numpy as np
from streamlit_gsheets import GSheetsConnection
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Sistema de Precificação Contábil v1.0", layout="wide")

# --- FUNÇÃO DE FORMATAÇÃO BRASILEIRA ---
def format_brl(valor):
    """Formata números para o padrão de moeda brasileiro."""
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

# --- CONEXÃO PARA LEITURA (O QUE JÁ FUNCIONA) ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CONFIGURAÇÃO PARA ESCRITA (GSPREAD - MAIS ROBUSTO) ---
def get_gspread_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    # Puxa as credenciais direto do que você já tem no Secrets
    creds_dict = {
        "type": st.secrets["connections"]["gsheets"]["type"],
        "project_id": st.secrets["connections"]["gsheets"]["project_id"],
        "private_key_id": st.secrets["connections"]["gsheets"]["private_key_id"],
        "private_key": st.secrets["connections"]["gsheets"]["private_key"],
        "client_email": st.secrets["connections"]["gsheets"]["client_email"],
        "client_id": st.secrets["connections"]["gsheets"]["client_id"],
        "auth_uri": st.secrets["connections"]["gsheets"]["auth_uri"],
        "token_uri": st.secrets["connections"]["gsheets"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["connections"]["gsheets"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["connections"]["gsheets"]["client_x509_cert_url"],
    }
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(credentials)

def carregar_config_custos():
    try:
        df = conn.read(worksheet=0, ttl=0)
        return {
            'pessoal': float(df.iloc[0, 1]),
            'despesas_gerais': float(df.iloc[1, 1]),
            'impostos_sobre_faturamento': float(df.iloc[2, 1]),
            'horas_uteis_colaborador': float(df.iloc[3, 1]),
            'total_colaboradores': int(df.iloc[4, 1])
        }
    except:
        return {'pessoal': 50000.0, 'despesas_gerais': 15000.0, 'impostos_sobre_faturamento': 15.0, 'horas_uteis_colaborador': 140.0, 'total_colaboradores': 5}

def carregar_pesos():
    try:
        df = conn.read(worksheet=1, ttl=0)
        return {
            'base_regime': {'Simples': float(df.iloc[0, 1]), 'Presumido': float(df.iloc[1, 1]), 'Real': float(df.iloc[2, 1])},
            'por_funcionario': float(df.iloc[3, 1]),
            'por_nota_fiscal': float(df.iloc[4, 1]),
            'por_lancamento': float(df.iloc[5, 1]),
            'fator_complexidade': {'Baixa': 1.0, 'Média': 1.3, 'Alta': 1.8},
            'fator_atendimento': {'Baixo': 1.0, 'Médio': 1.2, 'Alto': 1.5}
        }
    except:
        return {'base_regime': {'Simples': 2.0, 'Presumido': 5.0, 'Real': 10.0}, 'por_funcionario': 0.5, 'por_nota_fiscal': 0.1, 'por_lancamento': 0.05, 'fator_complexidade': {'Baixa': 1.0, 'Média': 1.3, 'Alta': 1.8}, 'fator_atendimento': {'Baixo': 1.0, 'Médio': 1.2, 'Alto': 1.5}}

if 'custos_db' not in st.session_state:
    st.session_state.custos_db = carregar_config_custos()
if 'pesos_esforço' not in st.session_state:
    st.session_state.pesos_esforço = carregar_pesos()

def calcular_custo_hora():
    custo_total = st.session_state.custos_db['pessoal'] + st.session_state.custos_db['despesas_gerais']
    horas_totais = st.session_state.custos_db['horas_uteis_colaborador'] * st.session_state.custos_db['total_colaboradores']
    return custo_total / horas_totais if horas_totais > 0 else 0

def calcular_esforco(regime, funcionarios, notas, lancamentos, complexidade, atendimento):
    h_base = st.session_state.pesos_esforço['base_regime'][regime]
    h_var = (funcionarios * st.session_state.pesos_esforço['por_funcionario']) + (notas * st.session_state.pesos_esforço['por_nota_fiscal']) + (lancamentos * st.session_state.pesos_esforço['por_lancamento'])
    return (h_base + h_var) * st.session_state.pesos_esforço['fator_complexidade'][complexidade] * st.session_state.pesos_esforço['fator_atendimento'][atendimento]

st.title("📊 Gestão de Precificação - Escrita Contabilidade")
tabs = st.tabs(["Cálculo de Preço", "Configuração de Custos", "Dashboard Gerencial", "Simulador"])

with tabs[0]:
    st.header("Novo Orçamento")
    col1, col2 = st.columns(2)
    with col1:
        nome_cliente = st.text_input("Nome do Cliente")
        regime = st.selectbox("Regime", ["Simples", "Presumido", "Real"])
        faturamento = st.number_input("Faturamento Estimado (R$)", min_value=0.0, format="%.2f")
        funcionarios = st.number_input("Funcionários", min_value=0, step=1)
    with col2:
        notas = st.number_input("Notas Fiscais", min_value=0, step=1)
        lancamentos = st.number_input("Lançamentos", min_value=0, step=1)
        complexidade = st.select_slider("Complexidade", options=["Baixa", "Média", "Alta"])
        atendimento = st.select_slider("Atendimento", options=["Baixo", "Médio", "Alto"])

    custo_h = calcular_custo_hora()
    esforco = calcular_esforco(regime, funcionarios, notas, lancamentos, complexidade, atendimento)
    custo_total_cli = esforco * custo_h

    st.divider()
    res1, res2, res3 = st.columns(3)
    precos = {}

    def render_card(label, margin, col):
        tax = st.session_state.custos_db['impostos_sobre_faturamento'] / 100
        p = custo_total_cli / (1 - tax - (margin/100))
        col.metric(label, format_brl(p), f"Margem: {margin}%")
        return p

    precos['Bronze'] = render_card("Bronze", 20, res1)
    precos['Prata'] = render_card("Prata", 35, res2)
    precos['Ouro'] = render_card("Ouro", 50, res3)

    if st.button("💾 Salvar Orçamento na Planilha"):
        if nome_cliente:
            try:
                gc = get_gspread_client()
                # Abre a planilha pelo ID exato
                sh = gc.open_by_key("1NYxBBZ1OM_dvlAV9nHoS6JcSaQRIuVXRXFrI3FHRviM")
                # Abre a aba Orcamentos pelo nome exato (ou use .get_worksheet(2))
                ws = sh.worksheet("Orcamentos")
                
                nova_linha = [nome_cliente, datetime.now().strftime("%d/%m/%Y"), round(precos['Prata'], 2), 35]
                ws.append_row(nova_linha)
                
                st.success("✅ Salvo com sucesso via gspread!")
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")
        else:
            st.warning("⚠️ Digite o nome do cliente.")

with tabs[1]:
    st.header("Configuração de Custos")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.session_state.custos_db['pessoal'] = st.number_input("Folha", value=st.session_state.custos_db['pessoal'], format="%.2f")
        st.session_state.custos_db['despesas_gerais'] = st.number_input("Despesas", value=st.session_state.custos_db['despesas_gerais'], format="%.2f")
        st.session_state.custos_db['impostos_sobre_faturamento'] = st.slider("Impostos %", 0.0, 30.0, st.session_state.custos_db['impostos_sobre_faturamento'])
    with col_c2:
        st.session_state.custos_db['total_colaboradores'] = st.number_input("Colaboradores", value=int(st.session_state.custos_db['total_colaboradores']), step=1)
        st.session_state.custos_db['horas_uteis_colaborador'] = st.number_input("Horas Úteis", value=st.session_state.custos_db['horas_uteis_colaborador'], format="%.2f")
        st.metric("Custo Hora", format_brl(calcular_custo_hora()))

with tabs[2]:
    st.header("Análise de Carteira")
    try:
        df_real = conn.read(worksheet="Orcamentos", ttl=0)
        if not df_real.empty:
            df_display = df_real.copy()
            df_display.iloc[:, 2] = df_display.iloc[:, 2].apply(format_brl)
            st.dataframe(df_display, use_container_width=True)
    except:
        st.warning("Sem dados.")

with tabs[3]:
    st.header("Simulador")
    aumento = st.slider("Aumento %", 0, 100, 0)
    st.warning(f"Custo invisível: {format_brl(calcular_custo_hora() * (1 + (aumento/100)))}")
