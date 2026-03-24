import streamlit as st
import pandas as pd
import numpy as np
from streamlit_gsheets import GSheetsConnection
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

# --- CONEXÃO COM BANCO DE DADOS (GOOGLE SHEETS) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_config_custos():
    try:
        # worksheet=0 pega a PRIMEIRA aba (Custos)
        df = conn.read(worksheet=0, ttl=0)
        return {
            'pessoal': float(df.iloc[0, 1]),
            'despesas_gerais': float(df.iloc[1, 1]),
            'impostos_sobre_faturamento': float(df.iloc[2, 1]),
            'horas_uteis_colaborador': float(df.iloc[3, 1]),
            'total_colaboradores': int(df.iloc[4, 1])
        }
    except Exception as e:
        return {
            'pessoal': 50000.0, 'despesas_gerais': 15000.0, 'impostos_sobre_faturamento': 15.0,
            'horas_uteis_colaborador': 140.0, 'total_colaboradores': 5
        }

def carregar_pesos():
    try:
        # worksheet=1 pega a SEGUNDA aba (Pesos)
        df = conn.read(worksheet=1, ttl=0)
        return {
            'base_regime': {'Simples': float(df.iloc[0, 1]), 
                            'Presumido': float(df.iloc[1, 1]), 
                            'Real': float(df.iloc[2, 1])},
            'por_funcionario': float(df.iloc[3, 1]),
            'por_nota_fiscal': float(df.iloc[4, 1]),
            'por_lancamento': float(df.iloc[5, 1]),
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

# Inicializa dados no session_state
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
        faturamento = st.number_input("Faturamento Mensal Estimado (R$)", min_value=0.0, format="%.2f")
        funcionarios = st.number_input("Nº de Funcionários", min_value=0, step=1)
    
    with col2:
        notas = st.number_input("Qtd Notas Fiscais/Mês", min_value=0, step=1)
        lancamentos = st.number_input("Qtd Lançamentos Contábeis/Mês", min_value=0, step=1)
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
        st.metric(label, format_brl(preco), f"Margem: {margin}%")
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

    st.info(f"Esforço estimado: **{horas_estimadas:.2f} horas/mês** | Custo operacional direto: **{format_brl(custo_operacional_cliente)}**")

    if st.button("💾 Salvar Orçamento na Planilha"):
        if nome_cliente:
            try:
                # worksheet=2 pega a TERCEIRA aba (Orcamentos)
                df_atual = conn.read(worksheet=2, ttl=0)
                
                novo_linha = pd.DataFrame([{
                    df_atual.columns[0]: nome_cliente,
                    df_atual.columns[1]: datetime.now().strftime("%d/%m/%Y"),
                    df_atual.columns[2]: round(precos_calculados['Prata'], 2),
                    df_atual.columns[3]: 35
                }])
                
                df_final = pd.concat([df_atual, novo_linha], ignore_index=True)
                # O update usando o índice numérico da aba evita erros de 404 por nome
                conn.update(worksheet=2, data=df_final)
                st.success("✅ Orçamento salvo com sucesso!")
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")
        else:
            st.warning("⚠️ Digite o nome do cliente antes de salvar.")

# --- TAB 2: CONFIGURAÇÃO DE CUSTOS (DRE) ---
with tabs[1]:
    st.header("Configuração da Operação (Base DRE)")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.session_state.custos_db['pessoal'] = st.number_input("Folha de Pagamento + Encargos (Mensal)", value=st.session_state.custos_db['pessoal'], format="%.2f")
        st.session_state.custos_db['despesas_gerais'] = st.number_input("Aluguel, Software, Energia, Outros", value=st.session_state.custos_db['despesas_gerais'], format="%.2f")
        st.session_state.custos_db['impostos_sobre_faturamento'] = st.slider("Impostos S/ Faturamento (%)", 0.0, 30.0, st.session_state.custos_db['impostos_sobre_faturamento'])
    
    with col_c2:
        st.session_state.custos_db['total_colaboradores'] = st.number_input("Total de Colaboradores Operacionais", value=int(st.session_state.custos_db['total_colaboradores']), step=1)
        st.session_state.custos_db['horas_uteis_colaborador'] = st.number_input("Horas Produtivas por Colaborador/Mês", value=st.session_state.custos_db['horas_uteis_colaborador'], format="%.2f")
        
        st.metric("Custo Hora Calculado", format_brl(calcular_custo_hora()))

    st.subheader("Pesos de Esforço (Configurável)")
    with st.expander("Ajustar Parâmetros de Tempo"):
        st.session_state.pesos_esforço['por_funcionario'] = st.number_input("Horas por Funcionário", value=st.session_state.pesos_esforço['por_funcionario'])
        st.session_state.pesos_esforço['por_nota_fiscal'] = st.number_input("Horas por Nota Fiscal", value=st.session_state.pesos_esforço['por_nota_fiscal'])
        st.session_state.pesos_esforço['por_lancamento'] = st.number_input("Horas por Lançamento Contábil", value=st.session_state.pesos_esforço['por_lancamento'])

# --- TAB 3: DASHBOARD GERENCIAL ---
with tabs[2]:
    st.header("Análise de Carteira Real")
    try:
        # worksheet=2 pega a TERCEIRA aba
        df_real = conn.read(worksheet=2, ttl=0)
        df_display = df_real.copy()
        if not df_display.empty:
            # Formata a terceira coluna (índice 2) independente do nome
            df_display.iloc[:, 2] = df_display.iloc[:, 2].apply(format_brl)
            st.dataframe(df_display, use_container_width=True)
        else:
            st.info("A aba de histórico está vazia.")
    except Exception as e:
        st.warning(f"Erro ao carregar dashboard: {e}")

# --- TAB 4: SIMULADOR ---
with tabs[3]:
    st.header("Simulador de Escala")
    st.write("O que acontece se a carga de trabalho aumentar em X% sem contratar?")
    aumento_carga = st.slider("Aumento de Volume Operacional (%)", 0, 100, 0)
    novo_custo_hora = calcular_custo_hora() * (1 + (aumento_carga/100))
    st.warning(f"Se o volume aumentar {aumento_carga}% sem novos recursos, o custo invisível por hora sobe para **{format_brl(novo_custo_hora)}** devido à perda de eficiência.")
