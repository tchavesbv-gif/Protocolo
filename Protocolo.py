from datetime import datetime
import base64
import io
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
        /* Estilização Geral e Cores de Fundo */
        .main {
            background-color: #f8fafc;
        }
        
        /* Cabeçalho Principal Estilizado */
        .header-container {
            background: linear-gradient(135deg, #1e3a8a 0%, #0284c7 100%);
            padding: 25px 30px;
            border-radius: 12px;
            color: white;
            margin-bottom: 25px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        .header-title {
            font-size: 26px;
            font-weight: 700;
            margin: 0;
            color: #ffffff;
        }
        .header-subtitle {
            font-size: 14px;
            color: #e0f2fe;
            margin-top: 5px;
            font-weight: 400;
        }

        /* FORÇAR FUNDO BRANCO E OPACIDADE NA BARRA DE PESQUISA */
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
            box-shadow: 0 2px 5px rgba(2, 132, 199, 0.15);
        }
        div[data-testid="stTextInput"] input:focus {
            border-color: #0369a1 !important;
            box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.25) !important;
        }

        /* Botões Gerais */
        div.stButton > button {
            background-color: #0284c7;
            color: white;
            font-weight: 600;
            border-radius: 8px;
            padding: 0.4rem 0.8rem;
            font-size: 14px;
            border: none;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            transition: all 0.3s ease;
        }
        div.stButton > button:hover {
            background-color: #0369a1;
            box-shadow: 0 4px 12px rgba(2, 132, 199, 0.2);
        }
        
        /* Ajuste de abas */
        .stTabs [data-baseweb="tab-list"] {
            gap: 12px;
        }
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
# 1. CONFIGURAÇÃO E MIGRAÇÃO DO BANCO DE DADOS (SQLite)
# ==========================================
def init_db():
  conn = sqlite3.connect("secretaria_teixeiras_exames.db")
  cursor = conn.cursor()
  
  cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='exames'")
  tabela_existe = cursor.fetchone()

  if tabela_existe:
    cursor.execute("PRAGMA table_info(exames)")
    colunas = [col[1] for col in cursor.fetchall()]

    if "cpf" in colunas or "cns" in colunas:
      cursor.execute("""
            CREATE TABLE IF NOT EXISTS exames_novos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                protocolo TEXT UNIQUE NOT NULL,
                data_coleta TEXT NOT NULL,
                nome_paciente TEXT NOT NULL,
                tipo_exame TEXT NOT NULL,
                status TEXT NOT NULL,
                data_chegada TEXT,
                data_entrega TEXT,
                recebido_por TEXT
            )
        """)
      cursor.execute("""
            SELECT id, protocolo, data_coleta, nome_paciente, tipo_exame, status, data_chegada, data_entrega, 
            COALESCE(recebido_por, '') FROM exames
        """)
      registros_antigos = cursor.fetchall()
      cursor.executemany("""
            INSERT INTO exames_novos (id, protocolo, data_coleta, nome_paciente, tipo_exame, status, data_chegada, data_entrega, recebido_por)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, registros_antigos)
      cursor.execute("DROP TABLE exames")
      cursor.execute("ALTER TABLE exames_novos RENAME TO exames")
      conn.commit()
    else:
      if "recebido_por" not in colunas:
        cursor.execute("ALTER TABLE exames ADD COLUMN recebido_por TEXT")
        conn.commit()
  else:
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
            recebido_por TEXT
        )
    """)
    conn.commit()

  conn.close()

init_db()

# ==========================================
# 2. FUNÇÃO DE GERAÇÃO DE PDF DUAS VIAS
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
# 3. INTERFACE VISUAL
# ==========================================
st.markdown("""
    <div class="header-container">
        <p class="header-title">🏥 Secretaria Municipal de Saúde de Teixeiras</p>
        <p class="header-subtitle">Sistema de Controle de Protocolos, Coletas e Entrega de Exames</p>
    </div>
""", unsafe_allow_html=True)

# Abas reduzidas (removida a aba de Consultar antiga)
tab1, tab2, tab3 = st.tabs([
    "🏠 Início / Atendimento", 
    "📊 Relatório Geral",
    "⚙️ Manutenção do Sistema"
])

conn = sqlite3.connect("secretaria_teixeiras_exames.db", check_same_thread=False)
cursor = conn.cursor()

if "mostrar_modal_cadastro" not in st.session_state:
  st.session_state["mostrar_modal_cadastro"] = False

if "mostrar_modal_entrega" not in st.session_state:
  st.session_state["mostrar_modal_entrega"] = False

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
      submitted = st.form_submit_button("💾 Salvar Registro de Exame", width="stretch")
    with col_f2:
      fechar = st.form_submit_button("❌ Fechar Janela", width="stretch")

    if fechar:
      st.session_state["mostrar_modal_cadastro"] = False
      st.rerun()

    if submitted:
      if nome_paciente:
        num_protocolo = f"TX-{datetime.now().strftime('%Y')}-{datetime.now().strftime('%m%d%H%M%S')}"
        data_coleta_str = data_coleta_input.strftime("%d/%m/%Y")

        try:
          cursor.execute("""
                        INSERT INTO exames (protocolo, data_coleta, nome_paciente, tipo_exame, status, recebido_por)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (num_protocolo, data_coleta_str, nome_paciente, tipo_exame, "Enviado ao Lab", responsavel_cadastro))
          conn.commit()
          st.success(f"🎉 Registro salvo com sucesso! Protocolo gerado: **{num_protocolo}**")
          st.session_state["mostrar_modal_cadastro"] = False
          st.rerun()
        except Exception as e:
          st.error(f"Erro ao salvar: {e}")
      else:
        st.warning("Preencha pelo menos o Nome Completo do Paciente.")

@st.dialog("📦 Gerenciar e Entregar Exames", width="large")
def modal_entregar_exames():
  st.markdown("Pesquise pelo nome do paciente para atualizar o status e emitir o comprovante.")
  busca_modal = st.text_input("🔎 Digite o Nome do Paciente:", key="busca_modal_input")

  if busca_modal:
    cursor.execute("SELECT * FROM exames WHERE nome_paciente LIKE ? ORDER BY id DESC", (f"%{busca_modal}%",))
    registros = cursor.fetchall()

    if registros:
      for reg in registros:
        with st.expander(f"📌 Protocolo: {reg[1]} | Paciente: {reg[3]} | Status: [{reg[5]}]"):
          col_a, col_b = st.columns(2)
          with col_a:
            st.write(f"**Tipo de Exame:** {reg[4]}")
            st.write(f"**Responsável Criação:** {reg[8] or 'Não informado'}")
          with col_b:
            st.write(f"**Data Coleta:** {reg[2]}")
            st.write(f"**Status Atual:** `{reg[5]}`")

          edit_key = f"edit_mode_{reg[0]}"
          if edit_key not in st.session_state:
            st.session_state[edit_key] = False

          col_btn_edit, _ = st.columns([1, 4])
          with col_btn_edit:
            if st.button("✏️ Editar Dados", key=f"btn_toggle_edit_{reg[0]}"):
              st.session_state[edit_key] = not st.session_state[edit_key]
              st.rerun()

          if st.session_state[edit_key]:
            st.markdown("---")
            with st.form(f"form_edit_dados_{reg[0]}"):
              e_col1, e_col2 = st.columns(2)
              with e_col1:
                novo_nome = st.text_input("Nome do Paciente", value=reg[3])
                nova_data_coleta = st.text_input("Data da Coleta (DD/MM/AAAA)", value=reg[2])
              with e_col2:
                novo_tipo = st.text_input("Tipo de Exame", value=reg[4])
                novo_resp = st.text_input("Responsável pelo Protocolo", value=reg[8] or "")
              
              col_salvar_edicao, col_cancelar_edicao = st.columns(2)
              with col_salvar_edicao:
                salvar_edicao = st.form_submit_button("💾 Salvar Alterações", width="stretch")
              with col_cancelar_edicao:
                cancelar_edicao = st.form_submit_button("❌ Cancelar", width="stretch")

              if cancelar_edicao:
                st.session_state[edit_key] = False
                st.rerun()

              if salvar_edicao:
                cursor.execute("""
                                UPDATE exames 
                                SET nome_paciente = ?, data_coleta = ?, tipo_exame = ?, recebido_por = ? 
                                WHERE id = ?
                            """, (novo_nome, nova_data_coleta, novo_tipo, novo_resp, reg[0]))
                conn.commit()
                st.session_state[edit_key] = False
                st.success("✅ Dados atualizados com sucesso!")
                st.rerun()

          st.markdown("---")
          with st.form(f"form_update_{reg[0]}"):
            lista_opcoes_status = ["Enviado ao Lab", "Pronto na Unidade", "Entregue"]
            status_salvo = reg[5] if reg[5] in lista_opcoes_status else "Enviado ao Lab"
            idx_status_atual = lista_opcoes_status.index(status_salvo)

            novo_status = st.selectbox(
                "Atualizar Status",
                lista_opcoes_status,
                index=idx_status_atual,
                key=f"status_sel_{reg[0]}"
            )
            recebido_por = st.text_input("Nome de quem retirou/recebeu o exame", value=reg[8] or "", key=f"rec_por_{reg[0]}")

            atualizar = st.form_submit_button("💾 Salvar Status")
            if atualizar:
              d_entrega = datetime.now().strftime("%d/%m/%Y") if novo_status == "Entregue" else (reg[7] or "")
              cursor.execute("""
                            UPDATE exames SET status = ?, data_entrega = ?, recebido_por = ? WHERE id = ?
                        """, (novo_status, d_entrega, recebido_por, reg[0]))
              conn.commit()
              st.success("✅ Status atualizado com sucesso!")
              st.rerun()

          cursor.execute("SELECT status, data_entrega, recebido_por FROM exames WHERE id = ?", (reg[0],))
          status_atual_db = cursor.fetchone()

          if status_atual_db and status_atual_db[0] == "Entregue":
            dados_dict = {
                "protocolo": reg[1],
                "data_coleta": reg[2],
                "nome_paciente": reg[3],
                "tipo_exame": reg[4],
                "recebido_por": status_atual_db[2] or "Atendente",
                "data_entrega": status_atual_db[1] or datetime.now().strftime("%d/%m/%Y")
            }
            pdf_bytes = gerar_pdf_protocolo(dados_dict)

            b64 = base64.b64encode(pdf_bytes).decode("utf-8")
            href = f'<a href="data:application/pdf;base64,{b64}" download="Protocolo_{reg[1]}.pdf" target="_blank" style="display:inline-block;padding:10px 18px;background-color:#1e3a8a;color:white;text-decoration:none;border-radius:6px;font-weight:600;margin-top:10px;box-shadow: 0 2px 4px rgba(0,0,0,0.1);">🖨️ Imprimir Comprovante Duas Vias (PDF)</a>'
            st.markdown(href, unsafe_allow_html=True)
    else:
      st.warning("Nenhum exame encontrado com este nome.")

  if st.button("❌ Fechar Janela de Entregas", width="stretch"):
    st.session_state["mostrar_modal_entrega"] = False
    st.rerun()

if st.session_state["mostrar_modal_cadastro"]:
  modal_novo_protocolo()

if st.session_state["mostrar_modal_entrega"]:
  modal_entregar_exames()

with tab1:
  st.markdown("### 📋 Painel de Atendimento")
  st.info("💡 Escolha uma das opções abaixo para iniciar o atendimento ao cidadão:")

  col_b1, col_b2, col_vazio = st.columns([1.5, 1.5, 2])

  with col_b1:
    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    if st.button("➕ Novo Protocolo", width="stretch"):
      st.session_state["mostrar_modal_cadastro"] = True
      st.rerun()

  with col_b2:
    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    if st.button("📦 Entregar Exames", width="stretch"):
      st.session_state["mostrar_modal_entrega"] = True
      st.rerun()

with tab2:
  st.markdown("### Relatório Geral de Exames")
  import pandas as pd

  df = pd.read_sql("SELECT * FROM exames", conn)
  st.dataframe(df, width="stretch")

  csv = df.to_csv(index=False).encode("utf-8")
  st.download_button(
      "📥 Baixar Relatório Completo em CSV (Excel)",
      csv,
      "relatorio_exames_teixeiras.csv",
      "csv",
  )

with tab3:
  st.markdown("### ⚙️ Manutenção do Sistema e Backup Externo")
  
  col_maint1, col_maint2 = st.columns(2)

  with col_maint1:
    st.markdown("#### 💾 1. Gerar Cópia de Segurança (Backup)")
    st.info("Baixe o arquivo completo do banco de dados contendo todos os cadastros, protocolos e históricos para guardar em local seguro.")
    
    try:
      with open("secretaria_teixeiras_exames.db", "rb") as f:
        db_bytes = f.read()
      
      data_hoje = datetime.now().strftime("%Y-%m-%d_%H-%M")
      st.download_button(
          label="📥 Baixar Backup do Banco de Dados (.db)",
          data=db_bytes,
          file_name=f"backup_exames_teixeiras_{data_hoje}.db",
          mime="application/octet-stream",
          width="stretch"
      )
    except Exception as e:
      st.error(f"Erro ao preparar o arquivo de backup: {e}")

  with col_maint2:
    st.markdown("#### 🔄 2. Restaurar Sistema a partir de Backup")
    st.warning("⚠️ **Atenção:** Enviar um arquivo de banco de dados (`.db`) antigo vai substituir os dados atuais pelos dados contidos no arquivo enviado.")
    
    arquivo_backup = st.file_uploader("Selecione o arquivo de backup (.db) para restaurar", type=["db"])
    
    if arquivo_backup is not None:
      if st.button("🚀 Confirmar e Restaurar Banco de Dados", width="stretch"):
        try:
          with open("secretaria_teixeiras_exames.db", "wb") as f:
            f.write(arquivo_backup.getbuffer())
          st.success("🎉 Sistema restaurado com sucesso! Recarregue a página para ver os dados atualizados.")
        except Exception as e:
          st.error(f"Erro ao restaurar o banco de dados: {e}")

  st.markdown("---")
  st.markdown("### 📂 Importação em Lote via Arquivo TXT / CSV")
  st.info(
      "💡 **Instruções para o arquivo TXT/CSV:**\n"
      "Cada linha do arquivo deve conter os dados separados por vírgula (`,`) ou ponto e vírgula (`;`) na seguinte ordem:\n"
      "**Nome do Paciente, Data da Coleta (DD/MM/AAAA), Tipo de Exame, Responsável**"
  )

  arquivo_txt = st.file_uploader("Selecione o arquivo TXT ou CSV para upload em lote", type=["txt", "csv"])

  if arquivo_txt is not None:
    if st.button("🚀 Processar e Importar Lote", width="stretch"):
      try:
        stringio = io.StringIO(arquivo_txt.getvalue().decode("utf-8", errors="ignore"))
        linhas = stringio.readlines()

        importados = 0
        for linha in linhas:
          linha = linha.strip()
          if not linha:
            continue

          separador = ";" if ";" in linha else ","
          partes = [p.strip() for p in linha.split(separador)]

          if len(partes) >= 1 and partes[0]:
            nome_paciente = partes[0]
            data_coleta_str = partes[1] if len(partes) > 1 and partes[1] else datetime.now().strftime("%d/%m/%Y")
            tipo_exame = partes[2] if len(partes) > 2 and partes[2] else "Exame Geral"
            responsavel_lote = partes[3] if len(partes) > 3 and partes[3] else ""

            num_protocolo = f"TX-{datetime.now().strftime('%Y')}-{datetime.now().strftime('%m%d%H%M%S')}-{importados+1}"

            cursor.execute("""
                            INSERT INTO exames (protocolo, data_coleta, nome_paciente, tipo_exame, status, recebido_por)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (num_protocolo, data_coleta_str, nome_paciente, tipo_exame, "Enviado ao Lab", responsavel_lote))
            importados += 1

        conn.commit()
        st.success(f"🎉 Sucesso! {importados} exames foram importados para o sistema.")
      except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
