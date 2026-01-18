

import os
import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime

# ================= PDF =================
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

# ================= CONFIG =================
st.set_page_config("Gestão Meira Nobre", layout="wide")
DB_NAME = "vendas.db"

# ================= BANCO =================
def run_db(query, params=(), select=False):
    with sqlite3.connect(DB_NAME) as conn:
        if select:
            return pd.read_sql(query, conn, params=params)
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
        categoria TEXT
    )
    """)

    # cria admin se não existir
    u = run_db("SELECT * FROM usuarios", select=True)
    if u.empty:
        run_db(
            "INSERT INTO usuarios (usuario, senha) VALUES (?,?)",
            ("admin", "1234")
        )

init_db()

# ================= LOGIN =================
if "user" not in st.session_state:
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
            st.session_state["user"] = u
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")

    st.stop()

# ================= UI =================
st.title("📊 Sistema Meira Nobre")
tabs = st.tabs([
    "📈 Dashboards",
    "➕ Nova Venda",
    "📜 Histórico",
    "👤 Novo Cliente",
    "📁 Banco de Clientes"
])

# ================= DASH =================
with tabs[0]:
    dfv = run_db("SELECT * FROM vendas", select=True)

    if not dfv.empty:
        dfv["valor_total"] = pd.to_numeric(dfv["valor_total"], errors="coerce").fillna(0)
        dfv["comissao"] = pd.to_numeric(dfv["comissao"], errors="coerce").fillna(0)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Faturamento", f"R$ {dfv.valor_total.sum():,.2f}")
        c2.metric("Comissões", f"R$ {dfv.comissao.sum():,.2f}")
        c3.metric("Pedidos", len(dfv))
        c4.metric("Ticket Médio", f"R$ {dfv.valor_total.mean():,.2f}")

        st.divider()

        g1, g2 = st.columns(2)
        g1.subheader("Vendas por Empresa")
        g1.bar_chart(dfv.groupby("empresa")["valor_total"].sum())

        g2.subheader("Vendas por Cliente")
        g2.bar_chart(dfv.groupby("cliente")["valor_total"].sum())

        # EXPORTAÇÃO
        e1, e2 = st.columns(2)

        e1.download_button(
            "📥 Exportar Excel",
            data=dfv.to_excel(index=False, engine="xlsxwriter"),
            file_name="vendas.xlsx"
        )

        def gerar_pdf(df):
            path = "/tmp/vendas.pdf"
            doc = SimpleDocTemplate(path, pagesize=A4)
            styles = getSampleStyleSheet()
            elements = [Paragraph("Relatório de Vendas", styles["Title"]), Spacer(1, 12)]
            elements.append(Table([df.columns.tolist()] + df.values.tolist()))
            doc.build(elements)
            return path

        if e2.button("📄 Gerar PDF"):
            pdf = gerar_pdf(dfv)
            with open(pdf, "rb") as f:
                e2.download_button(
                    "⬇️ Baixar PDF",
                    data=f,
                    file_name="vendas.pdf",
                    mime="application/pdf"
                )

# ================= NOVA VENDA =================
with tabs[1]:
    emp = st.text_input("Empresa")
    cli = st.text_input("Cliente")
    prod = st.text_input("Produto")

    qtd = st.number_input("Qtd", min_value=1, value=1)
    prc = st.number_input("Preço Unit", min_value=0.0)
    com = st.number_input("Comissão %", value=10)

    total = qtd * prc
    comissao = total * (com / 100)

    if st.button("Salvar Venda"):
        run_db(
            "INSERT INTO vendas VALUES (NULL,?,?,?,?,?,?,?,?)",
            (datetime.now().strftime("%d/%m/%Y"), emp, cli, prod, qtd, prc, total, comissao)
        )
        st.success("Venda registrada")
        st.rerun()

# ================= HISTÓRICO =================
with tabs[2]:
    df = run_db("SELECT * FROM vendas", select=True)
    edit = st.data_editor(df, num_rows="dynamic", hide_index=True)
    if st.button("Sincronizar"):
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("DELETE FROM vendas")
            edit.to_sql("vendas", conn, index=False, if_exists="append")
        st.success("Atualizado")
        st.rerun()

# ================= CLIENTES =================
with tabs[3]:
    rs = st.text_input("Razão Social")
    cj = st.text_input("CNPJ")
    cat = st.selectbox("Categoria", ["Varejo", "Atacado", "Outros"])
    if st.button("Salvar Cliente"):
        run_db(
            "INSERT INTO clientes VALUES (NULL,?,?,?)",
            (rs, cj, cat)
        )
        st.success("Cliente cadastrado")

with tabs[4]:
    dfc = run_db("SELECT * FROM clientes", select=True)
    edit = st.data_editor(dfc, num_rows="dynamic", hide_index=True)
    if st.button("Sincronizar Clientes"):
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("DELETE FROM clientes")
            edit.to_sql("clientes", conn, index=False, if_exists="append")
        st.success("Atualizado")
        st.rerun()
