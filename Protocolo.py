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
            st.markdown("### Identificação do Utilizador")
            user_input = st.text_input("Utilizador")
            senha_input = st.text_input("Palavra-passe", type="password")
            
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
                    registrar_log("Tiago", "LOGIN", "Utilizador acedeu ao sistema com credenciais definitivas")
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                elif u_limpo == "admin" and s_limpa == "123":
                    st.session_state.autenticado = True
                    st.session_state.usuario_atual = "admin"
                    st.session_state.nome_usuario = "Administrador do Sistema"
                    st.session_state.perfil_atual = "admin"
                    registrar_log("admin", "LOGIN", "Utilizador acedeu ao sistema com credenciais definitivas")
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                elif u_limpo == "lilian" and s_limpa == "123456":
                    st.session_state.autenticado = True
                    st.session_state.usuario_atual = "Lilian"
                    st.session_state.nome_usuario = "Lilian"
                    st.session_state.perfil_atual = "atendente"
                    registrar_log("Lilian", "LOGIN", "Utilizador acedeu ao sistema com credenciais definitivas")
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("Utilizador ou palavra-passe incorretos.")
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
            pdf.cell(138, 5, " PROTOCOLO: " + str(dados['protocolo']), border=1, fill=True, ln=1)
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
            pdf.multi_cell(138, 3, "Declaro que recebi os resultados dos exames descritos acima, conferindo a integridade e ciente das orientacoes.", align="C")
            pdf.ln(2)
            
            pdf.set_x(x_pos)
            pdf.set_font("Arial", "", 7.5)
            pdf.cell(69, 4, "_" * 32, align="C")
            pdf.cell(69, 4, "_" * 32, align="C", ln=1)
            pdf.set_x(x_pos)
            pdf.cell(69, 4, "Assinatura do Paciente / Responsavel", align="C")
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
            <p class="header-subtitle">Sistema de Controlo de Protocolos, Coletas e Entrega de Exames</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_h2:
    icone_perfil = "👑" if st.session_state.perfil_atual == "admin" else "👨‍💼"
    st.markdown(
        '<div class="header-box-unica" style="flex-direction: column; align-items: flex-end; text-align: right; margin-bottom: 0px; padding: 14px 20px;">'
        '<p class="header-user-info">' + icone_perfil + ' <b>' + str(st.session_state.nome_usuario) + '</b> (' + str(st.session_state.perfil_atual).upper() + ')</p>'
        '</div>',
        unsafe_allow_html=True
    )
    
    col_vazia_btn, col_b_sair = st.columns([1.3, 1.2])
    with col_b_sair:
        if st.button("Sair do Sistema", key="btn_sair_sistema", use_container_width=True):
            registrar_log(st.session_state.usuario_atual, "LOGOUT", "Utilizador desligou-se")
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
        "⚙ Manutenção & Logs"
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
    try:
        st.markdown("### Registar Novo Exame Coletado")
        
        if "lote_cadastros" not in st.session_state:
            st.session_state.lote_cadastros = []

        lista_exames_cadastrados = []
        try:
            res_tipos = supabase.table("tipos_exames").select("nome").order("nome").execute()
            if res_tipos.data:
                lista_exames_cadastrados = [t["nome"] for t in res_tipos.data if t.get("nome")]
        except Exception:
            pass

        if "form_version" not in st.session_state:
            st.session_state.form_version = 0
        v = st.session_state.form_version

        with st.form("form_cadastro_direto_" + str(v), clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                data_coleta_input = st.date_input("Data da Coleta", datetime.now(), format="DD/MM/YYYY")
            with col2:
                nome_paciente = st.text_input("Nome Completo do/a Paciente", key="val_nome_" + str(v))
            
            st.markdown("---")
            st.markdown("##### Selecione o Exame Existente ou Digite um Novo Abaixo")
            
            col_ex1, col_ex2 = st.columns(2)
            with col_ex1:
                exame_selecionado = st.selectbox(
                    "Selecionar da Lista Cadastrada",
                    ["-- Selecione ou digite abaixo --"] + lista_exames_cadastrados,
                    key="sel_exame_" + str(v)
                )
            with col_ex2:
                exame_novo_input = st.text_input("Ou Digite um Novo Tipo de Exame", key="val_novo_tipo_" + str(v))
                
            submitted = st.form_submit_button("Salvar e Adicionar ao Lote")
            
            if submitted:
                tipo_exame_final = ""
                novo_digitado = exame_novo_input.strip() if exame_novo_input else ""
                
                if novo_digitado:
                    tipo_exame_final = novo_digitado
                elif exame_selecionado and exame_selecionado != "-- Selecione ou digite abaixo --":
                    tipo_exame_final = exame_selecionado
                    
                if nome_paciente.strip() and tipo_exame_final:
                    num_protocolo = "TX-" + datetime.now().strftime('%Y%m%d%H%M%S')
                    data_coleta_str = data_coleta_input.strftime("%d/%m/%Y")
                    data_protocolo_str = datetime.now().strftime("%d/%m/%Y %H:%M")
                    
                    try:
                        supabase.table("exames").insert({
                            "protocolo": num_protocolo,
                            "data_coleta": data_coleta_str,
                            "nome_paciente": nome_paciente.strip(),
                            "tipo_exame": tipo_exame_final,
                            "status": "Pronto para entrega",
                            "recebido_por": "",
                            "data_protocolo": data_protocolo_str,
                            "usuario_cadastro": st.session_state.nome_usuario,
                            "usuario_entrega": "",
                            "comprovante_url": ""
                        }).execute()
                        
                        if novo_digitado:
                            try:
                                existe_tipo = any(t.lower() == novo_digitado.lower() for t in lista_exames_cadastrados)
                                if not existe_tipo:
                                    supabase.table("tipos_exames").insert({"nome": novo_digitado}).execute()
                            except Exception:
                                pass
                                
                        st.session_state.lote_cadastros.append({
                            "protocolo": num_protocolo,
                            "nome_paciente": nome_paciente.strip(),
                            "tipo_exame": tipo_exame_final,
                            "data_coleta": data_coleta_str,
                            "data_entrega": "Pendente",
                            "recebido_por": ""
                        })
                        
                        registrar_log(
                            st.session_state.usuario_atual, 
                            "NOVO_PROTOCOLO", 
                            "Protocolo gerado: " + num_protocolo + " para paciente " + nome_paciente + " (" + tipo_exame_final + ")"
                        )
                        st.session_state.form_version += 1
                        st.success("Exame inserido! Protocolo gerado: **" + num_protocolo + "** (Adicionado ao lote de impressao)")
                        st.rerun()
                    except Exception as e:
                        st.error("Erro ao salvar no Supabase: " + str(e))
                else:
                    st.warning("Preencha o Nome Completo do Paciente e informe/selecione o Tipo de Exame.")

        if st.session_state.lote_cadastros:
            st.markdown("---")
            st.info("📦 **Lote atual:** Existem **" + str(len(st.session_state.lote_cadastros)) + "** exame(s) a aguardar impressao conjunta (4 por folha).")
            
            df_lote = pd.DataFrame(st.session_state.lote_cadastros)[["protocolo", "nome_paciente", "tipo_exame", "data_coleta"]]
            df_lote.columns = ["Protocolo", "Paciente", "Tipo de Exame", "Data Coleta"]
            st.dataframe(df_lote, use_container_width=True)
            
            pdf_lote_bytes = gerar_pdf_lote(st.session_state.lote_cadastros)
            
            col_imp1, col_imp2 = st.columns([2, 1])
            with col_imp1:
                st.download_button(
                    label="🖨 IMPRIMIR LOTE CONJUNTO (4 POR FOLHA) - " + str(len(st.session_state.lote_cadastros)) + " EXAMES",
                    data=pdf_lote_bytes,
                    file_name="lote_4_por_folha_" + datetime.now().strftime('%Y%m%d_%H%M') + ".pdf",
                    mime="application/pdf",
                    key="btn_baixar_lote_completo"
                )
            with col_imp2:
                with st.expander("🗑️ Limpar Lote Atual"):
                    if st.button("Confirmar Limpeza do Lote", key="btn_limpar_lote_confirma"):
                        st.session_state.lote_cadastros = []
                        st.success("Lote limpo com sucesso!")
                        st.rerun()
    except Exception as e:
        st.error("Erro ao carregar a aba de cadastro: " + str(e))

# ==========================================
# ABA 2: ENTREGAR EXAMES
# ==========================================
with tab2:
    try:
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

        with st.form("form_busca_entregar_" + str(bv)):
            col_b1, col_b2 = st.columns([4, 1])
            with col_b1:
                busca_input = st.text_input("Bip / Digite o Código do Protocolo (Ex: TX-...) ou Nome do Paciente:", value=st.session_state.termo_busca_executado, key="input_busca_val_" + str(bv))
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
                            res_busca = supabase.table("exames").select("*").ilike("nome_paciente", "%" + busca_input.strip() + "%").order("id", desc=True).execute()
                            st.session_state.registros_encontrados = res_busca.data
                        
                        if not st.session_state.registros_encontrados:
                            st.warning("Nenhum exame encontrado com este código ou nome.")
                    except Exception as e:
                        st.session_state.registros_encontrados = []
                        st.error("Erro na busca: " + str(e))
                else:
                    st.session_state.registros_encontrados = None
                    st.warning("Digite um código de protocolo ou nome para realizar a busca.")

        if st.session_state.registros_encontrados is not None:
            registros = st.session_state.registros_encontrados
            if registros:
                st.markdown("**Encontrado(s) " + str(len(registros)) + " registo(s):**")
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
                            if
