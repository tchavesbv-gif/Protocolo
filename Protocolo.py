from datetime import datetime
import base64
import io
import os
import sqlite3
from fpdf import FPDF
import streamlit as st

# ==========================================
# 0. CONFIGURAÇÃO GLOBAL E ESTILOS CSS
# ==========================================
st.set_page_config(
    page_title="Controle de Exames - Sec. Saúde Teixeiras",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
    <style>
        .main { background-color: #f8fafc; }
        .header-container {
            background: linear-gradient(135deg, #1e3a8a 0%, #0284c7 100%);
            padding: 25px 30px;
            border-radius: 12px;
            color: white;
            margin-bottom: 25px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        .header-title { font-size: 26px; font-weight: 700; margin: 0; color: #ffffff; }
        .header-subtitle { font-size: 14px; color: #e0f2fe; margin-top: 5px; font-weight: 400; }

        div[data-testid="stTextInput"] div[data-baseweb="input"] {
            background-color: #ffffff !important;
            border-radius: 8px !important;
        }
        div[data-testid="stTextInput"] input {
            background-color: #ffffff !important;
            color: #1e293b !important;
            border: 2px solid #0284c7 !important;
            border-radius: 8px !important;
            padding: 8px 12px !important;
            font-weight: 500;
        }
        
        /* Realce para campos desativados (Status Atual) */
        div[data-testid="stTextInput"] input:disabled {
            background-color: #e0f2fe !important;
            color: #0369a1 !important;
            font-weight: 700 !important;
            border: 2px solid #38bdf8 !important;
            -webkit-text-fill-color: #0369a1 !important;
        }

        div.stButton > button {
            background-color: #0284c7;
            color: white;
            font-weight: 600;
            border-radius: 8px;
            padding: 0.4rem 0.8rem;
            font-size: 14px;
            border: none;
        }
        div.stButton > button:hover { background-color: #0369a1; }
        .stTabs [data-baseweb="tab-list"] { gap: 12px; }
        .stTabs [data-baseweb="tab"] {
            background-color: #ffffff;
            border-radius: 8px 8px 0px 0px;
            padding: 10px 20px;
            font-weight: 600;
            color: #475569;
            border: 1px solid #e2e8f0;
        }
        .stTabs [aria-selected="true"] {
            background-color: #0284c7 !important;
            color: white !important;
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 1. CONFIGURAÇÃO E MIGRAÇÃO DO BANCO DE DADOS
# ==========================================
DB_NAME = "secretaria_teixeiras_v2.db"

def init_db():
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS exames (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            protocolo TEXT UNIQUE NOT NULL,
            data_coleta TEXT NOT NULL,
            nome_paciente TEXT NOT NULL,
            tipo_exame TEXT NOT NULL,
            status TEXT NOT NULL,
            data_chegada TEXT,
            data_entrega TEXT,
            recebido_por TEXT,
            data_protocolo TEXT
        )
    """)
  conn.commit()
  conn.close()

init_db()

# ==========================================
# 2. GERAÇÃO DE PDF DUAS VIAS
# ==========================================
class PDFProtocoloDuasVias(FPDF):
  pass

def gerar_pdf_protocolo(dados):
  pdf = PDFProtocoloDuasVias(orientation="P", unit="mm", format="A5")
  pdf.set_auto_page_break(auto=False, margin=5)
  pdf.add_page()

  def desenhar_via(titulo_via):
    pdf.set_font("Arial", "B", 8)
    pdf.cell(0, 4, f"SEC. MUN. DE SAÚDE DE TEIXEIRAS - COMPROVANTE DE EXAME ({titulo_via})", border=0, align="C")
    pdf.ln(4)

    pdf.set_fill_color(30, 58, 138)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 8)
    pdf.cell(0, 4, f" PROTOCOLO: {dados['protocolo']}", border=1, fill=True, ln=True)

    pdf.set_text_color(0, 0, 0)
    campos = [
        ("Data Coleta:", dados["data_coleta"], "Retirada:", dados["data_entrega"]),
        ("Paciente:", dados["nome_paciente"], "Atendente:", dados["recebido_por"]),
        ("Exames:", dados["tipo_exame"], "", "")
    ]

    for rot1, val1, rot2, val2 in campos:
      pdf.set_font("Arial", "B", 7)
      pdf.cell(18, 4, rot1, border=1)
      pdf.set_font("Arial", "", 7)
      pdf.cell(48, 4, str(val1), border=1)

      if rot2:
        pdf.set_font("Arial", "B", 7)
        pdf.cell(18, 4, rot2, border=1)
        pdf.set_font("Arial", "", 7)
        pdf.cell(48, 4, str(val2), border=1, ln=True)
      else:
        pdf.ln(4)

    pdf.set_font("Arial", "I", 6.5)
    pdf.multi_cell(0, 3, "Declaro que recebi os resultados dos exames descritos acima, conferindo a integridade e ciente das orientações.")
    pdf.ln(3)

    pdf.set_font("Arial", "", 7)
    pdf.cell(66, 3, "_" * 32, align="C")
    pdf.cell(66, 3, "_" * 32, align="C", ln=True)
    pdf.cell(66, 3, "Assinatura do Paciente / Responsável", align="C")
    pdf.cell(66, 3, "Assinatura / Carimbo do Atendente", align="C", ln=True)

  desenhar_via("VIA DA UNIDADE / PACIENTE")
  pdf.ln(4)
  pdf.set_font("Arial", "I", 6)
  pdf.cell(0, 3, "-" * 95 + " (Destaque aqui) " + "-" * 95, align="C", ln=True)
  pdf.ln(4)
  desenhar_via("VIA DE CONTROLE")

  return pdf.output(dest="S").encode("latin1")

# ==========================================
# 3. INTERFACE VISUAL E MODAIS
# ==========================================
st.markdown("""
    <div class="header-container">
        <p class="header-title">🏥 Secretaria Municipal de Saúde de Teixeiras</p>
        <p class="header-subtitle">Sistema de Controle de Protocolos, Coletas e Entrega de Exames</p>
    </div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs([
    "🏠 Início / Atendimento", 
    "📊 Relatório Geral",
    "⚙️ Manutenção do Sistema"
])

conn = sqlite3.connect(DB_NAME, check_same_thread=False)
cursor = conn.cursor()

@st.dialog("📝 Registrar Novo Exame Coletado", width="large")
def modal_novo_protocolo():
  with st.form("form_cadastro_modal"):
    col1, col2 = st.columns(2)
    with col1:
      data_coleta_input = st.date_input("Data da Coleta", datetime.now(), format="DD/MM/YYYY")
    with col2:
      nome_paciente = st.text_input("Nome Completo do Paciente")
    
    tipo_exame = st.text_input("Tipo de Exame (ex: Hemograma, Preventivo...)")
    responsavel_cadastro = st.text_input("Responsável pelo Protocolo (Quem realizou o atendimento)")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
      submitted = st.form_submit_button("💾 Salvar Registro de Exame")
    with col_f2:
      fechar = st.form_submit_button("❌ Fechar Janela")

    if fechar:
      st.rerun()

    if submitted:
      if nome_paciente:
        num_protocolo = f"TX-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        data_coleta_str = data_coleta_input.strftime("%d/%m/%Y")
        data_protocolo_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        try:
          cursor.execute("""
                        INSERT INTO exames (protocolo, data_coleta, nome_paciente, tipo_exame, status, recebido_por, data_protocolo)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (num_protocolo, data_coleta_str, nome_paciente, tipo_exame, "Pronto para entrega", "", data_protocolo_str))
          conn.commit()
          st.success(f"🎉 Registro salvo! Protocolo: **{num_protocolo}**")
          st.rerun()
        except Exception as e:
          st.error(f"Erro ao salvar: {e}")
      else:
        st.warning("Preencha o Nome Completo do Paciente.")

@st.dialog("📦 Gerenciar e Entregar Exames", width="large")
def modal_entregar_exames():
  busca_modal = st.text_input("🔎 Digite o Nome do Paciente:", key="busca_modal_input")

  if busca_modal:
    cursor.execute("SELECT * FROM exames WHERE nome_paciente LIKE ? ORDER BY id DESC", (f"%{busca_modal}%",))
    registros = cursor.fetchall()

    if registros:
      for reg in registros:
        with st.expander(f"📌 Data: {reg[9] or 'N/D'} | {reg[1]} | {reg[3]} | Exame: {reg[4]} | Status: [{reg[5]}]"):
          with st.form(f"form_update_{reg[0]}"):
            status_atual = reg[5] if reg[5] else "Pronto para entrega"

            c1, c2 = st.columns(2)
            with c1:
              st.text_input("Status Atual", value=status_atual, disabled=True, key=f"status_txt_{reg[0]}")
            with c2:
              valor_inicial_retirado = reg[8] if reg[8] is not None else ""
              recebido_por = st.text_input("Retirado por", value=valor_inicial_retirado, key=f"rec_por_{reg[0]}")

            liberar = st.form_submit_button("🚀 Liberar Exame")
            if liberar:
              novo_status = "Exame retirado"
              d_entrega = datetime.now().strftime("%d/%m/%Y")
              cursor.execute("""
                            UPDATE exames SET status = ?, data_entrega = ?, recebido_por = ? WHERE id = ?
                        """, (novo_status, d_entrega, recebido_por, reg[0]))
              conn.commit()
              st.success("✅ Exame atualizado com sucesso!")
              st.rerun()

          cursor.execute("SELECT status, data_entrega, recebido_por FROM exames WHERE id = ?", (reg[0],))
          status_atual_db = cursor.fetchone()

          if status_atual_db and status_atual_db[0] == "Exame retirado":
            dados_dict = {
                "protocolo": reg[1],
                "data_coleta": reg[2],
                "nome_paciente": reg[3],
                "tipo_exame": reg[4],
                "recebido_por": status_atual_db[2] or "Não informado",
                "data_entrega": status_atual_db[1] or datetime.now().strftime("%d/%m/%Y")
            }
            pdf_bytes = gerar_pdf_protocolo(dados_dict)
            b64 = base64.b64encode(pdf_bytes).decode("utf-8")
            href = f'<a href="data:application/pdf;base64,{b64}" download="Protocolo_{reg[1]}.pdf" target="_blank" style="display:inline-block;padding:8px 14px;background-color:#1e3a8a;color:white;text-decoration:none;border-radius:6px;font-weight:600;margin-top:5px;">🖨️ Imprimir Comprovante de Entrega (PDF)</a>'
            st.markdown(href, unsafe_allow_html=True)
    else:
      st.warning("Nenhum exame encontrado.")

  if st.button("❌ Fechar Janela", key="fechar_modal_entrega"):
    st.rerun()

with tab1:
  st.markdown("### 📋 Painel de Atendimento")
  col_b1, col_b2, col_vazio = st.columns([1.5, 1.5, 2])
  with col_b1:
    if st.button("➕ Novo Protocolo"):
      modal_novo_protocolo()
  with col_b2:
    if st.button("📦 Entregar Exames"):
      modal_entregar_exames()

with tab2:
  st.markdown("### Relatório Geral de Exames")
  import pandas as pd
  df = pd.read_sql("SELECT * FROM exames", conn)
  st.dataframe(df, use_container_width=True)
  csv = df.to_csv(index=False).encode("utf-8")
  st.download_button("📥 Baixar Relatório em CSV", csv, "relatorio_exames_teixeiras.csv", "csv")

with tab3:
  st.markdown("### ⚙️ Manutenção do Sistema e Backup")
  col_maint1, col_maint2, col_maint3 = st.columns(3)
  
  with col_maint1:
    try:
      with open(DB_NAME, "rb") as f:
        db_bytes = f.read()
      st.download_button("📥 Baixar Backup (.db)", db_bytes, f"backup_{datetime.now().strftime('%Y-%m-%d')}.db", "application/octet-stream")
    except Exception as e:
      st.error(f"Erro: {e}")

  with col_maint2:
    arquivo_backup = st.file_uploader("Restaurar Banco (.db)", type=["db"])
    if arquivo_backup is not None and st.button("🚀 Confirmar Restauração"):
      with open(DB_NAME, "wb") as f:
        f.write(arquivo_backup.getbuffer())
      st.success("Restaurado! Recarregue a página.")

  with col_maint3:
    st.markdown("⚠️ **Zona de Perigo**")
    if st.button("🗑️ Zerar / Limpar Banco de Dados"):
      try:
        conn.close()
        if os.path.exists(DB_NAME):
          os.remove(DB_NAME)
        st.success("Banco de dados limpo e zerado com sucesso!")
        st.rerun()
      except Exception as e:
        st.error(f"Erro ao zerar banco: {e}")
