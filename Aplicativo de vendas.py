

import os, streamlit as st, pandas as pd, sqlite3
from datetime import datetime

# ================== CONFIGURAÇÕES E BANCO ==================
st.set_page_config(page_title="Gestão Meira Nobre", layout="wide")
DB_NAME = "vendas.db"

def run_db(query, params=(), is_select=False):
    with sqlite3.connect(DB_NAME) as conn:
        if is_select:
            return pd.read_sql(query, conn)
        conn.execute(query, params)
        conn.commit()

def init_db():
    # Criação das tabelas base (sem o campo 'segmento' para evitar erros)
    run_db("""CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, empresa TEXT, 
        cliente TEXT, produto TEXT, qtd INTEGER, valor_unit REAL, 
        valor_total REAL, comissao REAL)""")
    
    run_db("""CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, cnpj TEXT, razao_social TEXT, 
        telefone TEXT, email TEXT, categoria TEXT)""")
    
    # Migração: Garante que colunas novas existam no banco atual
    cols = run_db("PRAGMA table_info(clientes)", is_select=True)['name'].tolist()
    for col in ['telefone', 'email', 'categoria']:
        if col not in cols:
            run_db(f"ALTER TABLE clientes ADD COLUMN {col} TEXT DEFAULT 'Não Informado'")

# --- AUTENTICAÇÃO ---
if "autenticado" not in st.session_state:
    st.title("🔒 Acesso Restrito")
    senha = st.text_input("Digite a senha", type="password")
    if st.button("Entrar"):
        if senha == os.getenv("SENHA_APP", "1234"):
            st.session_state["autenticado"] = True
            st.rerun()
        else: st.error("Senha incorreta")
    st.stop()

init_db()

# ================== INTERFACE ==================
st.title("📊 Sistema Meira Nobre")
tabs = st.tabs(["📈 Dashboards", "➕ Nova Venda", "📜 Histórico", "👤 Novo Cliente", "📁 Banco de Clientes"])

# --- 1. DASHBOARDS ---
with tabs[0]:
    dfv = run_db("SELECT * FROM vendas", is_select=True)
    dfc = run_db("SELECT * FROM clientes", is_select=True)
    
    if not dfv.empty:
        m = st.columns(4)
        m[0].metric("Faturamento", f"R$ {dfv['valor_total'].sum():,.2f}")
        m[1].metric("Comissões", f"R$ {dfv['comissao'].sum():,.2f}")
        m[2].metric("Pedidos", len(dfv))
        m[3].metric("Ticket Médio", f"R$ {dfv['valor_total'].mean():,.2f}")
        
        st.divider()
        g1, g2 = st.columns(2)
        g1.subheader("Vendas por Representada")
        g1.bar_chart(dfv.groupby("empresa")["valor_total"].sum())
        g2.subheader("Vendas por Cliente")
        g2.bar_chart(dfv.groupby("cliente")["valor_total"].sum())
    
    st.subheader("🟣 Inteligência de Clientes")
    if not dfc.empty:
        c1, c2 = st.columns(2)
        c1.write(dfc['categoria'].value_counts())
        c2.bar_chart(dfc.groupby("categoria").size())

# --- 2. NOVA VENDA ---
with tabs[1]:
    with st.container(border=True):
        st.subheader("📝 Registrar Pedido")
        c1, c2 = st.columns(2)
        emp, cli = c1.text_input("Empresa"), c2.text_input("Cliente")
        prod = st.text_input("Produto")
        
        q1, q2, q3 = st.columns(3)
        qtd = q1.number_input("Qtd", min_value=1, value=1)
        prc = q2.number_input("Preço Unit.", min_value=0.0)
        com = q3.number_input("Comissão %", value=10)
        
        tot, c_val = qtd * prc, (qtd * prc) * (com / 100)
        
        if st.button("🚀 Salvar Venda", use_container_width=True):
            if emp and cli and prc > 0:
                run_db("INSERT INTO vendas (data, empresa, cliente, produto, qtd, valor_unit, valor_total, comissao) VALUES (?,?,?,?,?,?,?,?)",
                       (datetime.now().strftime("%d/%m/%Y"), emp, cli, prod, qtd, prc, tot, c_val))
                st.success("Venda salva!"); st.rerun()

# --- 3 & 5. HISTÓRICO E BANCO DE CLIENTES (EDITÁVEIS) ---
for i, table, label in zip([2, 4], ["vendas", "clientes"], ["Vendas", "Clientes"]):
    with tabs[i]:
        df = run_db(f"SELECT * FROM {table}", is_select=True)
        # num_rows="dynamic" permite adicionar (+) e excluir (lixeira)
        edited = st.data_editor(df, use_container_width=True, num_rows="dynamic", hide_index=True, key=f"ed_{table}")
        
        if st.button(f"💾 Sincronizar {label}"):
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute(f"DELETE FROM {table}")
                edited.to_sql(table, conn, if_exists="append", index=False)
            st.success("Dados atualizados!"); st.rerun()

# --- 4. NOVO CLIENTE ---
with tabs[3]:
    with st.form("f_cli", clear_on_submit=True):
        st.subheader("👤 Cadastro")
        rs, cj = st.text_input("Razão Social"), st.text_input("CNPJ")
        cat = st.selectbox("Categoria", ["Varejo", "Atacado", "Supermercado", "Outros"])
        if st.form_submit_button("Salvar Cliente"):
            run_db("INSERT INTO clientes (razao_social, cnpj, categoria) VALUES (?,?,?)", (rs, cj, cat))
            st.success("Cadastrado!")
