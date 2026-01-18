import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime
from io import BytesIO

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
    run_db("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, senha TEXT)")
    run_db("CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, razao_social TEXT, cnpj TEXT, categoria TEXT)")
    run_db("""
    CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, empresa TEXT, cliente TEXT, 
        produto TEXT, qtd INTEGER, valor_unit REAL, valor_total REAL, comissao REAL, segmento TEXT
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
    dfc = run_db("SELECT * FROM clientes", select=True)

    # --- Seção de Vendas ---
    st.subheader("💰 Indicadores de Vendas")
    if not dfv.empty:
        # CORREÇÃO DO ERRO: Limpeza de strings R$ e conversão numérica
        for col in ["valor_total", "comissao", "valor_unit"]:
            if dfv[col].dtype == object:
                dfv[col] = dfv[col].astype(str).str.replace('R$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).str.strip()
            dfv[col] = pd.to_numeric(dfv[col], errors='coerce').fillna(0)
        
        dfv["qtd"] = pd.to_numeric(dfv["qtd"], errors='coerce').fillna(0)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Faturamento", f"R$ {dfv.valor_total.sum():,.2f}")
        c2.metric("Comissões", f"R$ {dfv.comissao.sum():,.2f}")
        c3.metric("Pedidos", len(dfv))
        c4.metric("Ticket Médio", f"R$ {dfv.valor_total.mean():,.2f}")

        st.divider()
        g1, g2 = st.columns(2)
        with g1:
            st.write("### Faturamento por Empresa")
            st.bar_chart(dfv.groupby("empresa")["valor_total"].sum())
        with g2:
            st.write("### Faturamento por Segmento")
            st.bar_chart(dfv.groupby("segmento")["valor_total"].sum())
    else:
        st.info("Aguardando registro de vendas.")

    st.divider()

    # --- Seção de Clientes (DASHBOARD DE CLIENTES) ---
    st.subheader("👥 Dashboard de Clientes")
    if not dfc.empty:
        k1, k2 = st.columns([1, 2])
        with k1:
            st.metric("Total de Clientes", len(dfc))
            st.write("### Por Categoria")
            st.bar_chart(dfc["categoria"].value_counts())
        with k2:
            st.write("### Clientes Cadastrados")
            st.dataframe(dfc[["razao_social", "cnpj", "categoria"]], hide_index=True, use_container_width=True)
    else:
        st.info("Nenhum cliente cadastrado ainda.")

# ================= NOVA VENDA =================
with tabs[1]:
    st.subheader("📝 Registrar Nova Venda")
    clientes_sel = run_db("SELECT razao_social FROM clientes", select=True)
    
    with st.form("venda_form"):
        c1, c2 = st.columns(2)
        emp = c1.text_input("Empresa")
        cli = c2.selectbox("Cliente", clientes_sel["razao_social"] if not clientes_sel.empty else ["Cadastre um cliente"])
        prod = st.text_input("Produto")
        seg = st.selectbox("Segmento", ["Tecnologia", "Hardware", "Software", "Periféricos", "Redes", "Automação"])
        
        q1, q2, q3 = st.columns(3)
        qtd = q1.number_input("Qtd", min_value=1)
        prc = q2.number_input("Preço Unit", min_value=0.0)
        com = q3.number_input("Comissão %", value=10)
        
        if st.form_submit_button("🚀 Salvar Venda"):
            total = qtd * prc
            v_com = total * (com / 100)
            run_db("""INSERT INTO vendas (data, empresa, cliente, produto, qtd, valor_unit, valor_total, comissao, segmento) 
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                   (datetime.now().strftime("%d/%m/%Y"), emp, cli, prod, qtd, prc, total, v_com, seg))
            st.success("Venda registrada!")
            st.rerun()

    st.divider()
    dfv_list = run_db("SELECT * FROM vendas", select=True)
    if not dfv_list.empty:
        st.write("### Pedidos Registrados")
        st.data_editor(dfv_list, hide_index=True, use_container_width=True)

# ================= CLIENTES =================
with tabs[2]:
    st.subheader("👤 Cadastro de Cliente")
    with st.form("cli_form"):
        rs = st.text_input("Razão Social")
        cj = st.text_input("CNPJ")
        ct = st.selectbox("Categoria", ["Varejo", "Atacado", "Supermercado", "Outros"])
        if st.form_submit_button("Salvar Cliente"):
            run_db("INSERT INTO clientes (razao_social, cnpj, categoria) VALUES (?,?,?)", (rs, cj, ct))
            st.rerun()

# ================= USUÁRIOS =================
with tabs[3]:
    st.subheader("👥 Usuários")
    st.dataframe(run_db("SELECT usuario FROM usuarios", select=True), use_container_width=True)
