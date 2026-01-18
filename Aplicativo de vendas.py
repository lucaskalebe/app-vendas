

import os
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# ================== CONFIGURAÇÕES E ESTILO ==================
st.set_page_config(page_title="Gestão Meira Nobre", layout="wide")

st.markdown("""
    <style>
    .segmento-box { background-color: #1e293b; padding: 15px; border-radius: 10px; border-left: 5px solid #8b5cf6; }
    </style>
""", unsafe_allow_html=True)

SENHA_MESTRE = os.getenv("SENHA_APP", "1234")
DB_NAME = "vendas.db"

def get_data(query):
    with sqlite3.connect(DB_NAME) as conn:
        return pd.read_sql(query, conn)

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        # 1. Criação Inicial das Tabelas
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vendas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT, empresa TEXT, cliente TEXT, produto TEXT, segmento TEXT,
                qtd INTEGER, valor_unit REAL, valor_total REAL, comissao REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cnpj TEXT, razao_social TEXT, telefone TEXT, email TEXT, categoria TEXT
            )
        """)
        
        # 2. MIGAÇÃO AUTOMÁTICA (Verifica colunas faltando)
        # Verificando tabela VENDAS
        cursor.execute("PRAGMA table_info(vendas)")
        cols_vendas = [col[1] for col in cursor.fetchall()]
        if 'segmento' not in cols_vendas:
            cursor.execute("ALTER TABLE vendas ADD COLUMN segmento TEXT DEFAULT 'Outros'")
            
        # Verificando tabela CLIENTES
        cursor.execute("PRAGMA table_info(clientes)")
        cols_clientes = [col[1] for col in cursor.fetchall()]
        for col_name in ['telefone', 'email', 'categoria']:
            if col_name not in cols_clientes:
                cursor.execute(f"ALTER TABLE clientes ADD COLUMN {col_name} TEXT DEFAULT 'Não Informado'")
        
        conn.commit()

init_db()

# --- LOGIN ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.title("🔒 Acesso Meira Nobre")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if senha == SENHA_MESTRE:
            st.session_state["autenticado"] = True
            st.rerun()
        else: st.error("Incorreta")
    st.stop()

# ================== INTERFACE ==================
t_dash, t_venda, t_hist, t_cli, t_db_cli = st.tabs([
    "📈 Dashboards", "➕ Nova Venda", "📜 Histórico", "👤 Novo Cliente", "📁 Banco de Clientes"
])

# --- 1. DASHBOARDS ---
with t_dash:
    df_v = get_data("SELECT * FROM vendas")
    df_c = get_data("SELECT * FROM clientes")
    
    st.subheader("📊 Performance de Vendas")
    if not df_v.empty:
        df_v['segmento'] = df_v['segmento'].fillna('Outros')
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Faturamento", f"R$ {df_v['valor_total'].sum():,.2f}")
        m2.metric("Comissões", f"R$ {df_v['comissao'].sum():,.2f}")
        m3.metric("Qtd Itens", int(df_v['qtd'].sum()))
        m4.metric("Ticket Médio", f"R$ {df_v['valor_total'].mean():,.2f}")

        c1, c2 = st.columns(2)
        with c1:
            st.write("**Vendas por Representada (R$)**")
            st.bar_chart(df_v.groupby("empresa")["valor_total"].sum())
        with c2:
            st.write("**Volume de Produtos por Segmento**")
            st.bar_chart(df_v.groupby("segmento")["qtd"].sum())
    
    st.divider()
    
    st.subheader("🟣 Inteligência de Clientes")
    if not df_c.empty:
        # Preencher vazios para evitar erro no value_counts
        df_c['categoria'] = df_c['categoria'].fillna('Não Definido')
        
        col_c1, col_c2 = st.columns([1, 2])
        with col_c1:
            st.markdown('<div class="segmento-box">', unsafe_allow_html=True)
            st.metric("Total de Clientes", len(df_c))
            st.write("Top Categorias:")
            st.write(df_c['categoria'].value_counts())
            st.markdown('</div>', unsafe_allow_html=True)
        with col_c2:
            st.write("**Distribuição por Tipo de Loja**")
            st.bar_chart(df_c.groupby("categoria").size())
    else:
        st.info("Nenhum cliente cadastrado.")

# --- 2. NOVA VENDA ---
with t_venda:
    with st.container(border=True):
        st.subheader("📝 Registrar Pedido")
        c1, c2, c3 = st.columns(3)
        emp = c1.text_input("Representada", key="v1")
        cli = c2.text_input("Cliente", key="v2")
        seg = c
