import streamlit as st
import pandas as pd
import numpy as np
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Sistema de Precificação Contábil v1.0", layout="wide")

# --- CONEXÃO COM BANCO DE DATA (GOOGLE SHEETS) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_config_custos():
    # Tenta ler da aba 'Custos', se falhar usa padrão para não quebrar o sistema
    try:
        df = conn.read(worksheet="Custos", ttl=0)
        return {
            'pessoal': float(df.loc[df['item'] == 'pessoal', 'valor'].values[0]),
            'despesas_gerais': float(df.loc[df['item'] == 'despesas_gerais', 'valor'].values[0]),
            'impostos_sobre_faturamento': float(df.loc[df['item'] == 'impostos', 'valor'].values[0]),
            'horas_uteis_colaborador': float(df.loc[df['item'] == 'horas_uteis', 'valor'].values[0]),
            'total_colaboradores': int(df.loc[df['item'] == 'colaboradores', 'valor'].values[0])
        }
    except:
        return {
            'pessoal': 50000.0, 'despesas_gerais': 15000.0, 'impostos_sobre_faturamento': 15.0,
            'horas_uteis_colaborador': 140.0, 'total_colaboradores': 5
        }

def carregar_pesos():
    try:
        df = conn.read(worksheet="Pesos", ttl=0)
        # Transforma a planilha de pesos em dicionário para o motor de cálculo
        return {
            'base_regime': {'Simples': float(df.loc[df['parametro'] == 'Simples', 'valor'].values[0]), 
                            'Presumido': float(df.loc[df['parametro'] == 'Presumido', 'valor'].values[0]), 
                            'Real': float(df.loc[df['parametro'] == 'Real', 'valor'].values[0])},
            'por_funcionario': float(df.loc[df['parametro'] == 'por_funcionario', 'valor'].values[0]),
            'por_nota_fiscal': float(df.loc[df['parametro'] == 'por_nota_fiscal', 'valor'].values[0]),
            'por_lancamento': float(df.loc[df['parametro'] == 'por_lancamento', 'valor'].values[0]),
            'fator_complexidade': {'Baixa': 1.0, 'Média': 1.3, 'Alta': 1.8},
            'fator_atendimento': {'Baixo': 1.0, 'Médio': 1.2, 'Alto': 1.5}
        }
    except:
        return {
            'base_regime': {'Simples': 2.0, 'Presumido': 5.0, 'Real': 10.0},
            'por_funcionario': 0.5, 'por_nota_fiscal': 0.1, 'por_lancamento': 0.05,
            'fator_complexidade': {'Baixa': 1.0, 'Média': 1.3, 'Alta': 1.8},
            'fator_atendimento': {'Baixo': 1.0, 'Médio': 1.2, 'Alto': 1.5}
        }

# Inicializa dados no session_state vindos da Planilha
if 'custos_db' not in st.session_state:
    st.session_state.custos_db = carregar_config_custos()

if 'pesos_esforço' not in st.session_state:
    st.session_state.pesos_esforço = carregar_pesos()

# --- FUNÇÕES DE CÁLCULO ---
def calcular_custo_hora():
    custo_total = st.session_state.custos_db['pessoal'] + st.session_state.custos_db['despesas_gerais']
    horas_totais = st.session_state.custos_db['horas_uteis_colaborador'] * st.session_state.custos_db['total_colaboradores']
    return custo_total / horas_totais if horas_totais > 0 else 0

def calcular_esforco(regime, funcionarios, notas, lancamentos, complexidade, atendimento):
    horas_base = st.session_state.pesos_esforço['base_regime'][regime]
    horas_variaveis = (funcionarios * st.session_state.pesos_esforço['por_funcionario']) + \
                      (notas * st.session_state.pesos_esforço['por_nota_fiscal']) + \
                      (lancamentos * st.session_state.pesos_esforço['por_lancamento'])
    
    total_horas = (horas_base + horas_variaveis) * \
                  st.session_state.pesos_esforço['fator_complexidade'][complexidade] * \
                  st.session_state.pesos_esforço['fator_atendimento'][atendimento]
    return total_horas

# --- INTERFACE ---
st.title("📊 Gestão de Precificação Baseada em Custo Real")

tabs = st.tabs(["Cálculo de Preço", "Configuração de Custos", "Dashboard Gerencial", "Simulador"])

# --- TAB 1: CÁLCULO DE PREÇO ---
with tabs[0]:
    st.header("Novo Orçamento / Análise de Cliente")
    
    col1, col2 = st.columns(2)
    with col1:
        nome_cliente = st.text_input("Nome do Cliente/Prospect")
        regime = st.selectbox("Regime Tributário", ["Simples", "Presumido", "Real"])
        faturamento = st.number_input("Faturamento Mensal Estimado (R$)", min_value=0.0)
        funcionarios = st.number_input("Nº de Funcionários", min_value=0)
    
    with col2:
        notas = st.number_input("Qtd Notas Fiscais/Mês", min_value=0)
        lancamentos = st.number_input("Qtd Lançamentos Contábeis/Mês", min_value=0)
        complexidade = st.select_slider("Complexidade Técnica", options=["Baixa", "Média", "Alta"])
        atendimento = st.select_slider("Nível de Atendimento (Suporte)", options=["Baixo", "Médio", "Alto"])

    custo_hora = calcular_custo_hora()
    horas_estimadas = calcular_esforco(regime, funcionarios, notas, lancamentos, complexidade, atendimento)
    custo_operacional_cliente = horas_estimadas * custo_hora

    st.divider()
    
    col_res1, col_res2, col_res3 = st.columns(3)
    
    precos_calculados = {}

    def render_price_card(label, margin):
        tax = st.session_state.custos_db['impostos_sobre_faturamento'] / 100
        preco = custo_operacional_cliente / (1 - tax - (margin/100))
        st.metric(label, f"R$ {preco:,.2f}", f"Margem: {margin}%")
        return preco

    with col_res1:
        st.subheader("Mínimo (Sobrevivência)")
        precos_calculados['Bronze'] = render_price_card("Preço Bronze", 20)
    
    with col_res2:
        st.subheader("Ideal (Crescimento)")
        precos_calculados['Prata'] = render_price_card("Preço Prata", 35)
        
    with col_res3:
        st.subheader("Premium (Alta Rentabilidade)")
        precos_calculados['Ouro'] = render_price_card("Preço Ouro", 50)

    st.info(f"Esforço estimado: {horas_estimadas:.2f} horas/mês | Custo operacional direto: R$ {custo_operacional_cliente:,.2f}")

    if st.button("💾 Salvar Orçamento na Planilha"):
        # Lógica para salvar os dados na aba 'Orcamentos'
        novo_orcamento = pd.DataFrame([{
            "Data": datetime.now().strftime("%d/%m/%Y"),
            "Cliente": nome_cliente,
            "Custo_Operacional": custo_operacional_cliente,
            "Preco_Sugerido": precos_calculados['Prata']
        }])
        try:
            conn.create(worksheet="Orcamentos", data=novo_orcamento)
            st.success("Orçamento enviado para a planilha!")
        except:
            st.error("Erro ao salvar. Verifique as permissões de escrita.")

# --- TAB 2: CONFIGURAÇÃO DE CUSTOS (DRE) ---
with tabs[1]:
    st.header("Configuração da Operação (Base DRE)")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.session_state.custos_db['pessoal'] = st.number_input("Folha de Pagamento + Encargos (Mensal)", value=st.session_state.custos_db['pessoal'])
        st.session_state.custos_db['despesas_gerais'] = st.number_input("Aluguel, Software, Energia, Outros", value=st.session_state.custos_db['despesas_gerais'])
        st.session_state.custos_db['impostos_sobre_faturamento'] = st.slider("Impostos S/ Faturamento (%)", 0.0, 30.0, st.session_state.custos_db['impostos_sobre_faturamento'])
    
    with col_c2:
        st.session_state.custos_db['total_colaboradores'] = st.number_input("Total de Colaboradores Operacionais", value=st.session_state.custos_db['total_colaboradores'])
        st.session_state.custos_db['horas_uteis_colaborador'] = st.number_input("Horas Produtivas por Colaborador/Mês", value=st.session_state.custos_db['horas_uteis_colaborador'])
        
        st.metric("Custo Hora Calculado", f"R$ {calcular_custo_hora():,.2f}")

    st.subheader("Pesos de Esforço (Configurável)")
    with st.expander("Ajustar Parâmetros de Tempo"):
        st.session_state.pesos_esforço['por_funcionario'] = st.number_input("Horas por Funcionário", value=st.session_state.pesos_esforço['por_funcionario'])
        st.session_state.pesos_esforço['por_nota_fiscal'] = st.number_input("Horas por Nota Fiscal", value=st.session_state.pesos_esforço['por_nota_fiscal'])
        st.session_state.pesos_esforço['por_lancamento'] = st.number_input("Horas por Lançamento Contábil", value=st.session_state.pesos_esforço['por_lancamento'])

# --- TAB 3: DASHBOARD GERENCIAL ---
with tabs[2]:
    st.header("Análise de Carteira Real")
    try:
        df_real = conn.read(worksheet="Orcamentos", ttl=0)
        st.dataframe(df_real, use_container_width=True)
    except:
        st.warning("Nenhum dado encontrado na aba 'Orcamentos'.")

# --- TAB 4: SIMULADOR ---
with tabs[3]:
    st.header("Simulador de Escala")
    st.write("O que acontece se a carga de trabalho aumentar em X% sem contratar?")
    aumento_carga = st.slider("Aumento de Volume Operacional (%)", 0, 100, 0)
    novo_custo_hora = calcular_custo_hora() * (1 + (aumento_carga/100))
    st.warning(f"Se o volume aumentar {aumento_carga}% sem novos recursos, o custo invisível por hora sobe para R$ {novo_custo_hora:,.2f} devido à perda de eficiência.")
