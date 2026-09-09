from datetime import datetime
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

        .status-badge-verde {
            background-color: #10b981;
            color: white;
            padding: 6px 12px;
            border-radius: 6px;
            font-weight: 700;
            text-align: center;
            font-size: 13px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: inline-block;
            margin-top: 8px;
        }

        .info-retirada-box {
            background-color: #f1f5f9;
            border-left: 4px solid #10b981;
            padding: 10px 15px;
            border-radius: 6px;
            margin-top: 8px;
            font-size: 14px;
            color: #1e293b;
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
        ("Paciente:", dados["nome_paciente"], "Retirado por:", dados["recebido_por"]),
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
# 3. INTERFACE VISUAL E TELAS
# ==========================================
st.markdown("""
    <div class="header-container">
        <p class="header-title">🏥 Secretaria Municipal de Saúde de Teixeiras</p>
        <p class="header-subtitle">Sistema de Controle de Protocolos, Coletas e Entrega de Exames</p>
    </div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs([
    "🏠 Início / Atendimento", 
    "➕ Novo Protocolo",
    "📦 Entregar Exames",
    "⚙️ Relatórios e Manutenção"
])

conn = sqlite3.connect(DB_NAME, check_same_thread=False)
cursor = conn.cursor()

# ABA 1: Início
with tab1:
  st.markdown("### 📋 Bem-vindo ao Sistema de Controle")
  st.info("Utilize as abas acima para registrar novos exames ou gerenciar a entrega de resultados com emissão instantânea de comprovantes em PDF.")
  
  col_info1, col_info2 = st.columns(2)
  with col_info1:
    cursor.execute("SELECT COUNT(*) FROM exames WHERE status != 'Exame retirado'")
    pendentes = cursor.fetchone()[0]
    st.metric("Exames Pendentes / Prontos", pendentes)
  with col_info2:
    cursor.execute("SELECT COUNT(*) FROM exames WHERE status = 'Exame retirado'")
    retirados = cursor.fetchone()[0]
    st.metric("Exames Já Retirados", retirados)

# ABA 2: Novo Protocolo
with tab2:
  st.markdown("### 📝 Registrar Novo Exame Coletado")

  if "form_version" not in st.session_state:
    st.session_state.form_version = 0

  v = st.session_state.form_version

  with st.form(f"form_cadastro_direto_{v}", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
      data_coleta_input = st.date_input("Data da Coleta", datetime.now(), format="DD/MM/YYYY")
    with col2:
      nome_paciente = st.text_input("Nome Completo do Paciente", key=f"val_nome_{v}")
    
    tipo_exame = st.text_input("Tipo de Exame (ex: Hemograma, Preventivo...)", key=f"val_tipo_{v}")
    responsavel_cadastro = st.text_input("Responsável pelo Protocolo (Quem realizou o atendimento)", key=f"val_resp_{v}")

    submitted = st.form_submit_button("💾 Salvar Registro de Exame")

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
          
          st.session_state.form_version += 1
          st.success(f"🎉 Registro salvo com sucesso! Protocolo gerado: **{num_protocolo}**")
          st.rerun()
        except Exception as e:
          st.error(f"Erro ao salvar: {e}")
      else:
        st.warning("Preencha o Nome Completo do Paciente.")

# ABA 3: Entregar Exames
with tab3:
  st.markdown("### 📦 Gerenciar e Entregar Exames")
  busca_input = st.text_input("🔎 Digite o Nome do Paciente para Buscar:", key="busca_aba_entrega")

  if busca_input:
    cursor.execute("SELECT * FROM exames WHERE nome_paciente LIKE ? ORDER BY id DESC", (f"%{busca_input}%",))
    registros = cursor.fetchall()

    if registros:
      st.markdown(f"**Encontrado(s) {len(registros)} registro(s):**")
      for reg in registros:
        id_reg = reg[0]

        with st.expander(f"📌 Data: {reg[9] or 'N/D'} | Protocolo: {reg[1]} | Paciente: {reg[3]} | Exame: {reg[4]} | Status: [{reg[5]}]"):
          status_atual = reg[5] if reg[5] else "Pronto para entrega"

          # Valida diretamente pelo banco de dados se o status já é "Exame retirado"
          if status_atual == "Exame retirado":
            c1, c2 = st.columns(2)
            with c1:
              st.markdown("Status Atual")
              st.markdown('<div class="status-badge-verde">✔️ Exame retirado</div>', unsafe_allow_html=True)
            with c2:
              st.markdown("Detalhes da Retirada")
              nome_retirou = reg[8] if reg[8] else "Não informado"
              data_retirada = reg[7] if reg[7] else datetime.now().strftime("%d/%m/%Y")
              st.markdown(f"""
                <div class="info-retirada-box">
                    👤 Retirado por: <b>{nome_retirou}</b><br>
                    📅 Data da Retirada: <b>{data_retirada}</b>
                </div>
              """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("### 🖨️ Emissão de Comprovante")
            
            dados_pdf = {
                "protocolo": reg[1],
                "data_coleta": reg[2],
                "nome_paciente": reg[3],
                "tipo_exame": reg[4],
                "data_entrega": reg[7] or datetime.now().strftime("%d/%m/%Y"),
                "recebido_por": reg[8] or ""
            }
            pdf_bytes = gerar_pdf_protocolo(dados_pdf)
            
            st.download_button(
                label="📄 CLIQUE AQUI PARA BAIXAR / IMPRIMIR COMPROVANTE (PDF)",
                data=pdf_bytes,
                file_name=f"comprovante_{reg[1]}.pdf",
                mime="application/pdf",
                key=f"dl_pdf_retirado_{id_reg}"
            )

          else:
            c1, c2 = st.columns(2)
            with c1:
              st.markdown("Status Atual")
              st.markdown('<div class="status-badge-verde">🟢 Pronto para entrega</div>', unsafe_allow_html=True)
            with c2:
              recebido_por_input = st.text_input("Retirado por (Nome de quem vai buscar o exame)", value="", key=f"rec_por_{id_reg}")

            if st.button("🚀 Concluir Retirada", key=f"btn_liberar_{id_reg}"):
              if recebido_por_input.strip():
                novo_status = "Exame retirado"
                d_entrega = datetime.now().strftime("%d/%m/%Y")
                
                # Salva o nome da pessoa que retirou corretamente na coluna recebido_por
                cursor.execute("""
                              UPDATE exames SET status = ?, data_entrega = ?, recebido_por = ? WHERE id = ?
                          """, (novo_status, d_entrega, recebido_por_input, id_reg))
                conn.commit()
                
                st.success("✅ Exame concluído com sucesso!")
                st.rerun()
              else:
                st.warning("Por favor, preencha o nome de quem está retirando o exame antes de concluir.")
    else:
      st.warning("Nenhum exame encontrado com este nome.")

# ABA 4: Relatórios e Manutenção
with tab4:
  st.markdown("### 📊 Relatório Geral e Manutenção do Sistema")
  
  import pandas as pd
  df = pd.read_sql("SELECT * FROM exames", conn)
  st.dataframe(df, use_container_width=True)
  csv = df.to_csv(index=False).encode("utf-8")
  st.download_button("📥 Baixar Relatório em CSV", csv, "relatorio_exames_teixeiras.csv", "csv")

  st.markdown("---")
  st.markdown("### ⚙️ Backup e Segurança")
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
      st.success("Restaurado com sucesso! Recarregue a página.")

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
