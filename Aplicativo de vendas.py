

import os, streamlit as st, pandas as pd, sqlite3
from datetime import datetime

# ================== CONFIGURAÇÕES ==================
st.set_page_config(page_title="Gestão Meira Nobre", layout="wide")
DB_NAME = "vendas.db"

# ================== BANCO ==================
def run_db(query, params=(), is_select=False):
    with sqlite3.connect(DB_NAME) as conn:
        if is_select:
            return pd.read_sql(query, conn)
        conn.execute(query, params)
        conn.commit()

def init_db():
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

    # Migrações seguras
    cols_v = run_db("PRAGMA table_info(vendas)", is_select=True)["name"].tolist()
    if "segmento" not in cols_v:
        run_db("ALTER TABLE vendas ADD COLUMN segmento TEXT DEFAULT 'Não Informado'")

    cols_c = run_db("PRAGMA table_info(clientes)", is_select=True)["name"].tolist()
    for col in ["telefone", "email", "categoria"]:
        if col not in cols_c:
            run_db(f"ALTER TABLE clientes ADD COLUMN {col} TEXT DEFAULT 'Não Informado'")

# ================== LOGIN ==================
if "autenticado" not in st.session_state:
    st.title("🔒 Acesso Restrito")
    senha = st.text_input("Digite a senha", type="password")
    if st.button("Entrar"):
        if senha == os.getenv("SENHA_APP", "1234"):
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Senha incorreta")
    st.stop()

init_db()

# ================== INTERFACE ==================
st.title("📊 Sistema Meira Nobre")
tabs = st.tabs(["📈 Dashboards", "➕ Nova Venda", "📜 Histórico", "👤 Novo Cliente", "📁 Banco de Clientes"])

# ================== DASHBOARD ==================
with tabs[0]:
    dfv = run_db("SELECT * FROM vendas", is_select=True)
    dfc = run_db("SELECT * FROM clientes", is_select=True)

    if not dfv.empty:
        # Blindagem de tipos
        for col in ["qtd", "valor_unit", "valor_total", "comissao"]:
            dfv[col] = pd.to_numeric(dfv[col], errors="coerce").fillna(0)

        m = st.columns(4)
        m[0].metric("Faturamento", f"R$ {dfv['valor_total'].sum():,.2f}")
        m[1].metric("Comissões", f"R$ {dfv['comissao'].sum():,.2f}")
        m[2].metric("Pedidos", len(dfv))
        m[3].metric("Ticket Médio", f"R$ {dfv['valor_total'].mean():,.2f}")

        st.divider()
        g1, g2 = st.columns(2)
        g1.subheader("Vendas por Empresa")
        g1.bar_chart(dfv.groupby("empresa")["valor_total"].sum())

        g2.subheader("Vendas por Cliente")
        g2.bar_chart(dfv.groupby("cliente")["valor_total"].sum())

    st.subheader("🟣 Inteligência de Clientes")
    if not dfc.empty:
        c1, c2 = st.columns(2)
        c1.write(dfc["categoria"].value_counts())
        c2.bar_chart(dfc.groupby("categoria").size())

# ================== NOVA VENDA ==================
with tabs[1]:
    with st.container(border=True):
        st.subheader("📝 Registrar Pedido")

        c1, c2 = st.columns(2)
        emp = c1.text_input("Empresa")
        cli = c2.text_input("Cliente")

        prod = st.text_input("Produto")
        seg = st.selectbox("Segmento", [
            "Varejo", "Atacado", "Supermercado",
            "Food Service", "Hotelaria", "Outros"
        ])

        q1, q2, q3 = st.columns(3)
        qtd = q1.number_input("Qtd", min_value=1, value=1)
        prc = q2.number_input("Preço Unit.", min_value=0.0)
        com = q3.number_input("Comissão %", value=10)

        total = qtd * prc
        com_val = total * (com / 100)

        if st.button("🚀 Salvar Venda", use_container_width=True):
            if emp and cli and prod and prc > 0:
                run_db("""
                INSERT INTO vendas
                (data, empresa, cliente, produto, qtd, valor_unit, valor_total, comissao, segmento)
                VALUES (?,?,?,?,?,?,?,?,?)
                """, (
                    datetime.now().strftime("%d/%m/%Y"),
                    emp, cli, prod, qtd, prc, total, com_val, seg
                ))
                st.success("Venda salva com sucesso!")
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

            st.success("Dados sincronizados!")
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

