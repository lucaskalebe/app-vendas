import os
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# =============================
# CONFIGURAÇÕES GERAIS
# =============================
SENHA_MESTRE = os.getenv("SENHA_APP", "1234")  # fallback apenas para estudo
DB_NAME = "vendas.db"

st.set_page_config(page_title="Sistema de Vendas", layout="wide")


# =============================
# AUTENTICAÇÃO
# =============================
def check_password():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
        st.title("🔒 Acesso Restrito")
        senha = st.text_input("Digite a senha:", type="password")

        if st.button("Entrar"):
            if senha == SENHA_MESTRE:
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Senha incorreta.")
        return False
    return True


# =============================
# BANCO DE DADOS
# =============================
def get_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def init_db():
    with get_conn() as conn:
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_fantasia TEXT,
                contato TEXT,
                cidade TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS vendas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT,
                empresa TEXT,
                cliente TEXT,
                produto TEXT,
                valor_total REAL,
                comissao REAL
            )
        """)


# =============================
# CLIENTES
# =============================
def salvar_cliente(nome, contato, cidade):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO clientes (nome_fantasia, contato, cidade) VALUES (?, ?, ?)",
            (nome, contato, cidade)
        )


def carregar_clientes():
    return pd.read_sql("SELECT * FROM clientes", get_conn())


# =============================
# VENDAS
# =============================
def salvar_venda(empresa, cliente, produto, valor, perc):
    data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    comissao = valor * (perc / 100)

    with get_conn() as conn:
        conn.execute("""
            INSERT INTO vendas (data, empresa, cliente, produto, valor_total, comissao)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (data, empresa, cliente, produto, valor, comissao))


def carregar_vendas():
    return pd.read_sql("SELECT * FROM vendas", get_conn())


# =============================
# APP
# =============================
if not check_password():
    st.stop()

init_db()

st.title("📊 Sistema de Controle de Vendas")

abas = st.tabs(["📈 Dashboard", "➕ Nova Venda", "👥 Clientes", "📜 Histórico"])

df_vendas = carregar_vendas()
df_clientes = carregar_clientes()

lista_clientes = (
    df_clientes["nome_fantasia"]
    .dropna()
    .unique()
    .tolist()
    if not df_clientes.empty else []
)

# =============================
# DASHBOARD
# =============================
with abas[0]:
    st.subheader("Visão Geral")

    col1, col2 = st.columns(2)
    col1.metric("Total Vendido", f"R$ {df_vendas['valor_total'].sum():,.2f}")
    col2.metric("Total em Comissões", f"R$ {df_vendas['comissao'].sum():,.2f}")

    if not df_vendas.empty:
        st.bar_chart(df_vendas.groupby("empresa")["valor_total"].sum())


# =============================
# NOVA VENDA
# =============================
with abas[1]:
    st.subheader("Registrar Nova Venda")

    with st.form("nova_venda"):
        empresa = st.text_input("Empresa")
        produto = st.text_input("Produto")

        if lista_clientes:
            cliente = st.selectbox("Cliente / Loja", lista_clientes)
        else:
            st.warning("Cadastre um cliente antes de registrar vendas.")
            cliente = None

        col1, col2 = st.columns(2)
        valor = col1.number_input("Valor da Venda (R$)", min_value=0.0)
        perc = col2.number_input("Comissão (%)", value=10.0)

        if st.form_submit_button("Salvar Venda"):
            if empresa and cliente and valor > 0:
                salvar_venda(empresa, cliente, produto, valor, perc)
                st.success("Venda registrada com sucesso!")
                st.rerun()
            else:
                st.error("Preencha empresa, cliente e valor corretamente.")


# =============================
# CLIENTES
# =============================
with abas[2]:
    st.subheader("Cadastro de Clientes")

    with st.form("novo_cliente"):
        nome = st.text_input("Nome Fantasia")
        contato = st.text_input("Contato")
        cidade = st.text_input("Cidade")

        if st.form_submit_button("Salvar Cliente"):
            if nome:
                salvar_cliente(nome, contato, cidade)
                st.success("Cliente cadastrado!")
                st.rerun()
            else:
                st.warning("Nome Fantasia é obrigatório.")

    st.divider()
    st.dataframe(df_clientes, use_container_width=True)


# =============================
# HISTÓRICO
# =============================
with abas[3]:
    st.subheader("Histórico de Vendas")

    empresa_filtro = st.selectbox(
        "Filtrar por Empresa",
        ["Todas"] + sorted(df_vendas["empresa"].dropna().unique().tolist())
        if not df_vendas.empty else ["Todas"]
    )

    df_filtrado = df_vendas.copy()
    if empresa_filtro != "Todas":
        df_filtrado = df_filtrado[df_filtrado["empresa"] == empresa_filtro]

    st.dataframe(df_filtrado, use_container_width=True)

    st.divider()
    st.subheader("Excluir Última Venda")

    confirmar = st.checkbox("Confirmo que desejo apagar o último registro")

    if confirmar and st.button("Apagar Última Venda"):
        with get_conn() as conn:
            conn.execute("DELETE FROM vendas WHERE id = (SELECT MAX(id) FROM vendas)")
        st.success("Última venda removida.")
        st.rerun()
