import os
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import io

# ================== CONFIG ==================
SENHA_MESTRE = os.getenv("SENHA_APP", "1234")
DB_NAME = "vendas.db"

# ================== AUTH ==================
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

# ================== DATABASE ==================
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vendas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT,
                empresa TEXT,
                cliente TEXT,
                produto TEXT,
                qtd INTEGER,
                valor_unit REAL,
                valor_total REAL,
                comissao REAL
            )
        """)
        # Mantém o banco atualizado com novas colunas se necessário
        cursor = conn.cursor()
        colunas = [info[1] for info in cursor.execute("PRAGMA table_info(vendas)")]
        if "qtd" not in colunas:
            conn.execute("ALTER TABLE vendas ADD COLUMN qtd INTEGER DEFAULT 1")
        if "valor_unit" not in colunas:
            conn.execute("ALTER TABLE vendas ADD COLUMN valor_unit REAL DEFAULT 0")
        conn.commit()

def salvar_venda(empresa, cliente, produto, qtd, valor_unit, valor_total, perc_int):
    data = datetime.now().strftime("%d/%m/%Y %H:%M")
    # Cálculo usando o inteiro da comissão
    valor_comissao = valor_total * (perc_int / 100)

    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            INSERT INTO vendas (data, empresa, cliente, produto, qtd, valor_unit, valor_total, comissao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (data, empresa, cliente, produto, qtd, valor_unit, valor_total, valor_comissao))

def carregar_dados():
    with sqlite3.connect(DB_NAME) as conn:
        return pd.read_sql("SELECT * FROM vendas ORDER BY id DESC", conn)

# ================== APP ==================
if check_password():
    init_db()
    st.title("📊 Gestão de Vendas e Comissões")
    
    df = carregar_dados()

    tab_dash, tab_venda, tab_hist = st.tabs(["📈 Dashboard", "➕ Nova Venda", "📜 Histórico"])

    # ================== DASHBOARD ==================
    with tab_dash:
        if df.empty:
            st.info("Aguardando registros para gerar gráficos.")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Faturamento Total", f"R$ {df['valor_total'].sum():,.2f}")
            c2.metric("Total Comissões", f"R$ {df['comissao'].sum():,.2f}")
            c3.metric("Itens Vendidos", int(df['qtd'].sum()))

            st.subheader("Performance por Empresa")
            st.bar_chart(df.groupby("empresa")["valor_total"].sum())

    # ================== NOVA VENDA ==================
  
    with tab_venda:
        with st.form("form_venda", clear_on_submit=True):
            st.subheader("Registrar Pedido")
            empresa = st.text_input("Empresa Representada")
            cliente = st.text_input("Cliente / Loja")
            produto = st.text_input("Descrição do Produto")

            col1, col2, col3 = st.columns(3)
            qtd = col1.number_input("Qtd", min_value=1, value=1, step=1)
            v_unit = col2.number_input("Preço Unitário (R$)", min_value=0.0, format="%.2f")
            
            # COMISSÃO COMO INTEIRO (conforme você pediu)
            perc_int = col3.number_input("Comissão %", min_value=0, max_value=100, value=10, step=1)

            # CÁLCULOS
            total_venda = qtd * v_unit
            com_est = total_venda * (perc_int / 100)

            # EXIBIÇÃO DO RESUMO (CORRIGIDA)
            with st.status("✅ Resumo do Lançamento", expanded=True):
                st.write(f"Valor do Pedido: R$ {total_venda:,.2f}")
                st.write(f"Sua Comissão: R$ {com_est:,.2f}")    
            

            if st.form_submit_button("Salvar Registro"):
                if empresa and total_venda > 0:
                    salvar_venda(empresa, cliente, produto, qtd, v_unit, total_venda, perc_int)
                    st.success("Venda registrada com sucesso!")
                    st.rerun()
                else:
                    st.error("Preencha a Empresa e o Valor Unitário!")

    # ================== HISTÓRICO ==================
    with tab_hist:
        if not df.empty:
            # Filtro para facilitar a busca
            lista_empresas = ["Todas"] + sorted(df["empresa"].unique().tolist())
            escolha = st.selectbox("Ver apenas de:", lista_empresas)
            
            df_final = df if escolha == "Todas" else df[df["empresa"] == escolha]
            
            # Exibe a tabela formatada (width='stretch' para 2026)
            st.dataframe(df_final, width='stretch')

            # --- BOTÃO EXCEL ---
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_final.to_excel(writer, index=False, sheet_name='Relatorio')
            
            st.download_button(
                label="📥 Baixar em Excel",
                data=buffer.getvalue(),
                file_name=f"vendas_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
                mime="application/vnd.ms-excel"
            )

            st.divider()
            if st.checkbox("Liberar botão de exclusão"):
                if st.button("Remover último lançamento"):
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.execute("DELETE FROM vendas WHERE id = (SELECT MAX(id) FROM vendas)")
                    st.rerun()
        else:
            st.info("Nenhum histórico encontrado.")