import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime
from io import BytesIO

# ================= 1. CONFIGURAÇÃO (PRIMEIRA LINHA) =================

st.set_page_config(
    page_title="Gestão de Vendas | Meira Nobre",
    page_icon="📊",
    layout="wide"
)

DB = "vendas.db"

# ================= 2. BANCO DE DADOS =================
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

# ================= 3. LOGIN =================
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

# ================= 4. UI CABEÇALHO (ALINHADO) =================
st.markdown(
    """
    <style>
        .logo-texto {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            margin-bottom: 20px;
        }
    </style>

    <div class="logo-texto">
        <img src="data:image/png;base64,{logo_base64}" width="220">
        <h1 style="margin-top: 12px;">Gestão de Vendas | Meira Nobre</h1>
    </div>
    """,
    unsafe_allow_html=True
)

# ================= 5. DEFINIÇÃO DAS ABAS (CORREÇÃO) =================
tabs = st.tabs([
    "📈 Dashboard",
    "➕ Nova Venda",
    "👤 Clientes",
    "👥 Usuários"
])

# ================= DASHBOARD (Aba 0) =================
with tabs[0]:
    dfv = run_db("SELECT * FROM vendas", select=True)
    dfc = run_db("SELECT * FROM clientes", select=True)

    st.subheader("💰 Indicadores de Vendas")
    if not dfv.empty:
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

        # Exportar Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            dfv.to_excel(writer, index=False, sheet_name='Vendas')
        
        st.download_button(
            label="📥 Baixar Relatório em Excel",
            data=output.getvalue(),
            file_name=f"vendas_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.divider()
        g1, g2 = st.columns(2)
        with g1:
            st.write("### Faturamento por Empresa")
            st.bar_chart(dfv.groupby("empresa")["valor_total"].sum())
        with g2:
            st.write("### Faturamento por Segmento")
            st.bar_chart(dfv.groupby("segmento")["valor_total"].sum())
    else:
        st.info("Nenhuma venda registrada.")

    st.divider()
    st.subheader("👥 Resumo de Clientes")
    if not dfc.empty:
        res1, res2 = st.columns(2)
        res1.metric("Total de Clientes Cadastrados", len(dfc)) 
        with res2:
            st.write("### Clientes por Categoria")
            st.bar_chart(dfc["categoria"].value_counts())
    else:
        st.info("Nenhum cliente cadastrado.")

# ================= NOVA VENDA (Aba 1) =================
with tabs[1]:
    st.subheader("📝 Registrar Nova Venda")
    clientes_sel = run_db("SELECT razao_social FROM clientes", select=True)
    with st.form("venda_form"):
        c1, c2 = st.columns(2)
        emp = c1.text_input("Empresa")
        cli = c2.selectbox("Cliente", clientes_sel["razao_social"].tolist() if not clientes_sel.empty else ["Cadastre um cliente"])
        prod = st.text_input("Produto")
        seg = st.selectbox("Segmento", ["Tecnologia", "Hardware", "Software", "Periféricos", "Redes", "Automação", "Outros"])
        q1, q2, q3 = st.columns(3)
        qtd = q1.number_input("Qtd", min_value=1, value=1)
        prc = q2.number_input("Preço Unit", min_value=0.0)
        com = q3.number_input("Comissão %", value=10)
        if st.form_submit_button("🚀 Salvar Venda"):
            if emp and cli != "Cadastre um cliente" and prc > 0:
                total = qtd * prc
                v_com = total * (com / 100)
                run_db("INSERT INTO vendas (data, empresa, cliente, produto, qtd, valor_unit, valor_total, comissao, segmento) VALUES (?,?,?,?,?,?,?,?,?)", 
                       (datetime.now().strftime("%d/%m/%Y"), emp, cli, prod, qtd, prc, total, v_com, seg))
                st.success("Venda registrada!")
                st.rerun()

    st.divider()
    dfv_edit = run_db("SELECT * FROM vendas", select=True)
    if not dfv_edit.empty:
        new_dfv = st.data_editor(dfv_edit, hide_index=True, use_container_width=True, num_rows="dynamic", key="v_editor")
        if st.button("💾 Sincronizar Alterações de Pedidos"):
            with sqlite3.connect(DB) as conn:
                conn.execute("DELETE FROM vendas")
                new_dfv.to_sql("vendas", conn, index=False, if_exists="append")
            st.success("Sincronizado!")
            st.rerun()

# ================= CLIENTES (Aba 2) =================
with tabs[2]:
    st.subheader("👤 Cadastro de Cliente")
    with st.form("cli_form"):
        rs = st.text_input("Razão Social")
        cj = st.text_input("CNPJ")
        ct = st.selectbox("Categoria", ["Varejo", "Atacado", "Supermercado", "Outros"])
        if st.form_submit_button("Salvar Cliente"):
            if rs:
                run_db("INSERT INTO clientes (razao_social, cnpj, categoria) VALUES (?,?,?)", (rs, cj, ct))
                st.success("Cliente cadastrado!")
                st.rerun()
    st.divider()
    df_c_edit = run_db("SELECT * FROM clientes", select=True)
    if not df_c_edit.empty:
        new_dfc = st.data_editor(df_c_edit, hide_index=True, use_container_width=True, num_rows="dynamic", key="c_editor")
        if st.button("💾 Sincronizar Clientes"):
            with sqlite3.connect(DB) as conn:
                conn.execute("DELETE FROM clientes")
                new_dfc.to_sql("clientes", conn, index=False, if_exists="append")
            st.success("Sincronizado!")
            st.rerun()

# ================= USUÁRIOS (Aba 3) =================
with tabs[3]:
    st.subheader("➕ Incluir Novo Usuário")
    with st.form("new_user_form"):
        new_u = st.text_input("Nome do Usuário")
        new_s = st.text_input("Senha", type="password")
        if st.form_submit_button("Criar Usuário"):
            if new_u and new_s:
                try:
                    run_db("INSERT INTO usuarios (usuario, senha) VALUES (?,?)", (new_u, new_s))
                    st.success(f"Usuário {new_u} criado!")
                except:
                    st.error("Usuário já existe.")
    st.divider()
    st.dataframe(run_db("SELECT usuario FROM usuarios", select=True), use_container_width=True)





