

import os
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# ================== CONFIGURAÇÕES E ESTILO ==================
st.set_page_config(page_title="Gestão Meira Nobre", layout="wide")

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
        cursor = conn.cursor()
        # Tabelas base
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
                cnpj TEXT, razao_social TEXT, telefone TEXT, email TEXT, categoria TEXT
            )
        """)
        
        # Migração automática para garantir que as colunas existam (evita KeyError)
        cursor.execute("PRAGMA table_info(clientes)")
        cols_c = [c[1] for c in cursor.fetchall()]
        for col in ['telefone', 'email', 'categoria']:
            if col not in cols_c:
                cursor.execute(f"ALTER TABLE clientes ADD COLUMN {col} TEXT DEFAULT 'Não Informado'")
        conn.commit()

# ================== INTERFACE PRINCIPAL ==================
if check_password():
    init_db()
    st.title("📊 Sistema de Gestão Meira Nobre")

    t_dash, t_venda, t_hist_vendas, t_cad_cliente, t_db_cliente = st.tabs([
        "📈 Dashboard Pro", "➕ Nova Venda", "📜 Histórico e Edição", "👤 Cadastro Cliente", "📁 Banco de Dados Clientes"
    ])

    # --- 1. DASHBOARD ---
    with t_dash:
        with sqlite3.connect(DB_NAME) as conn:
            df_v = pd.read_sql("SELECT * FROM vendas", conn)
            df_c = pd.read_sql("SELECT * FROM clientes", conn)

        if not df_v.empty:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Faturamento Total", f"R$ {df_v['valor_total'].sum():,.2f}")
            m2.metric("Total Comissões", f"R$ {df_v['comissao'].sum():,.2f}")
            m3.metric("Ticket Médio", f"R$ {df_v['valor_total'].mean():,.2f}")
            m4.metric("Qtd Pedidos", len(df_v))
            
            st.divider()
            g1, g2 = st.columns(2)
            with g1:
                st.subheader("Vendas por Representada (R$)")
                st.bar_chart(df_v.groupby("empresa")["valor_total"].sum())
            with g2:
                st.subheader("Vendas por Cliente (R$)")
                st.bar_chart(df_v.groupby("cliente")["valor_total"].sum())
        else:
            st.info("Lance vendas para ativar o Dashboard.")
        
        st.divider()
        st.subheader("🟣 Inteligência de Clientes")
        if not df_c.empty:
            c_col1, c_col2 = st.columns(2)
            with c_col1:
                st.write("**Resumo por Categoria**")
                st.write(df_c['categoria'].value_counts())
            with c_col2:
                st.write("**Distribuição Visual**")
                st.bar_chart(df_c.groupby("categoria").size())

    # --- 2. NOVA VENDA ---
    with t_venda:
        with st.container(border=True):
            st.subheader("📝 Registrar Novo Pedido")
            c_top1, c_top2 = st.columns(2)
            emp = c_top1.text_input("🏢 Empresa Representada")
            cli = c_top2.text_input("🏬 Cliente / Loja")
            prod = st.text_input("📦 Descrição do Produto")
            
            c1, c2, c3 = st.columns(3)
            q = c1.number_input("🔢 Quantidade", min_value=1, value=1)
            v = c2.number_input("💰 Preço Unitário (R$)", min_value=0.0, format="%.2f")
            p = c3.number_input("📈 Comissão %", min_value=0, value=10)
            
            total_calc = q * v
            comis_calc = total_calc * (p / 100)
            
            st.divider()
            res1, res2 = st.columns(2)
            res1.metric("Valor Total", f"R$ {total_calc:,.2f}")
            res2.metric("Sua Comissão", f"R$ {comis_calc:,.2f}")

            if st.button("🚀 Salvar Venda", use_container_width=True):
                if emp and cli and v > 0:
                    dt = datetime.now().strftime("%d/%m/%Y %H:%M")
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.execute("""
                            INSERT INTO vendas (data, empresa, cliente, produto, qtd, valor_unit, valor_total, comissao) 
                            VALUES (?,?,?,?,?,?,?,?)
                        """, (dt, emp, cli, prod, q, v, total_calc, comis_calc))
                    st.success("✅ Venda registrada!")
                    st.rerun()
                else:
                    st.error("⚠️ Preencha os campos obrigatórios.")

    # --- 3. HISTÓRICO ---
    with t_hist_vendas:
        st.subheader("📜 Gestão de Pedidos")
        with sqlite3.connect(DB_NAME) as conn:
            df_hist = pd.read_sql("SELECT * FROM vendas ORDER BY id DESC", conn)
        
        if not df_hist.empty:
            edited_df = st.data_editor(df_hist, use_container_width=True, num_rows="dynamic", hide_index=True)
            if st.button("💾 Confirmar Alterações"):
                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute("DELETE FROM vendas")
                    edited_df.to_sql("vendas", conn, if_exists="append", index=False)
                st.success("✨ Histórico atualizado!")
                st.rerun()

    # --- 4. CADASTRO CLIENTE ---
    with t_cad_cliente:
        with st.form("form_cliente", clear_on_submit=True):
            st.subheader("👤 Novo Cliente")
            f1, f2 = st.columns(2)
            rs = f1.text_input("Razão Social")
            cj = f2.text_input("CNPJ")
            tel = f1.text_input("Telefone")
            email = f2.text_input("E-mail")
            cat = st.selectbox("Categoria", ["Varejo", "Atacado", "Supermercado", "Boutique", "Outros"])
            if st.form_submit_button("💾 Salvar Cliente"):
                if rs:
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.execute("INSERT INTO clientes (razao_social, cnpj, telefone, email, categoria) VALUES (?,?,?,?,?)", 
                                     (rs, cj, tel, email, cat))
                    st.success("Cliente cadastrado!")
                else:
                    st.error("Razão Social é obrigatória.")

    # --- 5. BANCO DE DADOS CLIENTES ---
    with t_db_cliente:
        with sqlite3.connect(DB_NAME) as conn:
            df_c_list = pd.read_sql("SELECT * FROM clientes", conn)
        st.dataframe(df_c_list, use_container_width=True)
