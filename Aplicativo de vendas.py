

import os
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from io import BytesIO

# ===== PDF =====
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

# ================== CONFIG ==================
st.set_page_config(page_title="Sistema Meira Nobre", layout="wide")
DB_NAME = "vendas.db"

# ================== BANCO ==================
def run_db(query, params=(), select=False):
    with sqlite3.connect(DB_NAME) as conn:
        if select:
            return pd.read_sql(query, conn)
        conn.execute(query, params)
        conn.commit()

def init_db():
    run_db("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE,
        senha TEXT
    )
    """)
    
    run_db("""
    CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT,
        empresa TEXT,
        cliente TEXT,
        produto TEXT,
        qtd INTEGER,
        valor_unit REAL,
        valor_total REAL,
        comissao REAL
    )
    """)

    run_db("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        razao_social TEXT,
        cnpj TEXT,
        telefone TEXT,
        email TEXT,
        categoria TEXT
    )
    """)

    # usuário padrão
    users = run_db("SELECT * FROM usuarios", select=True)
    if users.empty:
        run_db(
            "INSERT INTO usuarios (usuario, senha) VALUES (?,?)",
            ("admin", "1234")
        )

init_db()

# ================== LOGIN ==================
if "logado" not in st.session_state:
    st.title("🔐 Login")
    u = st.text_input("Usuário")
    s = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        df = run_db(
            "SELECT * FROM usuarios WHERE usuario=? AND senha=?",
            (u, s),
            select=True
        )
        if not df.empty:
            st.session_state["logado"] = True
            st.session_state["usuario"] = u
            st.rerun()
        else:
            st.error("Credenciais inválidas")
    st.stop()

# ================== HEADER ==================
st.title("📊 Sistema Meira Nobre")
st.caption(f"Usuário logado: **{st.session_state['usuario']}**")

tabs = st.tabs([
    "📈 Dashboard",
    "➕ Nova Venda",
    "📜 Histórico",
    "👤 Novo Cliente",
    "📁 Clientes"
])

# ================== DASHBOARD ==================
with tabs[0]:
    dfv = run_db("SELECT * FROM vendas", select=True)

    if not dfv.empty:
        dfv["valor_total"] = pd.to_numeric(dfv["valor_total"], errors="coerce").fillna(0)
        dfv["comissao"] = pd.to_numeric(dfv["comissao"], errors="coerce").fillna(0)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 Faturamento", f"R$ {dfv['valor_total'].sum():,.2f}")
        c2.metric("🤝 Comissões", f"R$ {dfv['comissao'].sum():,.2f}")
        c3.metric("📦 Pedidos", len(dfv))
        c4.metric("🎯 Ticket Médio", f"R$ {dfv['valor_total'].mean():,.2f}")

        st.divider()

        g1, g2 = st.columns(2)
        g1.subheader("Vendas por Empresa")
        g1.bar_chart(dfv.groupby("empresa")["valor_total"].sum())

        g2.subheader("Vendas por Cliente")
        g2.bar_chart(dfv.groupby("cliente")["valor_total"].sum())

        # ===== EXPORTAÇÃO =====
        st.divider()
        e1, e2 = st.columns(2)

        # Excel
        buffer = BytesIO()
        dfv.to_excel(buffer, index=False)
        e1.download_button(
            "⬇️ Baixar Excel",
            buffer.getvalue(),
            "relatorio_vendas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

        # PDF
        def gerar_pdf(df):
            file = "relatorio_vendas.pdf"
            doc = SimpleDocTemplate(file, pagesize=A4)
            styles = getSampleStyleSheet()
            elementos = [
                Paragraph("Relatório de Vendas - Meira Nobre", styles["Title"]),
                Spacer(1, 12)
            ]

            tabela = [df.columns.tolist()] + df.values.tolist()
            elementos.append(Table(tabela))
            doc.build(elementos)
            return file

        if e2.button("📄 Gerar PDF", use_container_width=True):
            pdf = gerar_pdf(dfv)
            with open(pdf, "rb") as f:
                e2.download_button(
                    "⬇️ Baixar PDF",
                    f,
                    file_name="relatorio_vendas.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
    else:
        st.info("Nenhuma venda registrada")

# ================== NOVA VENDA ==================
with tabs[1]:
    st.subheader("➕ Registrar Venda")
    with st.form("venda"):
        empresa = st.text_input("Empresa")
        cliente = st.text_input("Cliente")
        produto = st.text_input("Produto")
        c1, c2, c3 = st.columns(3)
        qtd = c1.number_input("Quantidade", 1)
        valor = c2.number_input("Valor Unitário", 0.0)
        com = c3.number_input("Comissão (%)", 10)

        if st.form_submit_button("Salvar"):
            total = qtd * valor
            comissao = total * (com / 100)
            run_db("""
                INSERT INTO vendas 
                (data, empresa, cliente, produto, qtd, valor_unit, valor_total, comissao)
                VALUES (?,?,?,?,?,?,?,?)
            """, (
                datetime.now().strftime("%d/%m/%Y"),
                empresa, cliente, produto,
                qtd, valor, total, comissao
            ))
            st.success("Venda registrada!")
            st.rerun()

# ================== HISTÓRICO ==================
with tabs[2]:
    df = run_db("SELECT * FROM vendas", select=True)
    edited = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Salvar Alterações"):
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("DELETE FROM vendas")
            edited.to_sql("vendas", conn, if_exists="append", index=False)
        st.success("Atualizado!")
        st.rerun()

# ================== NOVO CLIENTE ==================
with tabs[3]:
    with st.form("cliente"):
        rs = st.text_input("Razão Social")
        cnpj = st.text_input("CNPJ")
        cat = st.selectbox("Categoria", ["Varejo", "Atacado", "Distribuidor", "Outros"])
        if st.form_submit_button("Salvar"):
            run_db(
                "INSERT INTO clientes (razao_social, cnpj, categoria) VALUES (?,?,?)",
                (rs, cnpj, cat)
            )
            st.success("Cliente cadastrado")

# ================== CLIENTES ==================
with tabs[4]:
    dfc = run_db("SELECT * FROM clientes", select=True)
    edited = st.data_editor(dfc, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Salvar Clientes"):
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("DELETE FROM clientes")
            edited.to_sql("clientes", conn, if_exists="append", index=False)
        st.success("Clientes atualizados")
        st.rerun()

