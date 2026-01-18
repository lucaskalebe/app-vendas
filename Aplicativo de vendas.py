

import os
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# ================== CONFIGURAÇÕES E ESTILO ==================
st.set_page_config(page_title="Gestão Meira Nobre", layout="wide")

# CSS para cores personalizadas no Dash de Clientes
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
        # Tabela de Vendas Atualizada com SEGMENTO
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

# --- 1. DASHBOARDS (VENDA + CLIENTES) ---
with t_dash:
    df_v = get_data("SELECT * FROM vendas")
    df_c = get_data("SELECT * FROM clientes")
    
    st.subheader("📊 Performance de Vendas")
    if not df_v.empty:
        df_v = df_v.dropna(subset=['empresa'])
        
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
    
    # --- DASH DE CLIENTES (COR DIFERENTE) ---
    st.subheader("🟣 Inteligência de Clientes")
    if not df_c.empty:
        col_c1, col_c2 = st.columns([1, 2])
        with col_c1:
            st.markdown('<div class="segmento-box">', unsafe_allow_html=True)
            st.metric("Total de Clientes", len(df_c))
            st.write("Top Categorias:")
            st.write(df_c['categoria'].value_counts())
            st.markdown('</div>', unsafe_allow_html=True)
        with col_c2:
            st.write("**Distribuição por Tipo de Loja**")
            # Gráfico de área ou barras horizontais para clientes
            st.bar_chart(df_c.groupby("categoria").size())
    else:
        st.info("Nenhum cliente cadastrado para análise.")

# --- 2. NOVA VENDA (COM SEGMENTO) ---
with t_venda:
    with st.container(border=True):
        st.subheader("📝 Registrar Pedido")
        c1, c2, c3 = st.columns(3)
        emp = c1.text_input("Representada", key="v1")
        cli = c2.text_input("Cliente", key="v2")
        seg = c3.selectbox("Segmento", ["Utensílios de Cozinha", "Brinquedos", "Papelaria", "Outros"], key="v3")
        
        prod = st.text_input("Produto", key="v4")
        
        col1, col2, col3 = st.columns(3)
        q = col1.number_input("Qtd", min_value=1, value=1)
        v = col2.number_input("Preço Unit.", min_value=0.0)
        p = col3.number_input("Comissão %", value=10)
        
        total = q * v
        comis = total * (p/100)
        
        if st.button("🚀 Salvar Venda"):
            dt = datetime.now().strftime("%d/%m/%Y %H:%M")
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute("INSERT INTO vendas (data, empresa, cliente, produto, segmento, qtd, valor_unit, valor_total, comissao) VALUES (?,?,?,?,?,?,?,?,?)",
                             (dt, emp, cli, prod, seg, q, v, total, comis))
            st.success("Salvo!")
            st.rerun()

# --- 3. HISTÓRICO ---
with t_hist:
    df_h = get_data("SELECT * FROM vendas ORDER BY id DESC")
    edited = st.data_editor(df_h, use_container_width=True, num_rows="dynamic")
    if st.button("💾 Sincronizar Tudo"):
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("DELETE FROM vendas")
            edited.to_sql("vendas", conn, if_exists="append", index=False)
            conn.execute("VACUUM")
        st.rerun()

# --- 4. CADASTRO CLIENTE ---
with t_cli:
    with st.form("cli_form", clear_on_submit=True):
        st.subheader("👤 Novo Cliente")
        c1, c2 = st.columns(2)
        rs = c1.text_input("Razão Social")
        cj = c2.text_input("CNPJ")
        cat = st.selectbox("Tipo de Loja", ["Varejo", "Atacado", "Supermercado", "Boutique"])
        if st.form_submit_button("Salvar Cliente"):
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute("INSERT INTO clientes (cnpj, razao_social, categoria) VALUES (?,?,?)", (cj, rs, cat))
            st.success("Cliente na base!")

# --- 5. BANCO DE CLIENTES ---
with t_db_cli:
    df_clients = get_data("SELECT * FROM clientes")
    st.data_editor(df_clients, use_container_width=True, num_rows="dynamic")
