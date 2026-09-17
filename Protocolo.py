from datetime import datetime
import os
from fpdf import FPDF
import pandas as pd
import streamlit as st
from supabase import create_client

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
        
        .header-box-unica {
            background: linear-gradient(135deg, #1e3a8a 0%, #0284c7 100%);
            padding: 20px 24px;
            border-radius: 12px;
            color: white;
            margin-bottom: 25px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header-title {
            font-size: 28px !important;
            font-weight: 700 !important;
            margin: 0 !important;
            color: #ffffff !important;
        }
        
        .header-subtitle {
            font-size: 16px !important;
            color: #e0f2fe !important;
            margin: 4px 0 0 0 !important;
        }
        
        .header-user-info {
            font-size: 14px !important;
            color: #f1f5f9 !important;
            text-align: right;
            margin: 0 0 4px 0;
            font-weight: 600;
        }

        div[data-testid="stButton"] button {
            background-color: #dc2626 !important;
            color: white !important;
            font-weight: 600 !important;
            border-radius: 6px !important;
            padding: 0.3rem 0.8rem !important;
            font-size: 12px !important;
            border: none !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.15) !important;
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
        .stSelectbox > div > div,
        div[data-baseweb="input"], 
        div[data-baseweb="base-input"],
        div[data-baseweb="select"] {
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
# 1. CONEXÃO COM O SUPABASE (API REST)
# ==========================================
SUPABASE_URL = "https://yqvuqhzpyvxnbglxynbh.supabase.co"
SUPABASE_KEY = "sb_publishable_gd15fFKsaKLyENPqiSLDHg_FMvSa1Ii"

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

def registrar_log(usuario, acao, detalhes=""):
    try:
        supabase.table("logs_sistema").insert({
            "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "usuario": usuario,
            "acao": acao,
            "detalhes": detalhes
        }).execute()
    except Exception:
        pass

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
    col_l1, col_l2, col_l3 = st.columns([1, 1.4, 1])
    with col_l2:
        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        
        if os.path.exists("logo_prefeitura.jpg"):
            col_img1, col_img2, col_img3 = st.columns([1, 2.2, 1])
            with col_img2:
                st.image("logo_prefeitura.jpg", width=180)
        
        st.markdown("""
            <div class="header-box-unica" style="flex-direction: column; text-align: center; margin-top: 15px; margin-bottom: 25px;">
                <p class="header-title" style="font-size: 24px !important;">Secretaria Municipal de Saúde de Teixeiras</p>
                <p class="header-subtitle">Acesso Restrito - Nuvem Segura (Supabase API)</p>
            </div>
        """, unsafe_allow_html=True)

        with st.form("form_login"):
            st.markdown("### 🔐 Identificação do Usuário")
            user_input = st.text_input("Usuário")
            senha_input = st.text_input("Senha", type="password")
            
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            btn_login = st.form_submit_button("Entrar no Sistema", use_container_width=True)

            if btn_login:
                try:
                    res = supabase.table("usuarios").select("*").eq("username", user_input.strip()).execute()
                    dados_user = res.data

                    if dados_user and dados_user[0]["senha"] == senha_input:
                        st.session_state.autenticado = True
                        st.session_state.usuario_atual = user_input.strip()
                        st.session_state.nome_usuario = dados_user[0]["nome_completo"]
                        st.session_state.perfil_atual = dados_user[0]["perfil"]
                        registrar_log(user_input.strip(), "LOGIN", "Usuário acessou o sistema")
                        st.success("Login realizado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")
                except Exception as e:
                    st.error(f"Erro ao conectar com a nuvem: {e}")
    st.stop()

# ==========================================
# 3. GERAÇÃO DE PDFS (COMPROVANTE DUAS VIAS)
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
# 4. INTERFACE PRINCIPAL DO SISTEMA
# ==========================================
col_logo, col_h1, col_h2 = st.columns([1.2, 5.8, 2.5])

with col_logo:
    if os.path.exists("logo_prefeitura.jpg"):
        st.image("logo_prefeitura.jpg", width=150)
    else:
        st.markdown("🏛️")

with col_h1:
    st.markdown("""
        <div class="header-box-unica" style="margin-bottom: 0px;">
            <div>
                <p class="header-title">Secretaria Municipal de Saúde de Teixeiras</p>
                <p class="header-subtitle">Sistema de Controle de Protocolos, Coletas e Entrega de Exames</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

with col_h2:
    st.markdown(f"""
        <div class="header-box-unica" style="flex-direction: column; align-items: flex-end; text-align: right; margin-bottom: 0px; padding: 16px 20px;">
            <p class="header-user-info">👤 <b>{st.session_state.nome_usuario}</b> ({st.session_state.perfil_atual.upper()})</p>
        </div>
    """, unsafe_allow_html=True)
    col_dummy, col_b_sair = st.columns([1, 1.2])
    with col_b_sair:
        if st.button("🚪 Sair do Sistema", key="btn_sair_sistema"):
            registrar_log(st.session_state.usuario_atual, "LOGOUT", "Usuário desconectou")
            st.session_state.autenticado = False
            st.session_state.usuario_atual = None
            st.session_state.perfil_atual = None
            st.session_state.nome_usuario = None
            st.rerun()

st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)

if st.session_state.perfil_atual == "admin":
    tab1, tab2, tab3, tab4 = st.tabs(["➕ Novo Protocolo", "📦 Entregar Exames", "📊 Relatórios", "⚙️ Manutenção & Logs"])
else:
    tab1, tab2, tab3 = st.tabs(["➕ Novo Protocolo", "📦 Entregar Exames", "📊 Relatórios"])

# ABA 1: Novo Protocolo
with tab1:
    st.markdown("### 📝 Registrar Novo Exame Coletado")

    try:
        res_tipos = supabase.table("tipos_exames").select("nome").order("nome").execute()
        lista_exames_cadastrados = [t["nome"] for t in res_tipos.data] if res_tipos.data else []
    except Exception:
        lista_exames_cadastrados = []

    if "form_version" not in st.session_state:
        st.session_state.form_version = 0

    v = st.session_state.form_version

    with st.form(f"form_cadastro_direto_{v}", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data_coleta_input = st.date_input("Data da Coleta", datetime.now(), format="DD/MM/YYYY")
        with col2:
            nome_paciente = st.text_input("Nome Completo do Paciente", key=f"val_nome_{v}")

        st.markdown("---")
        st.markdown("##### Selecione o Exame Existente ou Digite um Novo Abaixo")
        
        col_ex1, col_ex2 = st.columns(2)
        with col_ex1:
            exame_selecionado = st.selectbox(
                "Selecionar da Lista Cadastrada",
                ["-- Selecione ou digite abaixo --"] + lista_exames_cadastrados,
                key=f"sel_exame_{v}"
            )
        with col_ex2:
            exame_novo_input = st.text_input("Ou Digite um Novo Tipo de Exame", key=f"val_novo_tipo_{v}")

        submitted = st.form_submit_button("💾 Salvar Registro de Exame")

        if submitted:
            tipo_exame_final = ""
            if exame_novo_input.strip():
                tipo_exame_final = exame_novo_input.strip()
            elif exame_selecionado != "-- Selecione ou digite abaixo --":
                tipo_exame_final = exame_selecionado

            if nome_paciente and tipo_exame_final:
                num_protocolo = f"TX-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                data_coleta_str = data_coleta_input.strftime("%d/%m/%Y")
                data_protocolo_str = datetime.now().strftime("%d/%m/%Y %H:%M")
                
                try:
                    supabase.table("exames").insert({
                        "protocolo": num_protocolo,
                        "data_coleta": data_coleta_str,
                        "nome_paciente": nome_paciente,
                        "tipo_exame": tipo_exame_final,
                        "status": "Pronto para entrega",
                        "recebido_por": "",
                        "data_protocolo": data_protocolo_str,
                        "usuario_cadastro": st.session_state.nome_usuario,
                        "usuario_entrega": ""
                    }).execute()

                    if exame_novo_input.strip():
                        try:
                            supabase.table("tipos_exames").insert({"nome": exame_novo_input.strip()}).execute()
                        except Exception:
                            pass

                    registrar_log(st.session_state.usuario_atual, "NOVO_PROTOCOLO", f"Protocolo gerado: {num_protocolo} para paciente {nome_paciente} ({tipo_exame_final})")

                    st.session_state.form_version += 1
                    st.success(f"🎉 Registro salvo com sucesso! Protocolo gerado: **{num_protocolo}**")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
            else:
                st.warning("Preencha o Nome Completo do Paciente e informe o Tipo de Exame.")

# ABA 2: Entregar Exames
with tab2:
    st.markdown("### 📦 Gerenciar e Entregar Exames")

    if "busca_termo" not in st.session_state:
        st.session_state.busca_termo = ""

    busca_input = st.text_input("🔎 Digite o Nome do Paciente para Buscar:", value=st.session_state.busca_termo, key="input_busca_paciente")
    st.session_state.busca_termo = busca_input

    if busca_input:
        try:
            res_busca = supabase.table("exames").select("*").ilike("nome_paciente", f"%{busca_input}%").order("id", desc=True).execute()
            registros = res_busca.data
        except Exception as e:
            registros = []
            st.error(f"Erro na busca: {e}")

        if registros:
            st.markdown(f"**Encontrado(s) {len(registros)} registro(s):**")
            for reg in registros:
                id_reg = reg["id"]
                protocolo = reg["protocolo"]
                data_coleta = reg["data_coleta"]
                nome_paciente = reg["nome_paciente"]
                tipo_exame = reg["tipo_exame"]
                status_atual = reg["status"] if reg["status"] else "Pronto para entrega"
                data_entrega_db = reg["data_entrega"] or ""
                recebido_por_db = reg["recebido_por"] or ""
                data_protocolo = reg["data_protocolo"] or "N/D"
                usr_cad = reg["usuario_cadastro"] or "N/D"
                usr_ent = reg["usuario_entrega"] or "N/D"

                with st.container():
                    st.markdown(f"""
                        <div class="card-paciente">
                            <b>📌 Protocolo:</b> {protocolo} | <b>Data Registro:</b> {data_protocolo} (Cadastrado por: <i>{usr_cad}</i>)<br>
                            <b>👤 Paciente:</b> <span style="font-size:16px; color:#1e3a8a; font-weight:bold;">{nome_paciente}</span><br>
                            <b>🧪 Exame:</b> {tipo_exame} | <b>Coleta:</b> {data_coleta}
                        </div>
                    """, unsafe_allow_html=True)

                    if status_atual == "Exame retirado":
                        col_st1, col_st2 = st.columns(2)
                        with col_st1:
                            st.markdown('<div class="status-badge-verde">✔️ Exame retirado</div>', unsafe_allow_html=True)
                        with col_st2:
                            st.markdown(f"""
                                <div class="info-retirada-box">
                                    👤 Retirado por: <b>{recebido_por_db}</b><br>
                                    📅 Data: <b>{data_entrega_db}</b> | Entregue por: <b>{usr_ent}</b>
                                </div>
                            """, unsafe_allow_html=True)

                        st.markdown("---")
                        dados_pdf = {
                            "protocolo": protocolo,
                            "data_coleta": data_coleta,
                            "nome_paciente": nome_paciente,
                            "tipo_exame": tipo_exame,
                            "data_entrega": data_entrega_db or datetime.now().strftime("%d/%m/%Y"),
                            "recebido_por": recebido_por_db
                        }
                        pdf_bytes = gerar_pdf_protocolo(dados_pdf)

                        st.download_button(
                            label=f"📄 BAIXAR / IMPRIMIR COMPROVANTE (PDF) - {protocolo}",
                            data=pdf_bytes,
                            file_name=f"comprovante_{protocolo}.pdf",
                            mime="application/pdf",
                            key=f"dl_pdf_retirado_{id_reg}"
                        )
                    else:
                        col_st1, col_st2 = st.columns(2)
                        with col_st1:
                            st.markdown('<div class="status-badge-verde" style="background-color: #0284c7;">🟢 Pronto para entrega</div>', unsafe_allow_html=True)
                        with col_st2:
                            recebido_por_input = st.text_input("Retirado por (Nome de quem vai buscar)", value="", key=f"rec_por_{id_reg}")

                        if st.button("🚀 Concluir Retirada e Liberar Comprovante", key=f"btn_liberar_{id_reg}"):
                            if recebido_por_input.strip():
                                novo_status = "Exame retirado"
                                d_entrega = datetime.now().strftime("%d/%m/%Y")

                                try:
                                    supabase.table("exames").update({
                                        "status": novo_status,
                                        "data_entrega": d_entrega,
                                        "recebido_por": recebido_por_input.strip(),
                                        "usuario_entrega": st.session_state.nome_usuario
                                    }).eq("id", id_reg).execute()

                                    registrar_log(st.session_state.usuario_atual, "ENTREGA_EXAME", f"Exame do protocolo {protocolo} entregue para {recebido_por_input.strip()}")

                                    st.success("✅ Exame concluído com sucesso! Atualizando visualização...")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao atualizar: {e}")
                            else:
                                st.warning("Por favor, preencha o nome de quem está retirando o exame.")

                    st.markdown("<hr style='margin: 20px 0; border: 1px solid #e2e8f0;'>", unsafe_allow_html=True)
        else:
            st.warning("Nenhum exame encontrado com este nome.")

# ABA 3: Relatórios
with tab3:
    st.markdown("### 📊 Relatório Geral do Sistema")
    try:
        res_exames = supabase.table("exames").select("*").order("id", desc=True).execute()
        df = pd.DataFrame(res_exames.data)
    except Exception:
        df = pd.DataFrame()

    st.dataframe(df, use_container_width=True)
    if not df.empty:
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Baixar Relatório em CSV", csv, "relatorio_exames_teixeiras.csv", "csv")

# ABA 4: Manutenção e Logs (Exclusiva para Admin)
if st.session_state.perfil_atual == "admin":
    with tab4:
        st.markdown("### ⚙️ Gerenciamento de Usuários do Sistema")

        if "form_user_version" not in st.session_state:
            st.session_state.form_user_version = 0
        uv = st.session_state.form_user_version

        with st.form(f"form_cadastrar_usuario_admin_{uv}"):
            st.markdown("**Cadastrar Novo Usuário (Atendente ou Admin)**")
            col_u1, col_u2, col_u3, col_u4 = st.columns(4)
            with col_u1:
                novo_user_log = st.text_input("Nome de Usuário (Login)", key=f"u_log_{uv}")
            with col_u2:
                novo_user_senha = st.text_input("Senha", type="password", key=f"u_sen_{uv}")
            with col_u3:
                novo_user_nome = st.text_input("Nome Completo", key=f"u_nom_{uv}")
            with col_u4:
                novo_user_perfil = st.selectbox("Perfil", ["atendente", "admin"], key=f"u_prf_{uv}")

            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            btn_salvar_novo_user = st.form_submit_button("✅ Confirmar e Cadastrar Novo Usuário")
            
            if btn_salvar_novo_user:
                if novo_user_log and novo_user_senha and novo_user_nome:
                    try:
                        supabase.table("usuarios").insert({
                            "username": novo_user_log.strip(),
                            "senha": novo_user_senha,
                            "nome_completo": novo_user_nome.strip(),
                            "perfil": novo_user_perfil
                        }).execute()

                        registrar_log(st.session_state.usuario_atual, "CRIACAO_USUARIO", f"Criado usuário {novo_user_log.strip()} com perfil {novo_user_perfil}")

                        st.session_state.form_user_version += 1
                        st.success(f"🎉 Usuário criado com sucesso! O login **{novo_user_log.strip()}** já está ativo no sistema.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro (verifique se o usuário já existe): {e}")
                else:
                    st.warning("Preencha todos os campos do novo usuário antes de confirmar.")

        st.markdown("---")
        st.markdown("### 📋 Usuários Cadastrados no Sistema")
        try:
            res_users = supabase.table("usuarios").select("id, username, nome_completo, perfil").execute()
            df_usuarios = pd.DataFrame(res_users.data)
        except Exception:
            df_usuarios = pd.DataFrame()
        st.dataframe(df_usuarios, use_container_width=True)

        st.markdown("---")
        st.markdown("### 🛠️ Ferramentas de Auditoria e Logs")
        try:
            res_logs = supabase.table("logs_sistema").select("*").order("id", desc=True).execute()
            df_logs = pd.DataFrame(res_logs.data)
        except Exception:
            df_logs = pd.DataFrame()
        st.dataframe(df_logs, use_container_width=True)
        if not df_logs.empty:
            csv_logs = df_logs.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Baixar Logs de Auditoria (CSV)", csv_logs, "logs_auditoria_teixeiras.csv", "csv")
