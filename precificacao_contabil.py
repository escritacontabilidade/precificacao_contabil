import streamlit as st
import pandas as pd
import numpy as np

# Configuração da Página
st.set_page_config(page_title="Sistema de Precificação Contábil v1.0", layout="wide")

# --- ESTADOS DO SISTEMA ---
if 'custos_db' not in st.session_state:
    st.session_state.custos_db = {
        'pessoal': 50000.0,
        'despesas_gerais': 15000.0,
        'impostos_sobre_faturamento': 15.0,
        'horas_uteis_colaborador': 140.0, # 160h - 20h (administrativo/ociosidade)
        'total_colaboradores': 5
    }

if 'pesos_esforço' not in st.session_state:
    st.session_state.pesos_esforço = {
        'base_regime': {'Simples': 2.0, 'Presumido': 5.0, 'Real': 10.0},
        'por_funcionario': 0.5,
        'por_nota_fiscal': 0.1,
        'por_lancamento': 0.05,
        'fator_complexidade': {'Baixa': 1.0, 'Média': 1.3, 'Alta': 1.8},
        'fator_atendimento': {'Baixo': 1.0, 'Médio': 1.2, 'Alto': 1.5}
    }

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
    
    def render_price_card(label, margin, color):
        # Markup = 1 / (1 - impostos - margem)
        tax = st.session_state.custos_db['impostos_sobre_faturamento'] / 100
        preco = custo_operacional_cliente / (1 - tax - (margin/100))
        st.metric(label, f"R$ {preco:,.2f}", f"Margem: {margin}%", delta_color="normal")
        return preco

    with col_res1:
        st.subheader("Mínimo (Sobrevivência)")
        render_price_card("Preço Bronze", 20, "inverse")
    
    with col_res2:
        st.subheader("Ideal (Crescimento)")
        render_price_card("Preço Prata", 35, "normal")
        
    with col_res3:
        st.subheader("Premium (Alta Rentabilidade)")
        render_price_card("Preço Ouro", 50, "normal")

    st.info(f"Esforço estimado: {horas_estimadas:.2f} horas/mês | Custo operacional direto: R$ {custo_operacional_cliente:,.2f}")

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
    st.header("Análise de Carteira (Mock Data)")
    # Simulação de dados para visualização
    data = {
        'Cliente': ['Empresa A', 'Empresa B', 'Empresa C', 'Empresa D'],
        'Honorário Atual': [2500, 1200, 5000, 800],
        'Custo Operacional': [1800, 1400, 3200, 950],
    }
    df = pd.DataFrame(data)
    df['Margem R$'] = df['Honorário Atual'] - df['Custo Operacional']
    df['Margem %'] = (df['Margem R$'] / df['Honorário Atual']) * 100
    df['Status'] = df['Margem R$'].apply(lambda x: "✅ Lucro" if x > 0 else "🚨 Prejuízo")
    
    st.table(df.sort_values(by='Margem %', ascending=False))
    
    st.bar_chart(df.set_index('Cliente')['Margem %'])

# --- TAB 4: SIMULADOR ---
with tabs[3]:
    st.header("Simulador de Escala")
    st.write("O que acontece se a carga de trabalho aumentar em X% sem contratar?")
    aumento_carga = st.slider("Aumento de Volume Operacional (%)", 0, 100, 0)
    novo_custo_hora = calcular_custo_hora() * (1 + (aumento_carga/100))
    st.warning(f"Se o volume aumentar {aumento_carga}% sem novos recursos, o custo invisível por hora sobe para R$ {novo_custo_hora:,.2f} devido à perda de eficiência.")
