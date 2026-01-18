

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
    
    # Adicionada a coluna 'segmento' para bater com sua imagem
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
    # Busca os dados atualizados do banco toda vez que entra na aba
    dfv = run_db("SELECT * FROM vendas", select=True)

    if not dfv.empty:
        # Conversão de tipos para garantir cálculos precisos
        dfv["valor_total"] = pd.to_numeric(dfv["valor_total"])
        dfv["comissao"] = pd.to_numeric(dfv["comissao"])

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Faturamento Total", f"R$ {dfv.valor_total.sum():,.2f}")
        c2.metric("Comissões Totais", f"R$ {dfv.comissao.sum():,.2f}")
        c3.metric("Total Pedidos", len(dfv))
        c4.metric("Ticket Médio", f"R$ {dfv.valor_total.mean():,.2f}")

        st.divider()
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.subheader("Vendas por Empresa")
            st.bar_chart(dfv.groupby("empresa")["valor_total"].sum())
        
        with col_g2:
            st.subheader("Vendas por Segmento")
            st.pie_chart(dfv.groupby("segmento")["valor_total"].sum())

        st.dataframe(dfv, use_container_width=True, hide_index=True)
    else:
        st.info("O Dashboard será populado assim que a primeira venda for registrada.")

# ================= NOVA VENDA =================
with tabs[1]:
    st.subheader("📝 Registrar Nova Venda")
    
    df_clientes = run_db("SELECT razao_social, categoria FROM clientes", select=True)
    
    with st.form("form_venda", clear_on_submit=True):
        c1, c2 = st.columns(2)
        emp = c1.text_input("Empresa (Sua Empresa)")
        cli = c2.selectbox("Cliente", df_clientes["razao_social"] if not df_clientes.empty else ["Cadastre um cliente primeiro"])
        
        prod = st.text_input("Produto")
        
        # Segmento baseado na categoria do cliente ou input manual
        seg = st.selectbox("Segmento", ["Tecnologia", "Hardware", "Software", "Periféricos", "Serviços"])
        
        q1, q2, q3 = st.columns(3)
        qtd = q1.number_input("Quantidade", min_value=1, value=1)
        prc = q2.number_input("Preço Unitário (R$)", min_value=0.0, format="%.2f")
        com_per = q3.number_input("Comissão (%)", min_value=0.0, value=10.0)
        
        if st.form_submit_button("🚀 Salvar Venda"):
            if emp and prod and prc > 0:
                total = qtd * prc
                v_comissao = total * (com_per / 100)
                
                run_db("""
                    INSERT INTO vendas (data, empresa, cliente, produto, qtd, valor_unit, valor_total, comissao, segmento)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (datetime.now().strftime("%d/%m/%Y"), emp, cli, prod, qtd, prc, total, v_comissao, seg))
                
                st.success("Venda registrada com sucesso!")
                st.rerun()
            else:
                st.error("Preencha todos os campos corretamente.")

# ================= CLIENTES (Sincronização em Tempo Real) =================
with tabs[2]:
    st.subheader("👤 Cadastro de Cliente")
    with st.form("form_cliente", clear_on_submit=True):
        rs = st.text_input("Razão Social")
        cj = st.text_input("CNPJ")
        cat = st.selectbox("Categoria", ["Varejo", "Atacado", "Supermercado", "Outros"])
        if st.form_submit_button("Salvar Cliente"):
            run_db("INSERT INTO clientes (razao_social, cnpj, categoria) VALUES (?,?,?)", (rs, cj, cat))
            st.rerun()

    st.divider()
    dfc = run_db("SELECT * FROM clientes", select=True)
    if not dfc.empty:
        st.write("### Banco de Clientes")
        st.dataframe(dfc, use_container_width=True, hide_index=True)
