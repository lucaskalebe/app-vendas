

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

    # Tabela atualizada com a coluna SEGMENTO
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
    )""")

    if run_db("SELECT * FROM usuarios", select=True).empty:
        run_db("INSERT INTO usuarios (usuario, senha) VALUES (?,?)", ("admin", "1234"))

init_db()

# ================= LOGIN =================
if "user" not in st.session_state:
    st.title("🔐 Login")
    u = st.text_input("Usuário")
    s = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        df = run_db("SELECT * FROM usuarios WHERE usuario=? AND senha=?", (u, s), select=True)
        if not df.empty:
            st.session_state["user"] = u
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")
    st.stop()

# ================= UI =================
st.title("📊 Sistema Meira Nobre")
tabs = st.tabs(["📈 Dashboard", "➕ Nova Venda", "👤 Clientes", "👥 Usuários"])

# ================= DASHBOARD =================
with tabs[0]:
    dfv = run_db("SELECT * FROM vendas", select=True)

    if not dfv.empty:
        # Tratamento rigoroso de tipos para evitar o erro ValueError
        cols_financeiras = ["valor_total", "comissao", "qtd", "valor_unit"]
        for col in cols_financeiras:
            dfv[col] = pd.to_numeric(dfv[col], errors="coerce").fillna(0)

        # KPIs
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Faturamento", f"R$ {dfv.valor_total.sum():,.2f}")
        c2.metric("Comissões", f"R$ {dfv.comissao.sum():,.2f}")
        c3.metric("Pedidos", len(dfv))
        ticket = dfv.valor_total.mean() if not dfv.empty else 0
        c4.metric("Ticket Médio", f"R$ {ticket:,.2f}")

        st.divider()

        # Gráficos em Tempo Real
        g1, g2 = st.columns(2)
        with g1:
            st.write("### Faturamento por Empresa")
            st.bar_chart(dfv.groupby("empresa")["valor_total"].sum())
        with g2:
            st.write("### Faturamento por Segmento")
            if "segmento" in dfv.columns and not dfv["segmento"].isnull().all():
                st.bar_chart(dfv.groupby("segmento")["valor_total"].sum())
            else:
                st.info("Cadastre vendas com 'Segmento' para ver este gráfico.")

        # Exportação Excel
        buffer = BytesIO()
        dfv.to_excel(buffer, index=False, engine="xlsxwriter")
        buffer.seek(0)
        
        e1, e2 = st.columns(2)
        e1.download_button("📥 Baixar Excel", data=buffer, file_name="vendas.xlsx", use_container_width=True)

        # PDF
        def gerar_pdf(df):
            path = "relatorio_vendas.pdf"
            doc = SimpleDocTemplate(path, pagesize=A4)
            styles = getSampleStyleSheet()
            data_list = [df.columns.tolist()] + df.values.tolist()
            elems = [Paragraph("Relatório de Vendas", styles["Title"]), Spacer(1, 12), Table(data_list)]
            doc.build(elems)
            return path

        if e2.button("📄 Gerar PDF", use_container_width=True):
            pdf_path = gerar_pdf(dfv)
            with open(pdf_path, "rb") as f:
                st.download_button("⬇️ Clique para Baixar PDF", f, file_name="vendas.pdf", use_container_width=True)
    else:
        st.info("Nenhuma venda registrada ainda")

# ================= NOVA VENDA =================
with tabs[1]:
    st.subheader("📝 Registrar Nova Venda")
    clientes_db = run_db("SELECT razao_social FROM clientes", select=True)

    c1, c2 = st.columns(2)
    emp = c1.text_input("Empresa")
    cli = c2.selectbox("Cliente", clientes_db["razao_social"] if not clientes_db.empty else ["Nenhum cadastrado"])
    
    prod = st.text_input("Produto")
    seg = st.selectbox("Segmento", ["Tecnologia", "Hardware", "Software", "Periféricos", "Varejo", "Outros"])

    q1, q2, q3 = st.columns(3)
    qtd = q1.number_input("Qtd", min_value=1, value=1)
    prc = q2.number_input("Preço Unit", min_value=0.0, format="%.2f")
    com_p = q3.number_input("Comissão %", value=10)

    if st.button("🚀 Salvar Venda", use_container_width=True):
        if emp and cli != "Nenhum cadastrado" and prc > 0:
            total = qtd * prc
            valor_com = total * (com_p / 100)
            run_db("""
                INSERT INTO vendas (data, empresa, cliente, produto, qtd, valor_unit, valor_total, comissao, segmento)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (datetime.now().strftime("%d/%m/%Y"), emp, cli, prod, qtd, prc, total, valor_com, seg))
            st.success("Venda registrada!")
            st.rerun()
        else:
            st.warning("Preencha todos os campos")

    st.divider()
    st.subheader("📜 Pedidos Registrados")
    dfv_edit = run_db("SELECT * FROM vendas", select=True)
    if not dfv_edit.empty:
        edit_v = st.data_editor(dfv_edit, hide_index=True, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Sincronizar Pedidos"):
            with sqlite3.connect(DB) as conn:
                conn.execute("DELETE FROM vendas")
                edit_v.to_sql("vendas", conn, index=False, if_exists="append")
            st.success("Dados sincronizados")
            st.rerun()

# ================= CLIENTES =================
with tabs[2]:
    st.subheader("👤 Cadastro de Cliente")
    c1, c2 = st.columns(2)
    rs = c1.text_input("Razão Social")
    cj = c2.text_input("CNPJ")
    cat = st.selectbox("Categoria", ["Varejo", "Atacado", "Supermercado", "Outros"])

    if st.button("Salvar Cliente"):
        if rs:
            run_db("INSERT INTO clientes (razao_social, cnpj, categoria) VALUES (?,?,?)", (rs, cj, cat))
            st.success("Cliente cadastrado")
            st.rerun()

    st.divider()
    dfc = run_db("SELECT * FROM clientes", select=True)
    if not dfc.empty:
        edit_c = st.data_editor(dfc, hide_index=True, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Sincronizar Clientes"):
            with sqlite3.connect(DB) as conn:
                conn.execute("DELETE FROM clientes")
                edit_c.to_sql("clientes", conn, index=False, if_exists="append")
            st.success("Clientes atualizados")
            st.rerun()

# ================= USUÁRIOS =================
with tabs[3]:
    st.subheader("➕ Novo Usuário")
    u_new = st.text_input("Usuário novo")
    s_new = st.text_input("Senha nova", type="password")
    if st.button("Criar Usuário"):
        try:
            run_db("INSERT INTO usuarios (usuario, senha) VALUES (?,?)", (u_new, s_new))
            st.success("Usuário criado")
        except:
            st.error("Erro ou usuário já existe")

    st.divider()
    st.dataframe(run_db("SELECT usuario FROM usuarios", select=True), use_container_width=True)
