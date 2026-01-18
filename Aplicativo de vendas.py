import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime
from io import BytesIO

# PDF
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

# ================= CONFIG =================
st.set_page_config("Gestão Meira Nobre", layout="wide")
DB = "vendas.db"

# ================= DB =================
def run_db(query, params=(), select=False):
    with sqlite3.connect(DB) as conn:
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
    )""")

    run_db("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        razao_social TEXT,
        cnpj TEXT,
        categoria TEXT
    )""")

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
    )""")

    if run_db("SELECT * FROM usuarios", select=True).empty:
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
    "📈 Dashboard",
    "➕ Nova Venda",
    "👤 Clientes",
    "👥 Usuários"
])

# ================= DASHBOARD =================
with tabs[0]:
    dfv = run_db("SELECT * FROM vendas", select=True)

    if not dfv.empty:
        dfv[["valor_total", "comissao"]] = dfv[["valor_total", "comissao"]].apply(
            pd.to_numeric, errors="coerce"
        ).fillna(0)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Faturamento", f"R$ {dfv.valor_total.sum():,.2f}")
        c2.metric("Comissões", f"R$ {dfv.comissao.sum():,.2f}")
        c3.metric("Pedidos", len(dfv))
        c4.metric("Ticket Médio", f"R$ {dfv.valor_total.mean():,.2f}")

        st.divider()

        g1, g2 = st.columns(2)
        g1.bar_chart(dfv.groupby("empresa")["valor_total"].sum())
        g2.bar_chart(dfv.groupby("cliente")["valor_total"].sum())

        # ===== EXPORT EXCEL =====
        buffer = BytesIO()
        dfv.to_excel(buffer, index=False, engine="xlsxwriter")
        buffer.seek(0)

        e1, e2 = st.columns(2)

        e1.download_button(
            "📥 Baixar Excel",
            data=buffer,
            file_name="vendas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

        # ===== PDF =====
        def gerar_pdf(df):
            path = "/tmp/vendas.pdf"
            doc = SimpleDocTemplate(path, pagesize=A4)
            styles = getSampleStyleSheet()

            elems = [
                Paragraph("Relatório de Vendas – Meira Nobre", styles["Title"]),
                Spacer(1, 12),
                Table([df.columns.tolist()] + df.values.tolist())
            ]
            doc.build(elems)
            return path

        if e2.button("📄 Gerar PDF", use_container_width=True):
            pdf = gerar_pdf(dfv)
            with open(pdf, "rb") as f:
                e2.download_button(
                    "⬇️ Baixar PDF",
                    data=f,
                    file_name="vendas.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
    else:
        st.info("Nenhuma venda registrada ainda")

# ================= NOVA VENDA =================
with tabs[1]:
    st.subheader("📝 Registrar Nova Venda")

    clientes = run_db("SELECT razao_social FROM clientes", select=True)

    c1, c2 = st.columns(2)
    emp = c1.text_input("Empresa")
    cli = c2.selectbox(
        "Cliente",
        clientes["razao_social"] if not clientes.empty else []
    )

    prod = st.text_input("Produto")

    q1, q2, q3 = st.columns(3)
    qtd = q1.number_input("Qtd", min_value=1, value=1)
    prc = q2.number_input("Preço Unit", min_value=0.0)
    com = q3.number_input("Comissão %", value=10)

    total = qtd * prc
    comissao = total * (com / 100)

    if st.button("🚀 Salvar Venda", use_container_width=True):
        if emp and cli and prc > 0:
            run_db("""
                INSERT INTO vendas
                (data, empresa, cliente, produto, qtd, valor_unit, valor_total, comissao)
                VALUES (?,?,?,?,?,?,?,?)
            """, (
                datetime.now().strftime("%d/%m/%Y"),
                emp, cli, prod, qtd, prc, total, comissao
            ))
            st.success("Venda registrada")
            st.rerun()
        else:
            st.warning("Preencha todos os campos obrigatórios")

    st.divider()
    st.subheader("📜 Pedidos Registrados")

    dfv = run_db("SELECT * FROM vendas", select=True)

    if not dfv.empty:
        edit = st.data_editor(
            dfv,
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic"
        )

        if st.button("💾 Sincronizar Pedidos"):
            with sqlite3.connect(DB) as conn:
                conn.execute("DELETE FROM vendas")
                edit.to_sql("vendas", conn, index=False, if_exists="append")
            st.success("Pedidos atualizados")
            st.rerun()
    else:
        st.info("Nenhuma venda cadastrada")

# ================= CLIENTES =================
with tabs[2]:
    st.subheader("👤 Cadastro de Cliente")

    c1, c2 = st.columns(2)
    rs = c1.text_input("Razão Social")
    cj = c2.text_input("CNPJ")

    cat = st.selectbox("Categoria", ["Varejo", "Atacado", "Supermercado", "Outros"])

    if st.button("Salvar Cliente"):
        run_db(
            "INSERT INTO clientes (razao_social, cnpj, categoria) VALUES (?,?,?)",
            (rs, cj, cat)
        )
        st.success("Cliente cadastrado")
        st.rerun()

    st.divider()
    st.subheader("📁 Banco de Clientes")

    dfc = run_db("SELECT * FROM clientes", select=True)

    if not dfc.empty:
        edit = st.data_editor(
            dfc,
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic"
        )

        if st.button("💾 Sincronizar Clientes"):
            with sqlite3.connect(DB) as conn:
                conn.execute("DELETE FROM clientes")
                edit.to_sql("clientes", conn, index=False, if_exists="append")
            st.success("Clientes atualizados")
            st.rerun()
    else:
        st.info("Nenhum cliente cadastrado")

# ================= USUÁRIOS =================
with tabs[3]:
    st.subheader("➕ Novo Usuário")

    u = st.text_input("Usuário novo")
    s = st.text_input("Senha nova", type="password")

    if st.button("Criar Usuário"):
        try:
            run_db(
                "INSERT INTO usuarios (usuario, senha) VALUES (?,?)",
                (u, s)
            )
            st.success("Usuário criado")
        except:
            st.error("Usuário já existe")

    st.divider()
    st.subheader("📋 Usuários Cadastrados")
    st.dataframe(run_db("SELECT usuario FROM usuarios", select=True))
