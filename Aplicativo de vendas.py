import os
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import io

# ================== CONFIGURAÇÕES ==================
SENHA_MESTRE = os.getenv("SENHA_APP", "1234")
DB_NAME = "vendas.db"

def check_password():
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
        return False
    return True

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
                cnpj TEXT, razao_social TEXT, nome_fantasia TEXT,
                inscricao_estadual TEXT, telefone TEXT, email TEXT, responsavel TEXT
            )
        """)
        conn.commit()

# ================== INTERFACE ==================
if check_password():
    init_db()
    st.set_page_config(page_title="Gestão Meira Nobre", layout="wide")
    st.title("📊 Sistema de Gestão Meira Nobre")

    # Criando as 5 abas conforme você pediu
    t_dash, t_venda, t_hist_vendas, t_cad_cliente, t_db_cliente = st.tabs([
        "📈 Dashboard", 
        "➕ Nova Venda", 
        "📜 Histórico Vendas", 
        "👤 Cadastro Cliente", 
        "📁 Banco de Dados Clientes"
    ])

    # --- 1. DASHBOARD ---
    with t_dash:
        with sqlite3.connect(DB_NAME) as conn:
            df_v = pd.read_sql("SELECT * FROM vendas", conn)
        if not df_v.empty:
            c1, c2 = st.columns(2)
            c1.metric("Faturamento Total", f"R$ {df_v['valor_total'].sum():,.2f}")
            c2.metric("Total Comissões", f"R$ {df_v['comissao'].sum():,.2f}")
            st.bar_chart(df_v.groupby("empresa")["valor_total"].sum())
        else:
            st.info("Sem dados para o Dashboard.")

    # --- 2. NOVA VENDA ---
    with t_venda:
        with st.form("f_venda", clear_on_submit=True):
            emp = st.text_input("Empresa")
            cli = st.text_input("Cliente")
            prod = st.text_input("Produto")
            col1, col2, col3 = st.columns(3)
            q = col1.number_input("Qtd", min_value=1)
            v = col2.number_input("Preço Unit.", min_value=0.0)
            p = col3.number_input("Comissão %", min_value=0, value=10)
            
            total = q * v
            comis = total * (p / 100)
            st.info(f"Resumo: Total R$ {total:,.2f} | Comissão R$ {comis:,.2f}")
            
            if st.form_submit_button("Salvar Venda"):
                dt = datetime.now().strftime("%d/%m/%Y %H:%M")
                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute("INSERT INTO vendas (data, empresa, cliente, produto, qtd, valor_unit, valor_total, comissao) VALUES (?,?,?,?,?,?,?,?)",
                                 (dt, emp, cli, prod, q, v, total, comis))
                st.success("Venda salva!")
                st.rerun()

    # --- 3. HISTÓRICO VENDAS ---
    with t_hist_vendas:
        with sqlite3.connect(DB_NAME) as conn:
            df_h = pd.read_sql("SELECT * FROM vendas ORDER BY id DESC", conn)
        st.dataframe(df_h, use_container_width=True)
        if not df_h.empty:
            buf = io.BytesIO()
            df_h.to_excel(buf, index=False, engine='xlsxwriter')
            st.download_button("📥 Baixar Excel Vendas", buf.getvalue(), "vendas.xlsx", "application/vnd.ms-excel")

    # --- 4. CADASTRO CLIENTE ---
    with t_cad_cliente:
        with st.form("f_cli", clear_on_submit=True):
            cnpj = st.text_input("CNPJ")
            razao = st.text_input("Razão Social")
            fant = st.text_input("Nome Fantasia")
            tel = st.text_input("Telefone")
            email = st.text_input("E-mail")
            resp = st.text_input("Responsável")
            
            if st.form_submit_button("Cadastrar Cliente"):
                if razao:
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.execute("INSERT INTO clientes (cnpj, razao_social, nome_fantasia, telefone, email, responsavel) VALUES (?,?,?,?,?,?)",
                                     (cnpj, razao, fant, tel, email, resp))
                    st.success("Cliente cadastrado!")
                    st.rerun()
                else:
                    st.error("Razão Social é obrigatória!")

    # --- 5. BANCO DE DADOS CLIENTES ---
    with t_db_cliente:
        with sqlite3.connect(DB_NAME) as conn:
            df_c = pd.read_sql("SELECT * FROM clientes ORDER BY razao_social", conn)
        st.dataframe(df_c, use_container_width=True)
        if not df_c.empty:
            buf_c = io.BytesIO()
            df_c.to_excel(buf_c, index=False, engine='xlsxwriter')
            st.download_button("📥 Baixar Excel Clientes", buf_c.getvalue(), "clientes.xlsx", "application/vnd.ms-excel")
