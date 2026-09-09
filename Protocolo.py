from datetime import datetime
import os
import sqlite3
from fpdf import FPDF
import pandas as pd
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
        
        /* Caixa unificada do cabeçalho estilo painel profissional */
        .header-container {
            background: linear-gradient(135deg, #1e3a8a 0%, #0284c7 100%);
            padding: 18px 25px;
            border-radius: 12px;
            color: white;
            margin-bottom: 25px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header-left-side {
            display: flex;
            flex-direction: column;
        }
        
        .header-title-text {
            font-size: 22px !important;
            font-weight: 700 !important;
            margin: 0 !important;
            color: #ffffff !important;
        }
        
        .header-subtitle-text {
            font-size: 13px !important;
            color: #e0f2fe !important;
            margin: 3px 0 0 0 !important;
        }
        
        .header-right-side {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 5px;
        }
        
        .user-info-badge {
            font-size: 13px !important;
            color: #f1f5f9 !important;
            text-align: right;
            margin: 0 !important;
        }

        /* Estilo customizado para o botão de sair encaixar perfeitamente */
        div[data-testid="stButton"] button {
            background-color: #dc2626 !important;
            color: white !important;
            font-weight: 600 !important;
            border-radius: 6px !important;
            padding: 0.25rem 0.75rem !important;
            font-size: 12px !important;
            border: none !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.15) !important;
            width: auto !important;
        }
        div[data-testid="stButton"] button:hover { 
            background-color: #b91c1c !important; 
        }

        label, .stTextInput label, .stSelectbox label {
            font-size: 17px !important;
            font-weight: 700 !important;
            color: #1e3a8a !important;
        }

        .stTextInput > div > div, 
        .stDateInput > div > div,
        div[data-baseweb="input"], 
        div[data-baseweb="base-input"] {
            background-color: #ffffff !important;
            background: #ffffff !important;
            border: 2px solid #1e3a8a !important;
            border-radius: 8px !important;
        }

        div[data-testid="stTextInput"] input,
        div[data-testid="stDateInput"] input {
            font-size: 17px !important;
            font-weight: 600 !important;
            color: #0f172a !important;
            background-color: #ffffff !important;
            background: #ffffff !important;
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
        }

        .card-paciente {
            background-color: #ffffff;
            border: 1px solid #cbd5e1;
            border-left: 5px solid #0284c7;
            padding: 18px;
            border-radius: 8px;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
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

        .stTabs [data-baseweb="tab-list"] { gap: 12px; }
        .stTabs [data-baseweb="tab"] {
            background-color: #ffffff;
            border-radius: 8px 8px 0px 0px;
            padding: 10px 20px;
            font-weight: 700;
            color: #475569;
            border: 1px solid #e2e8f0;
            font-size: 16px;
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
            data_protocolo TEXT,
            usuario_cadastro TEXT,
            usuario_entrega TEXT
        )
    """)
  
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs_sistema (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TEXT NOT NULL,
            usuario TEXT NOT NULL,
            acao TEXT NOT NULL,
            detalhes TEXT
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            nome_completo TEXT NOT NULL,
            perfil TEXT NOT NULL
        )
    """)

  cursor.execute("SELECT COUNT(*) FROM usuarios")
  if cursor.fetchone()[0] == 0:
    usuarios_iniciais = [
        ("admin", "123", "Administrador do Sistema", "admin"),
        ("atendente1", "123", "Atendente Recepção 1", "atendente"),
        ("atendente2", "123", "Atendente Recepção 2", "atendente")
    ]
    cursor.executemany("""
            INSERT INTO usuarios (username, senha, nome_completo, perfil)
            VALUES (?, ?, ?, ?)
        """, usuarios_iniciais)

  conn.commit()
  conn.close()

init_db()

def registrar_log(usuario, acao, detalhes=""):
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute("""
        INSERT INTO logs_sistema (data_hora, usuario, acao, detalhes)
        VALUES (?, ?, ?, ?)
    """, (datetime.now().strftime("%d/%m/%Y %H:%M:%S"), usuario, acao, detalhes))
  conn.commit()
  conn.close()

# ==========================================
# 2. CONTROLE DE ACESSO (LOGIN)
# ==========================================
if "autenticado" not in st.session_state:
  st.session_state.autenticado = False
if "usuario_atual" not in st.session_state:
  st.session_state.usuario_atual = None
if "perfil_atual" not in st.session_state:
  st.session_state.perfil_atual = None
if "nome_usuario" not in st.session_state:
  st.session_state.nome_usuario = None

if not st.session_state.autenticado:
  st.markdown("""
        <div class="header-container" style="justify-content: center; text-align: center;">
            <div>
                <p class="header-title-text">🏥 Secretaria Municipal de Saúde de Teixeiras</p>
                <p class="header-subtitle-text">Acesso Restrito ao Sistema de Controle de Exames</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

  col_l1, col_l2, col_l3 = st.columns([1, 1.2, 1])
  with col_l2:
    st.markdown("### 🔐 Identificação do Usuário")
    with st.form("form_login"):
      user_input = st.text_input("Usuário")
      senha_input = st.text_input("Senha", type="password")
      btn_login = st.form_submit_button("Entrar no Sistema")

      if btn_login:
        conn_l = sqlite3.connect(DB_NAME)
        cursor_l = conn_l.cursor()
        cursor_l.execute("SELECT senha, nome_completo, perfil FROM usuarios WHERE username = ?", (user_input.strip(),))
        res = cursor_l.fetchone()
        conn_l.close()

        if res and res[0] == senha_input:
          st.session_state.autenticado = True
          st.session_state.usuario_atual = user_input.strip()
          st.session_state.nome_usuario = res[1]
          st.session_state.perfil_atual = res[2]
          registrar_log(user_input.strip(), "LOGIN", "Usuário acessou o sistema")
          st.success("Login realizado com sucesso!")
          st.rerun()
        else:
          st.error("Usuário ou senha incorretos.")
  st.stop()

# ==========================================
# 3. GERAÇÃO DE PDF DUAS VIAS
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
# 4. INTERFACE PRINCIPAL DO SISTEMA (CABEÇALHO FLEXBOX PERFEITO)
# ==========================================
col_header_left, col_header_right = st.columns([7, 3])

with col_header_left:
  st.markdown(
      """
        <div style="background: linear-gradient(135deg, #1e3a8a 0%, #0284c7 100%); padding: 18px 22px; border-radius: 12px; color: white; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); margin-bottom: 25px;">
            <p style="font-size: 22px !important; font-weight: 700 !important; margin: 0 !important; color: #ffffff !important;">🏥 Secretaria Municipal de Saúde de Teixeiras</p>
            <p style="font-size: 13px !important; color: #e0f2fe !important; margin: 3px 0 0 0 !important;">Sistema de Controle de Protocolos, Coletas e Entrega de Exames</p>
        </div>
    """,
      unsafe_allow_html=True,
  )

with col_header_right:
  st.markdown(
      f"""
        <div style="background: linear-gradient(135deg, #0284c7 0%, #1e3a8a 100%); padding: 12px 20px; border-radius: 12px; color: white; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); margin-bottom: 25px; display: flex; flex-direction: column; align-items: flex-end; height: 76px; justify-content: center;">
            <span style="font-size: 13px !important; color: #f1f5f9 !important;">👤 <b>{st.session_state.nome_usuario}</b> ({st.session_state.perfil_atual.upper()})</span>
        </div>
    """,
      unsafe_allow_html=True,
  )
  # Botão de sair posicionado perfeitamente logo abaixo/junto ao card direito
  # Usamos um container menor ou estilizamos o botão para ficar compacto
  
  # Para manter o layout perfeitamente alinhado no topo, colocamos o botão de sair logo abaixo em formato compacto ou injetado via flex se preferir

# Melhor abordagem para alinhar o botão exatamente na mesma linha do cabeçalho direito:
