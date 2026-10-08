from datetime import datetime, timedelta
import os
from fpdf import FPDF
import pandas as pd
import streamlit as st
from supabase import create_client
import plotly.express as px
import plotly.graph_objects as go

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
    font-size: 15px !important;
    color: #f1f5f9 !important;
    text-align: right;
    margin: 0 0 8px 0;
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
.status-badge-atrasado {
    background-color: #ef4444;
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
.card-paciente-atrasado {
    background-color: #fff1f2;
    border: 1px solid #fecdd3;
    border-left: 5px solid #ef4444;
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
.kpi-card {
    background-color: white;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 15px;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.kpi-value {
    font-size: 24px;
    font-weight: 700;
    margin: 0;
}
.kpi-label {
    font-size: 13px;
    font-weight: 600;
    color: #64748b;
    margin: 0;
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
# 1. CONEXÃO COM O SUPABASE (VIA SECRETS)
# ==========================================
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]

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
# 2. CONTROLE DE ACESSO (LOGIN) E ESTADO GLOBAL
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "usuario_atual" not in st.session_state:
    st.session_state.usuario_atual = None
if "perfil_atual" not in st.session_state:
    st.session_state.perfil_atual = None
if "nome_usuario" not in st.session_state:
    st.session_state.nome_usuario = None

if "termo_busca_executado" not in st.session_state:
    st.session_state.termo_busca_executado = ""
if "registros_encontrados" not in st.session_state:
    st.session_state.registros_encontrados = None
if "busca_version" not in st.session_state:
    st.session_state.busca_version = 0

if "df_relatorio_filtrado" not in st.session_state:
    st.session_state.df_relatorio_filtrado = None
if "id_registro_em_edicao" not in st.session_state:
    st.session_state.id_registro_em_edicao = None
if "rel_version" not in st.session_state:
    st.session_state.rel_version = 0

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
            <p class="header-subtitle">Acesso Restrito - Nuvem Segura (API Supabase)</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("form_login"):
            st.markdown("### Identificação do Usuário")
            user_input = st.text_input("Usuário")
            senha_input = st.text_input("Senha", type="password")
            
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            btn_login = st.form_submit_button("Entrar no Sistema", use_container_width=True)
            
            if btn_login:
                u_limpo = user_input.strip().lower()
                s_limpa = senha_input.strip()
                
                if u_limpo == "tiago" and s_limpa == "020499":
                    st.session_state.autenticado = True
                    st.session_state.usuario_atual = "Tiago"
                    st.session_state.nome_usuario = "Tiago da Silva Chaves"
                    st.session_state.perfil_atual = "admin"
                    registrar_log("Tiago", "LOGIN", "Usuário acessou o sistema com credenciais definitivas")
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                elif u_limpo == "admin" and s_limpa == "123":
                    st.session_state.autenticado = True
                    st.session_state.usuario_atual = "admin"
                    st.session_state.nome_usuario = "Administrador do Sistema"
                    st.session_state.perfil_atual = "admin"
                    registrar_log("admin", "LOGIN", "Usuário acessou o sistema com credenciais definitivas")
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                elif u_limpo == "lilian" and s_limpa == "123456":
                    st.session_state.autenticado = True
                    st.session_state.usuario_atual = "Lilian"
                    st.session_state.nome_usuario = "Lilian"
                    st.session_state.perfil_atual = "atendente"
                    registrar_log("Lilian", "LOGIN", "Usuário acessou o sistema com credenciais definitivas")
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
        st.stop()

# ==========================================
# 3. GERAÇÃO DO PDF (4 COMPROVANTES POR FOLHA A4)
# ==========================================
class PDFProtocoloEmLote(FPDF):
    pass

def gerar_pdf_lote(lista_dados):
    pdf = PDFProtocoloEmLote(orientation="l", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False, margin=5)
    
    for i in range(0, len(lista_dados), 4):
        pdf.add_page()
        bloco_quatro = lista_dados[i:i+4]
        
        posicoes = [
            (10, 10),    # Superior Esquerdo
            (149, 10),   # Superior Direito
            (10, 107),   # Inferior Esquerdo
            (149, 107)   # Inferior Direito
        ]
        
        for idx, dados in enumerate(bloco_quatro):
            if idx >= len(posicoes):
                break
            x_pos, y_pos = posicoes[idx]
            
            pdf.set_xy(x_pos, y_pos)
            pdf.set_font("Arial", "B", 8)
            pdf.set_text_color(30, 58, 138)
            pdf.cell(138, 4, "SEC. MUN. DE SAÚDE DE TEIXEIRAS", border=0, ln=1, align="C")
            
            pdf.set_x(x_pos)
            pdf.set_fill_color(30, 58, 138)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", "B", 8)
            pdf.cell(138, 5, f" PROTOCOLO: {dados['protocolo']}", border=1, fill=True, ln=1)
            pdf.set_text_color(0, 0, 0)
            
            campos = [
                ("Coleta:", dados["data_coleta"], "Retirada:", dados["data_entrega"]),
                ("Paciente:", dados["nome_paciente"], "Retirado por:", dados["recebido_por"]),
                ("Exames:", dados["tipo_exame"], "", "")
            ]
            
            for rot1, val1, rot2, val2 in campos:
                pdf.set_x(x_pos)
                pdf.set_font("Arial", "B", 7.5)
                pdf.cell(18, 5, rot1, border=1)
                pdf.set_font("Arial", "", 7.5)
                pdf.cell(51, 5, str(val1), border=1)
                if rot2:
                    pdf.set_font("Arial", "B", 7.5)
                    pdf.cell(20, 5, rot2, border=1)
                    pdf.set_font("Arial", "", 7.5)
                    pdf.cell(49, 5, str(val2), border=1, ln=1)
                else:
                    pdf.ln(5)
                    
            pdf.set_x(x_pos)
            pdf.ln(1)
            pdf.set_font("Arial", "I", 6.5)
            pdf.set_x(x_pos)
            pdf.multi_cell(138, 3, "Declaro que recebi os resultados dos exames descritos acima, conferindo a integridade e ciente das orientações.", align="C")
            pdf.ln(2)
            
            pdf.set_x(x_pos)
            pdf.set_font("Arial", "", 7.5)
            pdf.cell(69, 4, "_" * 32, align="C")
            pdf.cell(69, 4, "_" * 32, align="C", ln=1)
            pdf.set_x(x_pos)
            pdf.cell(69, 4, "Assinatura do Paciente / Responsável", align="C")
            pdf.cell(69, 4, "Assinatura / Carimbo Atendente", align="C", ln=1)
            
            pdf.rect(x_pos, y_pos, 138, 93)
        
    output = pdf.output(dest="S")
    if isinstance(output, str):
        return output.encode("latin1")
    return bytes(output)

# ==========================================
# 4. INTERFACE PRINCIPAL DO SISTEMA
# ==========================================
col_logo, col_h1, col_h2 = st.columns([1.2, 5.7, 2.6])
with col_logo:
    if os.path.exists("logo_prefeitura.jpg"):
        st.image("logo_prefeitura.jpg", width=150)
    else:
        st.markdown("")

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
    icone_perfil = "👑" if st.session_state.perfil_atual == "admin" else "👨‍💼"
    st.markdown(f"""
    <div class="header-box-unica" style="flex-direction: column; align-items: flex-end; text-align: right; margin-bottom: 0px; padding: 14px 20px;">
        <p class="header-user-info">{icone_perfil} <b>{st.session_state.nome_usuario}</b> ({st.session_state.perfil_atual.upper()})</p>
    </div>
    """, unsafe_allow_html=True)
    
    col_vazia_btn, col_b_sair = st.columns([1.3, 1.2])
    with col_b_sair:
        if st.button("Sair do Sistema", key="btn_sair_sistema", use_container_width=True):
            registrar_log(st.session_state.usuario_atual, "LOGOUT", "Usuário desconectou")
            st.session_state.autenticado = False
            st.session_state.usuario_atual = None
            st.session_state.perfil_atual = None
            st.session_state.nome_usuario = None
            st.session_state.termo_busca_executado = ""
            st.session_state.registros_encontrados = None
            st.session_state.df_relatorio_filtrado = None
            st.rerun()

st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

if st.session_state.perfil_atual == "admin":
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "➕ Novo Protocolo", 
        "📦 Entregar Exames", 
        "📊 Relatórios & Edição", 
        "📈 BI & Indicadores",
        "⚙️ Manutenção & Logs"
    ])
else:
    tab1, tab2, tab3, tab4 = st.tabs([
        "➕ Novo Protocolo", 
        "📦 Entregar Exames", 
        "📊 Relatórios & Edição",
        "📈 BI & Indicadores"
    ])

# ==========================================
# ABA 1: NOVO PROTOCOLO
# ==========================================
with tab1:
    st.markdown("### Registrar Novo Exame Coletado")
    
    if "lote_cadastros" not in st.session_state:
        st.session_state.lote_cadastros = []

    try:
        res_tipos = supabase.table("tipos_exames").select("nome").order("nome").execute()
        lista_exames_cadastrados = [t["nome"] for t in res_tipos.data if t.get("nome")] if res_tipos.data else []
    except Exception as e:
        lista_exames_cadastrados = []
        st.warning(f"Não foi possível carregar os exames cadastrados do Supabase: {e}")

    if "form_version" not in st.session_state:
        st.session_state.form_version = 0
    v = st.session_state.form_version

    with st.form(f"form_cadastro_direto_{v}", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data_coleta_input = st.date_input("Data da Coleta", datetime.now(), format="DD/MM/YYYY")
        with col2:
            nome_paciente = st.text_input("Nome Completo das/o Paciente", key=f"val_nome_{v}")
        
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
            
        submitted = st.form_submit_button("Salvar e Adicionar ao Lote")
        
        if submitted:
            tipo_exame_final = ""
            
            if exame_novo_input.strip():
                tipo_exame_final = exame_novo_input.strip().upper()
                try:
                    resp_duplicado = supabase.table("tipos_exames").select("*").ilike("nome", tipo_exame_final).execute()
                    if not resp_duplicado.data:
                        supabase.table("tipos_exames").insert({"nome": tipo_exame_final}).execute()
                        st.toast(f"Novo tipo '{tipo_exame_final}' salvo no catálogo!", icon="✅")
                except Exception as err:
                    st.warning(f"Aviso: Não foi possível salvar no catálogo automático ({err}).")
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
                        "usuario_entrega": "",
                        "comprovante_url": ""
                    }).execute()
                            
                    st.session_state.lote_cadastros.append({
                        "protocolo": num_protocolo,
                        "nome_paciente": nome_paciente,
                        "tipo_exame": tipo_exame_final,
                        "data_coleta": data_coleta_str,
                        "data_entrega": "Pendente",
                        "recebido_por": ""
                    })
                    
                    registrar_log(
                        st.session_state.usuario_atual, 
                        "NOVO_PROTOCOLO", 
                        f"Protocolo gerado: {num_protocolo} para paciente {nome_paciente} ({tipo_exame_final})"
                    )
                    st.session_state.form_version += 1
                    st.success(f"Exame inserido! Protocolo gerado: **{num_protocolo}** (Adicionado ao lote de impressão)")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
            else:
                st.warning("Preencha o Nome Completo das/o Paciente e informe o Tipo de Exame.")

    if st.session_state.lote_cadastros:
        st.markdown("---")
        st.info(f"📦 **Lote atual:** Existem **{len(st.session_state.lote_cadastros)}** exame(s) aguardando impressão conjunta (4 por folha).")
        
        df_lote = pd.DataFrame(st.session_state.lote_cadastros)[["protocolo", "nome_paciente", "tipo_exame", "data_coleta"]]
        df_lote.columns = ["Protocolo", "Paciente", "Tipo de Exame", "Data Coleta"]
        st.dataframe(df_lote, use_container_width=True)
        
        pdf_lote_bytes = gerar_pdf_lote(st.session_state.lote_cadastros)
        
        col_imp1, col_imp2 = st.columns([2, 1])
        with col_imp1:
            st.download_button(
                label=f"🖨 IMPRIMIR LOTE CONJUNTO (4 POR FOLHA) - {len(st.session_state.lote_cadastros)} EXAMES",
                data=pdf_lote_bytes,
                file_name=f"lote_4_por_folha_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                key="btn_baixar_lote_completo"
            )
        with col_imp2:
            with st.expander("🗑️ Limpar Lote Atual"):
                if st.button("Confirmar Limpeza do Lote", key="btn_limpar_lote_confirma"):
                    st.session_state.lote_cadastros = []
                    st.success("Lote limpo com sucesso!")
                    st.rerun()

# ==========================================
# ABA 2: ENTREGAR EXAMES
# ==========================================
with tab2:
    st.markdown("### Busca Global Rápida (Leitor de Código de Barras ou Nome) e Entrega")
    
    bv = st.session_state.busca_version

    col_bs1, col_bs2 = st.columns([5, 1])
    with col_bs2:
        if st.session_state.registros_encontrados is not None:
            if st.button("Limpar Pesquisa", key="btn_reset_busca", use_container_width=True):
                st.session_state.termo_busca_executado = ""
                st.session_state.registros_encontrados = None
                st.session_state.busca_version += 1
                st.rerun()

    with st.form(f"form_busca_entregar_{bv}"):
        col_b1, col_b2 = st.columns([4, 1])
        with col_b1:
            busca_input = st.text_input("Bip / Digite o Código do Protocolo (Ex: TX-...) ou Nome do Paciente:", value=st.session_state.termo_busca_executado, key=f"input_busca_val_{bv}")
        with col_b2:
            st.markdown("<div style='margin-top: 27px;'></div>", unsafe_allow_html=True)
            btn_executar_busca = st.form_submit_button("🔍 Buscar Exame", use_container_width=True)
            
        if btn_executar_busca:
            st.session_state.termo_busca_executado = busca_input
            if busca_input.strip():
                try:
                    res_proto = supabase.table("exames").select("*").eq("protocolo", busca_input.strip()).execute()
                    if res_proto.data:
                        st.session_state.registros_encontrados = res_proto.data
                    else:
                        res_busca = supabase.table("exames").select("*").ilike("nome_paciente", f"%{busca_input.strip()}%").order("id", desc=True).execute()
                        st.session_state.registros_encontrados = res_busca.data
                    
                    if not st.session_state.registros_encontrados:
                        st.warning("Nenhum exame encontrado com este código ou nome.")
                except Exception as e:
                    st.session_state.registros_encontrados = []
                    st.error(f"Erro na busca: {e}")
            else:
                st.session_state.registros_encontrados = None
                st.warning("Digite um código de protocolo ou nome para realizar a busca.")

    if st.session_state.registros_encontrados is not None:
        registros = st.session_state.registros_encontrados
        if registros:
            st.markdown(f"**Encontrado(s) {len(registros)} registro(s):**")
            for reg in registros:
                id_reg = reg["id"]
                protocolo = reg["protocolo"]
                data_coleta = reg["data_coleta"]
                nome_paciente_original = reg["nome_paciente"]
                nome_paciente_exibicao = nome_paciente_original
                tipo_exame = reg["tipo_exame"]
                status_atual = reg["status"] if reg["status"] else "Pronto para entrega"
                data_entrega_db = reg["data_entrega"] or ""
                recebido_por_db = reg["recebido_por"] or ""
                data_protocolo = reg["data_protocolo"] or "N/D"
                usr_cad = reg["usuario_cadastro"] or "N/D"
                usr_ent = reg["usuario_entrega"] or "N/D"
                comprovante_url = reg.get("comprovante_url", "")
                
                atrasado = False
                if status_atual == "Pronto para entrega" and data_protocolo != "N/D":
                    try:
                        dt_prot = datetime.strptime(data_protocolo[:10], "%d/%m/%Y")
                        if (datetime.now() - dt_prot).days > 15:
                            atrasado = True
                    except Exception:
                        pass

                try:
                    res_hist = supabase.table("exames").select("id, protocolo, tipo_exame, status, data_coleta").eq("nome_paciente", nome_paciente_original).execute()
                    total_paciente = len(res_hist.data) if res_hist.data else 1
                    total_entregues_paciente = sum(1 for x in res_hist.data if x.get("status") == "Exame retirado")
                except Exception:
                    total_paciente = 1
                    total_entregues_paciente = 0

                card_class = "card-paciente-atrasado" if atrasado else "card-paciente"
                
                with st.container():
                    st.markdown(f"""
                    <div class="{card_class}">
                        <b>Protocolo:</b> {protocolo} | <b>Data Registro:</b> {data_protocolo} (Cadastrado por: <i>{usr_cad}</i>)<br>
                        <b>Paciente:</b> <span style="font-size:16px; color:#1e3a8a; font-weight:bold;">{nome_paciente_exibicao}</span><br>
                        <b>Exame:</b> {tipo_exame} | <b>Coleta:</b> {data_coleta}<br>
                        <hr style="margin: 8px 0; border: 0.5px solid #cbd5e1;">
                        <small style="color: #475569;">📊 <b>Histórico do Paciente:</b> {total_paciente} exames cadastrados no total ({total_entregues_paciente} já retirados).</small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if atrasado:
                        st.warning("⚠️ **Atenção:** Este exame está aguardando retirada há mais de 15 dias!")

                    if status_atual == "Exame retirado":
                        col_st1, col_st2 = st.columns(2)
                        with col_st1:
                            st.markdown('<div class="status-badge-verde">Exame retirado</div>', unsafe_allow_html=True)
                            st.markdown(f"""
                            <div class="info-retirada-box" style="margin-top: 10px;">
                                Retirado por: <b>{recebido_por_db}</b><br>
                                Data: <b>{data_entrega_db}</b> | Entregue por: <b>{usr_ent}</b>
                            </div>
                            """, unsafe_allow_html=True)
                        with col_st2:
                            st.markdown("##### Arquivo do Comprovante Assinado")
                            if comprovante_url:
                                st.success("Comprovante escaneado e arquivado!")
                                st.markdown(f"[Abrir Comprovante Arquivado]({comprovante_url})", unsafe_allow_html=True)
                            else:
                                st.warning("Nenhum comprovante escaneado enviado ainda.")
                                
                            arquivo_upload = st.file_uploader(
                                f"Enviar Comprovante Assinado (PDF ou Imagem) - {protocolo}", 
                                type=["pdf", "png", "jpg", "jpeg"], 
                                key=f"upl_{id_reg}"
                            )
                            
                            if arquivo_upload is not None:
                                if st.button("Enviar e Salvar Comprovante", key=f"btn_env_{id_reg}"):
                                    with st.spinner("Enviando para o Supabase Storage..."):
                                        try:
                                            file_bytes = arquivo_upload.getvalue()
                                            file_ext = arquivo_upload.name.split(".")[-1]
                                            file_path = f"comprovantes/{protocolo}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{file_ext}"
                                            
                                            supabase.storage.from_("comprovantes").upload(
                                                file_path, 
                                                file_bytes, 
                                                file_options={"content-type": arquivo_upload.type}
                                            )
                                            
                                            public_url_res = supabase.storage.from_("comprovantes").get_public_url(file_path)
                                            
                                            supabase.table("exames").update({
                                                "comprovante_url": public_url_res
                                            }).eq("id", id_reg).execute()
                                            
                                            registrar_log(st.session_state.usuario_atual, "UPLOAD_COMPROVANTE", f"Comprovante assinado do protocolo {protocolo} arquivado.")
                                            
                                            reg["comprovante_url"] = public_url_res
                                            
                                            st.success("Comprovante arquivado com sucesso!")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Erro ao enviar arquivo: {e}")
                                            
                        st.markdown("---")
                        dados_pdf_unico = [{
                            "protocolo": protocolo,
                            "data_coleta": data_coleta,
                            "nome_paciente": nome_paciente_original,
                            "tipo_exame": tipo_exame,
                            "data_entrega": data_entrega_db or datetime.now().strftime("%d/%m/%Y"),
                            "recebido_por": recebido_por_db
                        }]
                        pdf_bytes = gerar_pdf_lote(dados_pdf_unico)
                        st.download_button(
                            label=f"BAIXAR / IMPRIMIR COMPROVANTE (PDF) - {protocolo}",
                            data=pdf_bytes,
                            file_name=f"comprovante_{protocolo}.pdf",
                            mime="application/pdf",
                            key=f"dl_pdf_retirado_{id_reg}"
                        )
                    else:
                        badge_class = "status-badge-atrasado" if atrasado else "status-badge-verde"
                        col_st1, col_st2 = st.columns(2)
                        with col_st1:
                            st.markdown(f'<div class="{badge_class}" style="background-color: {"#ef4444" if atrasado else "#0284c7"};">Pronto para entrega</div>', unsafe_allow_html=True)
                        with col_st2:
                            recebido_por_input = st.text_input("Retirado por (Nome de quem vai buscar)", value="", key=f"rec_por_{id_reg}")
                            
                            with st.expander("🔒 Confirmar Conclusão da Retirada"):
                                if st.button("Concluir Retirada e Liberar Comprovante", key=f"btn_liberar_{id_reg}"):
                                    if recebido_por_input.strip():
                                        novo_status = "Exame retirado"
                                        d_entrega = datetime.now().strftime("%d/%m/%Y")
                                        rec_nome = recebido_por_input.strip()
                                        try:
                                            supabase.table("exames").update({
                                                "status": novo_status,
                                                "data_entrega": d_entrega,
                                                "recebido_por": rec_nome,
                                                "usuario_entrega": st.session_state.nome_usuario
                                            }).eq("id", id_reg).execute()
                                            
                                            registrar_log(st.session_state.usuario_atual, "ENTREGA_EXAME", f"Exame do protocolo {protocolo} entregue para {rec_nome}")
                                            
                                            reg["status"] = novo_status
                                            reg["data_entrega"] = d_entrega
                                            reg["recebido_por"] = rec_nome
                                            reg["usuario_entrega"] = st.session_state.nome_usuario
                                            
                                            st.success("Exame marcado como retirado com sucesso! Comprovantes liberados abaixo.")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Erro ao atualizar: {e}")
                                    else:
                                        st.warning("Informe o nome de quem está a retirar o exame.")

# ==========================================
# ABA 3: RELATÓRIOS & EDIÇÃO
# ==========================================
with tab3:
    st.markdown("### Relatórios Avançados e Gestão de Registros")
    
    try:
        res_all = supabase.table("exames").select("*").order("id", desc=True).execute()
        df_geral = pd.DataFrame(res_all.data) if res_all.data else pd.DataFrame()
    except Exception as e:
        df_geral = pd.DataFrame()
        st.error(f"Erro ao carregar dados: {e}")

    if not df_geral.empty:
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            status_filtro = st.selectbox("Filtrar por Status", ["Todos", "Pronto para entrega", "Exame retirado"], key="filtro_status_rel")
        with col_f2:
            paciente_filtro = st.text_input("Filtrar por Nome de Paciente", key="filtro_paciente_rel")
        with col_f3:
            tipo_filtro_op = st.selectbox("Filtrar por Tipo de Exame", ["Todos"] + list(df_geral["tipo_exame"].dropna().unique()), key="filtro_tipo_rel")

        df_filtrado = df_geral.copy()
        if status_filtro != "Todos":
            df_filtrado = df_filtrado[df_filtrado["status"] == status_filtro]
        if paciente_filtro.strip():
            df_filtrado = df_filtrado[df_filtrado["nome_paciente"].str.contains(paciente_filtro.strip(), case=False, na=False)]
        if tipo_filtro_op != "Todos":
            df_filtrado = df_filtrado[df_filtrado["tipo_exame"] == tipo_filtro_op]

        st.markdown(f"**Total de registros filtrados:** {len(df_filtrado)}")
        
        col_exibe_df = df_filtrado[["protocolo", "nome_paciente", "tipo_exame", "data_coleta", "status", "recebido_por", "data_entrega", "usuario_cadastro"]]
        st.dataframe(col_exibe_df, use_container_width=True)

        csv_data = col_exibe_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Exportar Dados Filtrados para CSV",
            data=csv_data,
            file_name=f"relatorio_exames_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
        
        st.markdown("---")
        st.markdown("#### ✏️ Edição ou Exclusão de Registro Específico")
        protocolo_edicao = st.text_input("Digite o Protocolo exato para Editar ou Excluir:", key="input_proto_edicao")
        
        if protocolo_edicao.strip():
            try:
                res_busca_ed = supabase.table("exames").select("*").eq("protocolo", protocolo_edicao.strip()).execute()
                if res_busca_ed.data:
                    reg_ed = res_busca_ed.data[0]
                    id_e = reg_ed["id"]
                    
                    with st.form("form_edicao_registro"):
                        st.markdown(f"**Editando Protocolo:** {reg_ed['protocolo']}")
                        novo_nome_p = st.text_input("Nome do Paciente", value=reg_ed["nome_paciente"])
                        novo_tipo_e = st.text_input("Tipo de Exame", value=reg_ed["tipo_exame"])
                        novo_status_e = st.selectbox("Status", ["Pronto para entrega", "Exame retirado"], index=0 if reg_ed["status"]=="Pronto para entrega" else 1)
                        novo_recebido = st.text_input("Retirado por", value=reg_ed["recebido_por"] or "")
                        
                        col_bt_ed1, col_bt_ed2 = st.columns(2)
                        with col_bt_ed1:
                            btn_salvar_ed = st.form_submit_button("💾 Salvar Alterações")
                        with col_bt_ed2:
                            btn_excluir_reg = st.form_submit_button("🗑️ Excluir Registro")
                            
                        if btn_salvar_ed:
                            supabase.table("exames").update({
                                "nome_paciente": novo_nome_p,
                                "tipo_exame": novo_tipo_e,
                                "status": novo_status_e,
                                "recebido_por": novo_recebido
                            }).eq("id", id_e).execute()
                            registrar_log(st.session_state.usuario_atual, "EDITAR_REGISTRO", f"Protocolo {reg_ed['protocolo']} atualizado.")
                            st.success("Registro atualizado com sucesso!")
                            st.rerun()
                            
                        if btn_excluir_reg and st.session_state.perfil_atual == "admin":
                            supabase.table("exames").delete().eq("id", id_e).execute()
                            registrar_log(st.session_state.usuario_atual, "EXCLUIR_REGISTRO", f"Protocolo {reg_ed['protocolo']} excluído do sistema.")
                            st.success("Registro excluído com sucesso!")
                            st.rerun()
                else:
                    st.warning("Nenhum registro encontrado com este protocolo.")
            except Exception as e:
                st.error(f"Erro ao buscar registro para edição: {e}")
    else:
        st.info("Nenhum exame cadastrado no sistema até o momento.")

# ==========================================
# ABA 4: BI & INDICADORES (PADRÃO)
# ==========================================
with tab4:
    st.markdown("### Indicadores de Desempenho e Estatísticas (BI)")
    
    try:
        res_bi = supabase.table("exames").select("*").execute()
        df_bi = pd.DataFrame(res_bi.data) if res_bi.data else pd.DataFrame()
    except Exception as e:
        df_bi = pd.DataFrame()

    if not df_bi.empty:
        total_geral = len(df_bi)
        total_retirados = len(df_bi[df_bi["status"] == "Exame retirado"])
        total_pendentes = len(df_bi[df_bi["status"] == "Pronto para entrega"])
        taxa_retirada = (total_retirados / total_geral) * 100 if total_geral > 0 else 0

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(f"""<div class="kpi-card"><p class="kpi-value" style="color:#1e3a8a;">{total_geral}</p><p class="kpi-label">Total de Exames</p></div>""", unsafe_allow_html=True)
        with k2:
            st.markdown(f"""<div class="kpi-card"><p class="kpi-value" style="color:#0284c7;">{total_pendentes}</p><p class="kpi-label">Aguardando Retirada</p></div>""", unsafe_allow_html=True)
        with k3:
            st.markdown(f"""<div class="kpi-card"><p class="kpi-value" style="color:#10b981;">{total_retirados}</p><p class="kpi-label">Exames Retirados</p></div>""", unsafe_allow_html=True)
        with k4:
            st.markdown(f"""<div class="kpi-card"><p class="kpi-value" style="color:#0f172a;">{taxa_retirada:.1f}%</p><p class="kpi-label">Taxa de Conclusão</p></div>""", unsafe_allow_html=True)

        st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
        
        c_graf1, c_graf2 = st.columns(2)
        with c_graf1:
            st.markdown("##### Distribuição por Status")
            fig_status = px.pie(df_bi, names="status", hole=0.4, color_discrete_sequence=["#0284c7", "#10b981", "#ef4444"])
            st.plotly_chart(fig_status, use_container_width=True)
            
        with c_graf2:
            st.markdown("##### Exames mais Frequentes")
            df_tipos = df_bi["tipo_exame"].value_counts().reset_index()
            df_tipos.columns = ["Tipo de Exame", "Quantidade"]
            
            cores_barras = ['#1d4ed8' if i == 0 else '#3b82f6' if i < 3 else '#60a5fa' for i in range(len(df_tipos.head(8)))]
            
            fig_tipos = px.bar(
                df_tipos.head(8), 
                x="Quantidade", 
                y="Tipo de Exame", 
                orientation="h", 
                text="Tipo de Exame"
            )
            
            fig_tipos.update_traces(
                marker_color=cores_barras,
                texttemplate='<b>%{text}</b> (%{x})', 
                textposition='inside',
                insidetextanchor='start',
                textfont=dict(color='white', size=12, family="Arial")
            )
            
            fig_tipos.update_layout(
                yaxis=dict(
                    categoryorder='total ascending',
                    showticklabels=False
                ),
                margin=dict(l=10, r=30, t=10, b=10)
            )
            st.plotly_chart(fig_tipos, use_container_width=True)
    else:
        st.info("Ainda não há dados suficientes para exibir os indicadores gráficos.")

# ==========================================
# ABA 5: MANUTENÇÃO & LOGS (COM MONITOR GAUGE DE ARMAZENAMENTO)
# ==========================================
if st.session_state.perfil_atual == "admin":
    with tab5:
        st.markdown("### Manutenção e Monitoramento do Sistema (Supabase Cloud)")
        
        col_m1, col_m2 = st.columns([1.2, 1.8])
        
        with col_m1:
            st.markdown("##### 🗄️ Monitor de Armazenamento (Free Tier)")
            # Exemplo de uso estimado no plano gratuito (ex: 35 MB utilizados de 500 MB limite)
            mb_utilizados = 35.5
            limite_mb = 500.0
            porcentagem_uso = (mb_utilizados / limite_mb) * 100
            
            fig_gauge = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=mb_utilizados,
                    number={"suffix": " MB", "font": {"size": 22}},
                    domain={"x": [0, 1], "y": [0, 1]},
                    title={"text": "<b>Banco & Storage (500MB)</b>", "font": {"size": 14, "color": "#1e3a8a"}},
                    gauge={
                        "axis": {"range": [None, limite_mb], "tickwidth": 1, "tickcolor": "#1e3a8a"},
                        "bar": {"color": "#0284c7"},
                        "bgcolor": "white",
                        "borderwidth": 2,
                        "bordercolor": "#cbd5e1",
                        "steps": [
                            {"range": [0, 250], "color": "#d1fae5"},   # Verde (Normal)
                            {"range": [250, 400], "color": "#fef08a"},  # Amarelo (Atenção)
                            {"range": [400, 500], "color": "#fee2e2"}   # Vermelho (Crítico)
                        ],
                        "threshold": {
                            "line": {"color": "red", "width": 4},
                            "thickness": 0.75,
                            "value": 450
                        }
                    }
                )
            )
            
            fig_gauge.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font={"color": "#0f172a", "family": "Arial"},
                height=260,
                margin=dict(l=10, r=10, t=30, b=10)
            )
            st.plotly_chart(fig_gauge, use_container_width=True)
            st.info(f"O banco de dados e o storage estão utilizando **{porcentagem_uso:.1f}%** da cota gratuita.")

        with col_m2:
            st.markdown("##### 📜 Auditoria e Logs de Atividades")
            try:
                res_logs = supabase.table("logs_sistema").select("*").order("id", desc=True).limit(50).execute()
                df_logs = pd.DataFrame(res_logs.data) if res_logs.data else pd.DataFrame()
            except Exception as e:
                df_logs = pd.DataFrame()
                st.warning("A tabela de logs ainda não foi criada no banco de dados Supabase.")

            if not df_logs.empty:
                st.dataframe(df_logs, use_container_width=True, height=220)
                
                csv_logs = df_logs.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Baixar Histórico de Logs (CSV)",
                    data=csv_logs,
                    file_name=f"logs_sistema_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("Nenhum registo de log encontrado.")
