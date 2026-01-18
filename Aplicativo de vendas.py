

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
                cnpj TEXT, razao_social TEXT, telefone TEXT, email TEXT
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

    # --- 2. NOVA VENDA (VISUAL CARDS ELEGANTES) ---
    with t_venda:
        with st.container(border=True):
            st.subheader("📝 Registrar Novo Pedido")
            
            col_id1, col_id2 = st.columns(2)
            emp = col_id1.text_input("🏢 Empresa Representada")
            cli = col_id2.text_input("🏬 Cliente / Loja")
            prod = st.text_input("📦 Descrição do Produto")
            
            c1, c2, c3 = st.columns(3)
            q = c1.number_input("🔢 Quantidade", min_value=1, value=1)
            v = c2.number_input("💰 Preço Unitário (R$)", min_value=0.0, format="%.2f")
            p = c3.number_input("📈 Comissão %", min_value=0, value=10)
            
            # CÁLCULO E CARDS ELEGANTES
            total_calc = q * v
            comis_calc = total_calc * (p / 100)
            
            st.write("---")
            # Criando os "balões" de resumo
            b1, b2, b3 = st.columns([1,1,2])
            b1.metric("Valor Total", f"R$ {total_calc:,.2f}")
            b2.metric("Sua Comissão", f"R$ {comis_calc:,.2f}")
            
            st.write("") # Espaçamento
            if st.button("🚀 Salvar Venda definitiva", use_container_width=True):
                if emp and cli and v > 0:
                    dt = datetime.now().strftime("%d/%m/%Y %H:%M")
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.execute("INSERT INTO vendas (data, empresa, cliente, produto, qtd, valor_unit, valor_total, comissao) VALUES (?,?,?,?,?,?,?,?)",
                                     (dt, emp, cli, prod, q, v, total_calc, comis_calc))
                    st.success("✅ Venda salva com sucesso!")
                    st.rerun()
                else:
                    st.error("⚠️ Preencha Empresa, Cliente e Valor Unitário.")

    # --- 3. HISTÓRICO COM RE-CÁLCULO AUTOMÁTICO ---
    with t_hist_vendas:
        st.subheader("📜 Gestão de Pedidos")
        with sqlite3.connect(DB_NAME) as conn:
            df_hist = pd.read_sql("SELECT * FROM vendas ORDER BY id DESC", conn)
        
        if not df_hist.empty:
            st.info("💡 Se você alterar a Quantidade ou Valor Unitário, o Total e a Comissão serão recalculados ao salvar.")
            
            # Editor tipo Excel
            edited_df = st.data_editor(
                df_hist, 
                use_container_width=True, 
                num_rows="dynamic", 
                hide_index=True,
                column_config={
                    "valor_total": st.column_config.NumberColumn("Total R$", disabled=True), # Travado para não editarem errado
                    "comissao": st.column_config.NumberColumn("Comissão R$", disabled=True)  # Travado para não editarem errado
                }
            )
            
            if st.button("💾 Salvar Alterações e Recalcular"):
                # Lógica de re-cálculo para garantir integridade
                edited_df["valor_total"] = edited_df["qtd"] * edited_df["valor_unit"]
                # Para a comissão, precisamos de uma porcentagem. Como não salvamos a % fixa no banco, 
                # mantemos a proporção original ou assumimos a última usada. 
                # Aqui, vamos recalcular a comissão baseada na proporção anterior da linha editada:
                edited_df["comissao"] = edited_df["valor_total"] * (df_hist["comissao"] / df_hist["valor_total"]).fillna(0.1)

                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute("DELETE FROM vendas")
                    edited_df.to_sql("vendas", conn, if_exists="append", index=False)
                st.success("✨ Dados salvos e valores recalculados!")
                st.rerun()
        else:
            st.info("Nenhuma venda encontrada.")

    # --- 4. CADASTRO CLIENTE ---
    with t_cad_cliente:
        with st.container(border=True):
            st.subheader("👤 Cadastro de Novo Cliente")
            with st.form("f_cli"):
                cn = st.text_input("CNPJ")
                rs = st.text_input("Razão Social")
                tl = st.text_input("Telefone")
                em = st.text_input("E-mail")
                if st.form_submit_button("💾 Salvar Cliente"):
                    if rs:
                        with sqlite3.connect(DB_NAME) as conn:
                            conn.execute("INSERT INTO clientes (cnpj, razao_social, telefone, email) VALUES (?,?,?,?)",
                                         (cn, rs, tl, em))
                        st.success("✅ Cliente cadastrado!")
                        st.rerun()

    # --- 5. BANCO DE DADOS CLIENTES ---
    with t_db_cliente:
        st.subheader("📁 Gerenciar Clientes")
        with sqlite3.connect(DB_NAME) as conn:
            df_c = pd.read_sql("SELECT * FROM clientes ORDER BY razao_social", conn)
        
        edited_clients = st.data_editor(df_c, use_container_width=True, num_rows="dynamic", hide_index=True)
        
        if st.button("💾 Salvar Mudanças de Clientes"):
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute("DELETE FROM clientes")
                edited_clients.to_sql("clientes", conn, if_exists="append", index=False)
            st.success("✅ Lista de clientes atualizada!")
            st.rerun()
