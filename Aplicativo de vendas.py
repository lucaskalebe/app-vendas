import os
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import io

# ================== CONFIGURAÇÕES E ESTILO ==================
st.set_page_config(page_title="Gestão Meira Nobre", layout="wide")

SENHA_MESTRE = os.getenv("SENHA_APP", "1234")
DB_NAME = "vendas.db"

def check_password():
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
        return False
    return True

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
                cnpj TEXT, razao_social TEXT, nome_fantasia TEXT,
                telefone TEXT, email TEXT, responsavel TEXT
            )
        """)

# ================== INTERFACE PRINCIPAL ==================
if check_password():
    init_db()
    st.title("📊 Sistema de Gestão Meira Nobre")

    t_dash, t_venda, t_hist_vendas, t_cad_cliente, t_db_cliente = st.tabs([
        "📈 Dashboard Pro", "➕ Nova Venda", "📜 Histórico e Edição", "👤 Cadastro Cliente", "📁 Banco de Dados Clientes"
    ])

    # --- 1. DASHBOARD ---
    with t_dash:
        with sqlite3.connect(DB_NAME) as conn:
            df_v = pd.read_sql("SELECT * FROM vendas", conn)
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
                st.bar_chart(df_v.groupby("empresa")["valor_total"].sum())
            with g2:
                st.subheader("Performance de Comissões")
                st.bar_chart(df_v.groupby("empresa")["comissao"].sum())
        else:
            st.info("Lance vendas para ativar o Dashboard.")

    # --- 2. NOVA VENDA (VISUAL PREMIUM) ---
    with t_venda:
        with st.container(border=True):
            st.subheader("📝 Registrar Novo Pedido")
            with st.form("f_venda", clear_on_submit=True):
                emp = st.text_input("🏢 Empresa Representada")
                cli = st.text_input("🏬 Cliente / Loja")
                prod = st.text_input("📦 Descrição do Produto")
                col1, col2, col3 = st.columns(3)
                q = col1.number_input("🔢 Quantidade", min_value=1, value=1)
                v = col2.number_input("💰 Preço Unitário (R$)", min_value=0.0, format="%.2f")
                p = col3.number_input("📈 Comissão %", min_value=0, value=10)
                
                if st.form_submit_button("🚀 Salvar Venda"):
                    if emp and cli and v > 0:
                        total = q * v
                        comis = total * (p / 100)
                        dt = datetime.now().strftime("%d/%m/%Y %H:%M")
                        with sqlite3.connect(DB_NAME) as conn:
                            conn.execute("INSERT INTO vendas (data, empresa, cliente, produto, qtd, valor_unit, valor_total, comissao) VALUES (?,?,?,?,?,?,?,?)",
                                         (dt, emp, cli, prod, q, v, total, comis))
                        st.success(f"✅ Venda de R$ {total:,.2f} registrada!")
                        st.rerun()

    # --- 3. HISTÓRICO COM EDIÇÃO E EXCLUSÃO (UX MÁXIMO) ---
    with t_hist_vendas:
        st.subheader("📜 Gestão de Pedidos")
        st.info("💡 Clique em qualquer célula para editar ou use a lixeira à esquerda para excluir.")
        
        with sqlite3.connect(DB_NAME) as conn:
            df_hist = pd.read_sql("SELECT * FROM vendas ORDER BY id DESC", conn)
        
        # O Editor de Dados permite excluir e editar livremente
        edited_df = st.data_editor(
            df_hist, 
            use_container_width=True, 
            num_rows="dynamic", # Permite deletar linhas
            hide_index=True,
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "valor_total": st.column_config.NumberColumn("Total R$", format="R$ %.2f"),
                "comissao": st.column_config.NumberColumn("Comissão R$", format="R$ %.2f")
            }
        )

        if st.button("💾 Confirmar Alterações / Exclusões"):
            with sqlite3.connect(DB_NAME) as conn:
                # Limpa a tabela e salva a nova versão editada
                conn.execute("DELETE FROM vendas")
                edited_df.to_sql("vendas", conn, if_exists="append", index=False)
            st.success("✨ Banco de dados atualizado com sucesso!")
            st.rerun()

    # --- 4. CADASTRO CLIENTE ---
    with t_cad_cliente:
        with st.container(border=True):
            st.subheader("👤 Cadastro de Novo Cliente")
            with st.form("f_cli", clear_on_submit=True):
                c1, c2 = st.columns(2)
                cnpj = c1.text_input("CNPJ")
                razao = c2.text_input("Razão Social")
                tel = st.text_input("Telefone")
                email = st.text_input("E-mail")
                if st.form_submit_button("💾 Salvar Cliente"):
                    if razao:
                        with sqlite3.connect(DB_NAME) as conn:
                            conn.execute("INSERT INTO clientes (cnpj, razao_social, telefone, email) VALUES (?,?,?,?)",
                                         (cnpj, razao, tel, email))
                        st.success("✅ Cliente cadastrado!")
                        st.rerun()

    # --- 5. BANCO DE DADOS CLIENTES (COM EDIÇÃO) ---
    with t_db_cliente:
        st.subheader("📁 Gerenciar Clientes")
        with sqlite3.connect(DB_NAME) as conn:
            df_c = pd.read_sql("SELECT * FROM clientes ORDER BY razao_social", conn)
        
        # Também permitindo editar clientes direto na tabela
        edited_clients = st.data_editor(df_c, use_container_width=True, num_rows="dynamic", hide_index=True)
        
        if st.button("💾 Salvar Mudanças nos Clientes"):
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute("DELETE FROM clientes")
                edited_clients.to_sql("clientes", conn, if_exists="append", index=False)
            st.success("✅ Lista de clientes atualizada!")
            st.rerun()
