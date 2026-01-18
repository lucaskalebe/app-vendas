

import os
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# ================== CONFIGURAÇÕES E ESTILO ==================
st.set_page_config(page_title="Gestão Meira Nobre", layout="wide")

SENHA_MESTRE = os.getenv("SENHA_APP", "1234")
DB_NAME = "vendas.db"

# Função para garantir que o Dashboard pegue dados frescos
def get_data(query):
    with sqlite3.connect(DB_NAME) as conn:
        return pd.read_sql(query, conn)

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vendas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT, empresa TEXT, cliente TEXT, produto TEXT,
                qtd INTEGER, valor_unit REAL, valor_total REAL, comissao REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cnpj TEXT, razao_social TEXT, telefone TEXT, email TEXT
            )
        """)

init_db()

# --- AUTENTICAÇÃO ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.title("🔒 Acesso Restrito")
    senha = st.text_input("Digite a senha", type="password")
    if st.button("Entrar"):
        if senha == SENHA_MESTRE:
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Senha incorreta")
    st.stop()

# ================== INTERFACE PRINCIPAL ==================
st.title("📊 Sistema de Gestão Meira Nobre")

t_dash, t_venda, t_hist_vendas, t_cad_cliente, t_db_cliente = st.tabs([
    "📈 Dashboard Pro", "➕ Nova Venda", "📜 Histórico e Edição", "👤 Cadastro Cliente", "📁 Banco de Dados Clientes"
])

# --- 1. DASHBOARD (Sincronizado com o Banco) ---
with t_dash:
    df_v = get_data("SELECT * FROM vendas")
    
    # Remove qualquer linha suja que possa ter ficado no banco
    df_v = df_v.dropna(subset=['empresa', 'valor_total'])
    df_v = df_v[df_v['empresa'] != ""]

    if not df_v.empty:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Faturamento Total", f"R$ {df_v['valor_total'].sum():,.2f}")
        m2.metric("Total Comissões", f"R$ {df_v['comissao'].sum():,.2f}")
        m3.metric("Ticket Médio", f"R$ {df_v['valor_total'].mean():,.2f}")
        m4.metric("Qtd Pedidos", len(df_v))
        
        st.divider()
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("Vendas por Representada")
            vendas_resumo = df_v.groupby("empresa")["valor_total"].sum()
            st.bar_chart(vendas_resumo)
        with g2:
            st.subheader("Comissões por Representada")
            comis_resumo = df_v.groupby("empresa")["comissao"].sum()
            st.bar_chart(comis_resumo)
    else:
        st.info("O banco de dados está vazio ou limpo. Lance novas vendas!")

# --- 2. NOVA VENDA (Com Reset de Campos) ---
with t_venda:
    with st.container(border=True):
        st.subheader("📝 Registrar Novo Pedido")
        
        # Keys para permitir o reset
        c_top1, c_top2 = st.columns(2)
        emp = c_top1.text_input("🏢 Empresa Representada", key="txt_emp")
        cli = c_top2.text_input("🏬 Cliente / Loja", key="txt_cli")
        prod = st.text_input("📦 Descrição do Produto", key="txt_prod")
        
        c1, c2, c3 = st.columns(3)
        q = c1.number_input("🔢 Quantidade", min_value=1, value=1, key="num_q")
        v = c2.number_input("💰 Preço Unitário (R$)", min_value=0.0, format="%.2f", key="num_v")
        p = c3.number_input("📈 Comissão %", min_value=0, value=10, key="num_p")
        
        total_calc = q * v
        comis_calc = total_calc * (p / 100)
        
        st.divider()
        res1, res2 = st.columns(2)
        res1.metric("Valor Total", f"R$ {total_calc:,.2f}")
        res2.metric("Sua Comissão", f"R$ {comis_calc:,.2f}")

        if st.button("🚀 Salvar Venda", use_container_width=True):
            if emp and cli and v > 0:
                dt = datetime.now().strftime("%d/%m/%Y %H:%M")
                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute("INSERT INTO vendas (data, empresa, cliente, produto, qtd, valor_unit, valor_total, comissao) VALUES (?,?,?,?,?,?,?,?)",
                                 (dt, emp, cli, prod, q, v, total_calc, comis_calc))
                st.success("✅ Venda salva!")
                st.rerun() # O rerun limpa os campos automaticamente devido ao fluxo do Streamlit
            else:
                st.error("⚠️ Preencha os campos obrigatórios.")

# --- 3. HISTÓRICO E EDIÇÃO (Com Limpeza Real de Deletados) ---
with t_hist_vendas:
    st.subheader("📜 Gestão e Limpeza")
    df_hist = get_data("SELECT * FROM vendas ORDER BY id DESC")
    
    if not df_hist.empty:
        st.warning("💡 Edite e clique em salvar. Linhas deletadas sumirão do Dashboard imediatamente.")
        edited_df = st.data_editor(
            df_hist, 
            use_container_width=True, 
            num_rows="dynamic", 
            hide_index=True,
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "valor_total": st.column_config.NumberColumn("Total R$", disabled=True, format="R$ %.2f"),
                "comissao": st.column_config.NumberColumn("Comissão R$", disabled=True, format="R$ %.2f")
            }
        )
        
        if st.button("💾 Salvar Alterações e Sincronizar Dash"):
            # Remove linhas vazias
            edited_df = edited_df.dropna(subset=['empresa', 'valor_unit'])
            edited_df = edited_df[edited_df['empresa'] != ""]
            
            # Recalcula
            edited_df["valor_total"] = edited_df["qtd"] * edited_df["valor_unit"]
            # Proporção de comissão (mantém a lógica anterior)
            edited_df["comissao"] = edited_df["valor_total"] * 0.1 

            with sqlite3.connect(DB_NAME) as conn:
                conn.execute("DELETE FROM vendas")
                edited_df.to_sql("vendas", conn, if_exists="append", index=False)
                conn.execute("VACUUM") # COMANDO PARA APAGAR DADOS DELETADOS DO DISCO
            st.success("✨ Banco de dados sincronizado!")
            st.rerun()
    else:
        st.info("Histórico vazio.")

# --- 4. CADASTRO CLIENTE ---
with t_cad_cliente:
    with st.container(border=True):
        st.subheader("👤 Cadastro de Novo Cliente")
        with st.form("f_cli", clear_on_submit=True):
            rs = st.text_input("Razão Social")
            cn = st.text_input("CNPJ")
            tl = st.text_input("Telefone")
            em = st.text_input("E-mail")
            if st.form_submit_button("💾 Salvar Cliente"):
                if rs:
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.execute("INSERT INTO clientes (cnpj, razao_social, telefone, email) VALUES (?,?,?,?)", (cn, rs, tl, em))
                    st.success("✅ Cliente salvo!")
                else: st.error("Razão Social obrigatória.")

# --- 5. BANCO DE CLIENTES ---
with t_db_cliente:
    df_c = get_data("SELECT * FROM clientes ORDER BY razao_social")
    st.data_editor(df_c, use_container_width=True, num_rows="dynamic", hide_index=True)
