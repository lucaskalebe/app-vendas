

import os, sqlite3, hashlib
import streamlit as st
import pandas as pd
from datetime import datetime

# PDF
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

# ================== CONFIG ==================
st.set_page_config("Gestão Meira Nobre", layout="wide")
DB_NAME = "vendas.db"

# ================== DB CORE ==================
def run_db(query, params=(), is_select=False):
    with sqlite3.connect(DB_NAME) as conn:
        if is_select:
            return pd.read_sql(query, conn)
        conn.execute(query, params)
        conn.commit()

def init_db():
    # vendas
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
        comissao REAL,
        segmento TEXT
    )
    """)

    # clientes
    run_db("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cnpj TEXT,
        razao_social TEXT,
        telefone TEXT,
        email TEXT,
        categoria TEXT
    )
    """)

    # usuários
    run_db("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE,
        senha_hash TEXT
    )
    """)

    # migrações
    for col in ["segmento"]:
        cols = run_db("PRAGMA table_info(vendas)", is_select=True)["name"].tolist()
        if col not in cols:
            run_db(f"ALTER TABLE vendas ADD COLUMN {col} TEXT DEFAULT 'Não Informado'")

    # cria admin padrão
    hash_admin = hashlib.sha256("admin123".encode()).hexdigest()
    run_db(
        "INSERT OR IGNORE INTO usuarios (usuario, senha_hash) VALUES (?,?)",
        ("admin", hash_admin)
    )

# ================== LOGIN ==================
def hash_senha(s):
    return hashlib.sha256(s.encode()).hexdigest()

if "usuario_logado" not in st.session_state:
    st.title("🔐 Login – Sistema Meira Nobre")

    u = st.text_input("Usuário")
    s = st.text_input("Senha", type="password")

    if st.button("Entrar", use_container_width=True):
        dfu = run_db(
            "SELECT * FROM usuarios WHERE usuario=? AND senha_hash=?",
            (u, hash_senha(s)),
            is_select=True
        )
        if not dfu.empty:
            st.session_state["usuario_logado"] = u
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")

    st.caption("Login padrão: admin | senha: admin123")
    st.stop()

# ================== START ==================
init_db()

st.title("📊 Sistema Meira Nobre")
st.caption(f"Usuário logado: **{st.session_state['usuario_logado']}**")

tabs = st.tabs([
    "📈 Dashboards",
    "➕ Nova Venda",
    "📜 Histórico",
    "👤 Novo Cliente",
    "📁 Banco de Clientes"
])

# ================== DASHBOARD ==================
with tabs[0]:
    dfv = run_db("SELECT * FROM vendas", is_select=True)
    dfc = run_db("SELECT * FROM clientes", is_select=True)

    if not dfv.empty:
        for col in ["qtd", "valor_unit", "valor_total", "comissao"]:
            dfv[col] = pd.to_numeric(dfv[col], errors="coerce").fillna(0)

        m = st.columns(4)
        m[0].metric("💰 Faturamento", f"R$ {dfv['valor_total'].sum():,.2f}")
        m[1].metric("🤝 Comissões", f"R$ {dfv['comissao'].sum():,.2f}")
        m[2].metric("📦 Pedidos", len(dfv))
        m[3].metric("🎯 Ticket Médio", f"R$ {dfv['valor_total'].mean():,.2f}")

        st.divider()

        g1, g2 = st.columns(2)
        g1.subheader("Vendas por Empresa")
        g1.bar_chart(dfv.groupby("empresa")["valor_total"].sum())

        g2.subheader("Vendas por Segmento")
        g2.bar_chart(dfv.groupby("segmento")["valor_total"].sum())

        # ===== EXPORTAÇÕES =====
        st.divider()
        st.subheader("📤 Exportações")

        c1, c2 = st.columns(2)

        # EXCEL
        c1.download_button(
            "⬇️ Baixar Excel",
            data=dfv.to_csv(index=False).encode("utf-8"),
            file_name="vendas_meira_nobre.csv",
            mime="text/csv",
            use_container_width=True
        )

        # PDF
        def gerar_pdf(df):
            path = "/tmp/relatorio_vendas.pdf"
            doc = SimpleDocTemplate(path, pagesize=A4)
            styles = getSampleStyleSheet()

            elementos = []
            elementos.append(Paragraph("Relatório de Vendas – Meira Nobre", styles["Title"]))
            elementos.append(Spacer(1, 12))
            elementos.append(Paragraph(
                f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                styles["Normal"]
            ))
            elementos.append(Spacer(1, 12))

            tabela = [df.columns.tolist()] + df.values.tolist()
            elementos.append(Table(tabela))

            doc.build(elementos)
            return path

        if c2.button("📄 Gerar PDF", use_container_width=True):
            pdf = gerar_pdf(dfv)
            with open(pdf, "rb") as f:
                c2.download_button(
                    "⬇️ Baixar PDF",
                    data=f,
                    file_name="relatorio_vendas.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

    st.subheader("🟣 Inteligência de Clientes")
    if not dfc.empty:
        st.bar_chart(dfc["categoria"].value_counts())

# ================== NOVA VENDA ==================
with tabs[1]:
    with st.container(border=True):
        st.subheader("📝 Registrar Pedido")

        emp, cli = st.columns(2)
        empresa = emp.text_input("Empresa")
        cliente = cli.text_input("Cliente")

        produto = st.text_input("Produto")
        segmento = st.selectbox(
            "Segmento",
            ["Varejo", "Atacado", "Supermercado", "Food Service", "Hotelaria", "Outros"]
        )

        q1, q2, q3 = st.columns(3)
        qtd = q1.number_input("Qtd", min_value=1, value=1)
        prc = q2.number_input("Preço Unit.", min_value=0.0)
        com = q3.number_input("Comissão %", value=10)

        total = qtd * prc
        com_val = total * (com / 100)

        if st.button("🚀 Salvar Venda", use_container_width=True):
            if empresa and cliente and produto and prc > 0:
                run_db("""
                INSERT INTO vendas
                (data, empresa, cliente, produto, qtd, valor_unit, valor_total, comissao, segmento)
                VALUES (?,?,?,?,?,?,?,?,?)
                """, (
                    datetime.now().strftime("%d/%m/%Y"),
                    empresa, cliente, produto, qtd, prc, total, com_val, segmento
                ))
                st.success("Venda registrada com sucesso!")
                st.rerun()

# ================== HISTÓRICO / CLIENTES ==================
for i, table, label in zip([2, 4], ["vendas", "clientes"], ["Vendas", "Clientes"]):
    with tabs[i]:
        df = run_db(f"SELECT * FROM {table}", is_select=True)

        edited = st.data_editor(
            df,
            num_rows="dynamic",
            hide_index=True,
            use_container_width=True,
            key=f"ed_{table}"
        )

        if st.button(f"💾 Sincronizar {label}"):
            edited = edited.drop(columns=["id"], errors="ignore")
            edited = edited.fillna("Não Informado")

            with sqlite3.connect(DB_NAME) as conn:
                conn.execute(f"DELETE FROM {table}")
                edited.to_sql(table, conn, if_exists="append", index=False)

            st.success("Dados atualizados!")
            st.rerun()

# ================== NOVO CLIENTE ==================
with tabs[3]:
    with st.form("f_cli", clear_on_submit=True):
        st.subheader("👤 Cadastro de Cliente")

        rs = st.text_input("Razão Social")
        cj = st.text_input("CNPJ")
        cat = st.selectbox("Categoria", ["Varejo", "Atacado", "Supermercado", "Outros"])

        if st.form_submit_button("Salvar Cliente"):
            if rs:
                run_db(
                    "INSERT INTO clientes (razao_social, cnpj, categoria) VALUES (?,?,?)",
                    (rs, cj, cat)
                )
                st.success("Cliente cadastrado!")

