

import os
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# ================== CONFIGURAÇÕES E ESTILO ==================
st.set_page_config(page_title="Gestão Meira Nobre", layout="wide")

SENHA_MESTRE = os.getenv("SENHA_APP", "1234")
DB_NAME = "vendas.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vendas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT, empresa TEXT, cliente TEXT, produto TEXT,
                qtd INTEGER, valor_unit REAL, valor_total REAL, comissao REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cnpj TEXT, razao_social TEXT, telefone TEXT, email TEXT
            )
        """)

# Inicializa banco
init_db()

# Funções de Login
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.title("🔒 Acesso Restrito")
    senha = st.text_input("Digite a senha", type="password")
    if st.button("Entrar"):
        if senha == SENHA_MESTRE:
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Senha incorreta")
    st.stop()

# ================== INTERFACE PRINCIPAL ==================
st.title("📊 Sistema de Gestão Meira Nobre")

t_dash, t_venda, t_hist_vendas, t_cad_cliente, t_db_cliente = st.tabs([
    "📈 Dashboard Pro", "➕ Nova Venda", "📜 Histórico e Edição", "👤 Cadastro Cliente", "📁 Banco de Dados Clientes"
])

# --- 1. DASHBOARD (CORRIGIDO SEM GAP) ---
with t_dash:
    with sqlite3.connect(DB_NAME) as conn:
        df_v = pd.read_sql("SELECT * FROM vendas", conn)
    
    # Limpa linhas nulas para não dar erro no gráfico
    df_v = df_v.dropna(subset=['empresa', 'valor_total'])
    
    if not df_v.empty:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Faturamento Total", f"R$ {df_v['valor_total'].sum():,.2f}")
        m2.metric("Total Comissões", f"R$ {df_v['comissao'].sum():,.2f}")
        m3.metric("Ticket Médio", f"R$ {df_v['valor_total'].mean():,.2f}")
        m4.metric("Qtd Pedidos", len(df_v))
        
        st.divider()
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("Vendas por Representada")
            vendas_emp = df_v.groupby("empresa")["valor_total"].sum().reset_index()
            st.bar_chart(vendas_emp.set_index("empresa"))
        with g2:
            st.subheader("Performance de Comissões")
            comis_emp = df_v.groupby("empresa")["comissao"].sum().reset_index()
            st.bar_chart(comis_emp.set_index("empresa"))
    else:
        st.info("Lance vendas válidas para ativar o Dashboard.")

# --- 2. NOVA VENDA (COM LIMPEZA AUTOMÁTICA) ---
with t_venda:
    with st.container(border=True):
        st.subheader("📝 Registrar Novo Pedido")
        
        # Uso de chaves (keys) para permitir o reset
        c_top1, c_top2 = st.columns(2)
        emp = c_top1.text_input("🏢 Empresa Representada", key="n_emp")
        cli = c_top2.text_input("🏬 Cliente / Loja", key="n_cli")
        prod = st.text_input("📦 Descrição do Produto", key="n_prod")
        
        c1, c2, c3 = st.columns(3)
        q = c1.number_input("🔢 Quantidade", min_value=1, value=1, key="n_q")
        v = c2.number_input("💰 Preço Unitário (R$)", min_value=0.0, format="%.2f", key="n_v")
        p = c3.number_input("📈 Sua Comissão %", min_value=0, value=10, key="n_p")
        
        total_calc = q * v
        comis_calc = total_calc * (p / 100)
        
        st.divider()
        res1, res2 = st.columns(2)
        res1.metric("Valor Total", f"R$ {total_calc:,.2f}")
        res2.metric("Sua Comissão", f"R$ {comis_calc:,.2f}")

        if st.button("🚀 Salvar Venda definitiva", use_container_width=True):
            if emp and cli and v > 0:
                dt = datetime.now().strftime("%d/%m/%Y %H:%M")
                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute("INSERT INTO vendas (data, empresa, cliente, produto, qtd, valor_unit, valor_total, comissao) VALUES (?,?,?,?,?,?,?,?)",
                                 (dt, emp, cli, prod, q, v, total_calc, comis_calc))
                st.success("✅ Venda salva!")
                # Força a limpeza de todos os campos resetando o estado
                for key in ["n_emp", "n_cli", "n_prod", "n_v"]:
                    st.session_state[key] = "" if isinstance(st.session_state[key], str) else 0.0
                st.rerun()
            else:
                st.error("⚠️ Preencha os campos obrigatórios.")

# --- 3. HISTÓRICO (REMOVE 'NONE' AUTOMATICAMENTE) ---
with t_hist_vendas:
    st.subheader("📜 Gestão de Pedidos")
    with sqlite3.connect(DB_NAME) as conn:
        df_hist = pd.read_sql("SELECT * FROM vendas ORDER BY id DESC", conn)
    
    if not df_hist.empty:
        st.info("💡 Linhas vazias (None) são removidas automaticamente ao clicar em salvar.")
        edited_df = st.data_editor(
            df_hist, 
            use_container_width=True, 
            num_rows="dynamic", 
            hide_index=True,
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "valor_total": st.column_config.NumberColumn("Total R$", disabled=True, format="R$ %.2f"),
                "comissao": st.column_config.NumberColumn("Comissão R$", disabled=True, format="R$ %.2f")
            }
        )
        
        if st.button("💾 Salvar Alterações e Limpar"):
            # Remove linhas onde a empresa ou valor_unit são nulos/None
            edited_df = edited_df.dropna(subset=['empresa', 'valor_unit'])
            
            # Recalcula
            edited_df["valor_total"] = edited_df["qtd"] * edited_df["valor_unit"]
            # Calcula comissão baseada na linha original (ou fixa 10% se for nova)
            edited_df["comissao"] = edited_df["valor_total"] * 0.1 

            with sqlite3.connect(DB_NAME) as conn:
                conn.execute("DELETE FROM vendas")
                edited_df.to_sql("vendas", conn, if_exists="append", index=False)
            st.success("✨ Histórico limpo e atualizado!")
            st.rerun()

# --- 4. CADASTRO CLIENTE (CORRIGIDO) ---
with t_cad_cliente:
    with st.container(border=True):
        st.subheader("👤 Cadastro de Novo Cliente")
        with st.form("f_cli", clear_on_submit=True):
            cn = st.text_input("CNPJ")
            rs = st.text_input("Razão Social")
            tl = st.text_input("Telefone")
            em = st.text_input("E-mail")
            if st.form_submit_button("💾 Salvar Cliente"):
                if rs:
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.execute("INSERT INTO clientes (cnpj, razao_social, telefone, email) VALUES (?,?,?,?)",
                                     (cn, rs, tl, em))
                    st.success("✅ Cliente cadastrado!")
                else:
                    st.error("Razão Social é obrigatória.")

# --- 5. BANCO DE CLIENTES ---
with t_db_cliente:
    with sqlite3.connect(DB_NAME) as conn:
        df_c = pd.read_sql("SELECT * FROM clientes ORDER BY razao_social", conn)
    st.data_editor(df_c, use_container_width=True, num_rows="dynamic", hide_index=True)
