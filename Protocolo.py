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
# 3. GERAÇÃO DO PDF (2 COMPROVANTES POR FOLHA A5)
# ==========================================
class PDFProtocoloEmLote(FPDF):
    pass

def gerar_pdf_lote(lista_dados):
    pdf = PDFProtocoloEmLote(orientation="p", unit="mm", format="A5")
    pdf.set_auto_page_break(auto=False, margin=5)
    
    for i in range(0, len(lista_dados), 2):
        pdf.add_page()
        bloco_par = lista_dados[i:i+2]
        
        for idx, dados in enumerate(bloco_par):
            if idx > 0:
                pdf.ln(2)
                pdf.set_font("Arial", "I", 6.5)
                pdf.set_text_color(180, 180, 180)
                pdf.cell(0, 3, "-" * 85, ln=True, align="C")
                pdf.ln(2)

            pdf.set_font("Arial", "B", 7.5)
            pdf.set_text_color(30, 58, 138)
            pdf.cell(0, 3.5, "SEC. MUN. DE SAÚDE DE TEIXEIRAS", border=0, ln=True, align="C")
            pdf.ln(1)
            
            pdf.set_fill_color(30, 58, 138)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", "B", 7.5)
            pdf.cell(0, 4.5, f" PROTOCOLO: {dados['protocolo']}", border=1, fill=True, ln=True)
            pdf.set_text_color(0, 0, 0)
            
            campos = [
                ("Coleta:", dados["data_coleta"], "Retirada:", dados["data_entrega"]),
                ("Paciente:", dados["nome_paciente"], "Retirado por:", dados["recebido_por"]),
                ("Exames:", dados["tipo_exame"], "", "")
            ]
            
            for rot1, val1, rot2, val2 in campos:
                pdf.set_font("Arial", "B", 7)
                pdf.cell(18, 4.5, rot1, border=1)
                pdf.set_font("Arial", "", 7)
                pdf.cell(59, 4.5, str(val1), border=1)
                if rot2:
                    pdf.set_font("Arial", "B", 7)
                    pdf.cell(20, 4.5, rot2, border=1)
                    pdf.set_font("Arial", "", 7)
                    pdf.cell(31, 4.5, str(val2), border=1, ln=True)
                else:
                    pdf.ln(4.5)
                    
            pdf.ln(1.5)
            pdf.set_font("Arial", "I", 6)
            pdf.multi_cell(0, 3, "Declaro que recebi os resultados dos exames descritos acima, conferindo a integridade e ciente das orientações.")
            pdf.ln(3)
            
            pdf.set_font("Arial", "", 7)
            pdf.cell(64, 3.5, "_" * 28, align="C")
            pdf.cell(64, 3.5, "_" * 28, align="C", ln=True)
            pdf.cell(64, 3.5, "Assinatura do Paciente / Responsável", align="C")
            pdf.cell(64, 3.5, "Assinatura / Carimbo Atendente", align="C", ln=True)
            pdf.ln(2)
        
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

with tab1:
    st.markdown("### Registrar Novo Exame Coletado")
    
    if "lote_cadastros" not in st.session_state:
        st.session_state.lote_cadastros = []

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
            
        submitted = st.form_submit_button("Salvar e Adicionar ao Lote")
        
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
                        "usuario_entrega": "",
                        "comprovante_url": ""
                    }).execute()
                    
                    if exame_novo_input.strip():
                        try:
                            supabase.table("tipos_exames").insert({"nome": exame_novo_input.strip()}).execute()
                        except Exception:
                            pass
                            
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
                st.warning("Preencha o Nome Completo do Paciente e informe o Tipo de Exame.")

    if st.session_state.lote_cadastros:
        st.markdown("---")
        st.info(f"📦 **Lote atual:** Existem **{len(st.session_state.lote_cadastros)}** exame(s) aguardando impressão conjunta (2 por folha).")
        
        df_lote = pd.DataFrame(st.session_state.lote_cadastros)[["protocolo", "nome_paciente", "tipo_exame", "data_coleta"]]
        df_lote.columns = ["Protocolo", "Paciente", "Tipo de Exame", "Data Coleta"]
        st.dataframe(df_lote, use_container_width=True)
        
        pdf_lote_bytes = gerar_pdf_lote(st.session_state.lote_cadastros)
        
        col_imp1, col_imp2 = st.columns([2, 1])
        with col_imp1:
            st.download_button(
                label=f"🖨️ IMPRIMIR LOTE CONJUNTO (2 POR FOLHA) - {len(st.session_state.lote_cadastros)} EXAMES",
                data=pdf_lote_bytes,
                file_name=f"lote_2_por_folha_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                key="btn_baixar_lote_completo"
            )
        with col_imp2:
            with st.expander("🗑️ Limpar Lote Atual"):
                if st.button("Confirmar Limpeza do Lote", key="btn_limpar_lote_confirma"):
                    st.session_state.lote_cadastros = []
                    st.success("Lote limpo com sucesso!")
                    st.rerun()

with tab2:
    st.markdown("### Busca Global Rápida (Leitor de Código de Barras ou Nome) e Entrega")
    
    bv = st.session_state.busca_version

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
                        st.session_state.termo_busca_executado = ""
                        st.session_state.busca_version += 1
                except Exception as e:
                    st.session_state.registros_encontrados = []
                    st.session_state.termo_busca_executado = ""
                    st.session_state.busca_version += 1
                    st.error(f"Erro na busca: {e}")
            else:
                st.session_state.registros_encontrados = []
                st.session_state.termo_busca_executado = ""
                st.session_state.busca_version += 1
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
                                        try:
                                            supabase.table("exames").update({
                                                "status": novo_status,
                                                "data_entrega": d_entrega,
                                                "recebido_por": recebido_por_input.strip(),
                                                "usuario_entrega": st.session_state.nome_usuario
                                            }).eq("id", id_reg).execute()
                                            
                                            registrar_log(st.session_state.usuario_atual, "ENTREGA_EXAME", f"Exame do protocolo {protocolo} entregue para {recebido_por_input.strip()}")
                                            
                                            reg["status"] = novo_status
                                            reg["data_entrega"] = d_entrega
                                            reg["recebido_por"] = recebido_por_input.strip()
                                            reg["usuario_entrega"] = st.session_state.nome_usuario
                                            
                                            st.success("Exame concluído com sucesso!")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Erro ao atualizar: {e}")
                                    else:
                                        st.warning("Por favor, preencha o nome de quem está retirando o exame.")
                                        
                        if status_atual == "Exame retirado":
                            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                            dados_pdf_imediato = [{
                                "protocolo": protocolo,
                                "data_coleta": data_coleta,
                                "nome_paciente": nome_paciente_original,
                                "tipo_exame": tipo_exame,
                                "data_entrega": data_entrega_db or datetime.now().strftime("%d/%m/%Y"),
                                "recebido_por": recebido_por_db
                            }]
                            pdf_bytes_imediato = gerar_pdf_lote(dados_pdf_imediato)
                            st.download_button(
                                label=f"📥 BAIXAR COMPROVANTE DO EXAME CONCLUÍDO - {protocolo}",
                                data=pdf_bytes_imediato,
                                file_name=f"comprovante_{protocolo}.pdf",
                                mime="application/pdf",
                                key=f"dl_pdf_imediato_{id_reg}"
                            )

                    st.markdown("<hr style='margin: 20px 0; border: 1px solid #e2e8f0;'>", unsafe_allow_html=True)
        else:
            st.warning("Nenhum exame encontrado com este código ou nome.")
            st.session_state.registros_encontrados = None

with tab3:
    st.markdown("### Relatório Geral, Filtros e Edição Direta de Registros")
    
    rv = st.session_state.rel_version

    with st.form(f"form_filtro_relatorios_{rv}"):
        col_f1, col_f2, col_f3 = st.columns([3, 2, 1])
        with col_f1:
            filtro_nome = st.text_input("Filtrar por Nome do Paciente (Opcional)", value="", key=f"input_rel_nome_{rv}")
        with col_f2:
            filtro_status = st.selectbox("Filtrar por Status", ["Todos", "Pronto para entrega", "Exame retirado"])
        with col_f3:
            st.markdown("<div style='margin-top: 27px;'></div>", unsafe_allow_html=True)
            btn_filtrar_rel = st.form_submit_button("🔍 Filtrar Relatório", use_container_width=True)
            
        if btn_filtrar_rel:
            st.session_state.id_registro_em_edicao = None
            try:
                query = supabase.table("exames").select("*")
                if filtro_nome.strip():
                    query = query.ilike("nome_paciente", f"%{filtro_nome.strip()}%")
                if filtro_status != "Todos":
                    query = query.eq("status", filtro_status)
                
                res_rel = query.order("id", desc=True).execute()
                st.session_state.df_relatorio_filtrado = res_rel.data
                
                if not st.session_state.df_relatorio_filtrado:
                    st.session_state.rel_version += 1
            except Exception as e:
                st.session_state.df_relatorio_filtrado = []
                st.session_state.rel_version += 1
                st.error(f"Erro ao gerar relatório: {e}")

    if st.session_state.df_relatorio_filtrado is None:
        try:
            res_exames = supabase.table("exames").select("*").order("id", desc=True).execute()
            st.session_state.df_relatorio_filtrado = res_exames.data
        except Exception:
            st.session_state.df_relatorio_filtrado = []

    registros_rel = st.session_state.df_relatorio_filtrado

    if registros_rel:
        df_exibicao = pd.DataFrame(registros_rel)
            
        st.dataframe(df_exibicao, use_container_width=True)
        
        csv = df_exibicao.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Baixar Relatório Filtrado em CSV", csv, "relatorio_exames_teixeiras.csv", "csv")
        
        st.markdown("---")
        st.markdown("### ✏️ Ações de Edição nos Exames Listados Acima")
        st.markdown("Clique no botão **'✏️ Editar'** ao lado do registro que deseja corrigir:")

        for reg in registros_rel:
            r_id = reg["id"]
            r_prot = reg["protocolo"]
            r_pac = reg["nome_paciente"]
            r_ex = reg["tipo_exame"]
            r_col = reg["data_coleta"]
            r_status = reg["status"]

            col_info, col_btn = st.columns([5, 1])
            with col_info:
                st.markdown(f"**[{r_prot}]** - **{r_pac}** | Exame: *{r_ex}* | Coleta: {r_col} | Status: `{r_status}`")
            with col_btn:
                if st.button("✏️ Editar", key=f"btn_ativar_edicao_{r_id}"):
                    st.session_state.id_registro_em_edicao = r_id
                    st.rerun()

        if st.session_state.id_registro_em_edicao is not None:
            reg_alvo = next((r for r in registros_rel if r["id"] == st.session_state.id_registro_em_edicao), None)
            
            if reg_alvo:
                st.markdown("---")
                st.markdown(f"#### 📝 Editando Registro: `{reg_alvo['protocolo']}` (Paciente: **{reg_alvo['nome_paciente']}**)")
                
                try:
                    res_tipos_ed = supabase.table("tipos_exames").select("nome").order("nome").execute()
                    lista_exames_ed = [t["nome"] for t in res_tipos_ed.data] if res_tipos_ed.data else []
                except Exception:
                    lista_exames_ed = []

                with st.form("form_edicao_direta_tabela"):
                    novo_prot = st.text_input("Número do Protocolo", value=reg_alvo["protocolo"])
                    novo_nome = st.text_input("Nome do Paciente", value=reg_alvo["nome_paciente"])
                    nova_coleta = st.text_input("Data da Coleta", value=reg_alvo["data_coleta"])
                    
                    exame_atual_db = reg_alvo["tipo_exame"]
                    idx_exame = lista_exames_ed.index(exame_atual_db) if exame_atual_db in lista_exames_ed else 0
                    
                    novo_tipo = st.selectbox("Tipo de Exame", lista_exames_ed if lista_exames_ed else [exame_atual_db], index=idx_exame)
                    novo_status_reg = st.selectbox("Status", ["Pronto para entrega", "Exame retirado"], index=0 if reg_alvo["status"] == "Pronto para entrega" else 1)
                    
                    col_salv1, col_salv2 = st.columns(2)
                    with col_salv1:
                        btn_salvar_mudanca = st.form_submit_button("💾 Salvar Alterações", use_container_width=True)
                    with col_salv2:
                        btn_cancelar_mudanca = st.form_submit_button("❌ Cancelar Edição", use_container_width=True)
                        
                    if btn_salvar_mudanca:
                        try:
                            supabase.table("exames").update({
                                "protocolo": novo_prot.strip(),
                                "nome_paciente": novo_nome.strip(),
                                "data_coleta": nova_coleta.strip(),
                                "tipo_exame": novo_tipo,
                                "status": novo_status_reg
                            }).eq("id", reg_alvo["id"]).execute()
                            
                            registrar_log(
                                st.session_state.usuario_atual, 
                                "EDICAO_PROTOCOLO", 
                                f"Protocolo {reg_alvo['protocolo']} editado para: Paciente={novo_nome.strip()}, Exame={novo_tipo}"
                            )
                            st.session_state.id_registro_em_edicao = None
                            st.session_state.df_relatorio_filtrado = None
                            st.success("Alterações salvas com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")
                            
                    if btn_cancelar_mudanca:
                        st.session_state.id_registro_em_edicao = None
                        st.rerun()
    else:
        st.info("Nenhum registro encontrado com este filtro.")
        st.session_state.df_relatorio_filtrado = None

with (tab4 if st.session_state.perfil_atual == "admin" else tab4):
    st.markdown("### 📈 Painel de Business Intelligence e Indicadores de Saúde")
    st.markdown("Visão gerencial consolidada do fluxo de exames e desempenho da Secretaria Municipal.")

    try:
        res_kpi = supabase.table("exames").select("status, data_protocolo, nome_paciente").execute()
        total_regs = len(res_kpi.data) if res_kpi.data else 0
        total_prontos = sum(1 for x in res_kpi.data if x.get("status") == "Pronto para entrega")
        total_retirados = sum(1 for x in res_kpi.data if x.get("status") == "Exame retirado")
        
        taxa_conclusao = round((total_retirados / total_regs * 100), 1) if total_regs > 0 else 0.0
    except Exception:
        total_regs, total_prontos, total_retirados, taxa_conclusao = 0, 0, 0, 0.0

    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    with col_kpi1:
        st.markdown(f"""
        <div class="kpi-card">
            <p class="kpi-value" style="color: #10b981;">{total_regs}</p>
            <p class="kpi-label">Total de Exames Registrados</p>
        </div>
        """, unsafe_allow_html=True)
    with col_kpi2:
        st.markdown(f"""
        <div class="kpi-card">
            <p class="kpi-value" style="color: #ef4444;">{total_prontos}</p>
            <p class="kpi-label">Prontos para Retirada</p>
        </div>
        """, unsafe_allow_html=True)
    with col_kpi3:
        st.markdown(f"""
        <div class="kpi-card">
            <p class="kpi-value" style="color: #0284c7;">{total_retirados}</p>
            <p class="kpi-label">Exames Já Entregues</p>
        </div>
        """, unsafe_allow_html=True)
    with col_kpi4:
        st.markdown(f"""
        <div class="kpi-card">
            <p class="kpi-value" style="color: #6366f1;">{taxa_conclusao}%</p>
            <p class="kpi-label">Taxa de Conclusão (Entrega)</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)

    try:
        res_bi = supabase.table("exames").select("id, tipo_exame, status, data_coleta, usuario_cadastro, usuario_entrega").execute()
        dados_bi = res_bi.data if res_bi.data else []
    except Exception:
        dados_bi = []

    if dados_bi:
        df_bi = pd.DataFrame(dados_bi)

        col_bi1, col_bi2 = st.columns(2)
        
        with col_bi1:
            st.markdown("#### 🎯 Proporção do Fluxo de Status")
            status_counts = df_bi["status"].value_counts().reset_index()
            status_counts.columns = ["Status", "Quantidade"]
            
            fig_donut = px.pie(
                status_counts, 
                names="Status", 
                values="Quantidade", 
                hole=0.6,
                color="Status",
                color_discrete_map={
                    "Pronto para entrega": "#ef4444", 
                    "Exame retirado": "#0284c7"
                }
            )
            fig_donut.update_traces(
                textposition='inside', 
                textinfo='percent+label',
                marker=dict(line=dict(color='#ffffff', width=2))
            )
            fig_donut.update_layout(
                margin=dict(t=10, b=10, l=10, r=10),
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_donut, use_container_width=True)

        with col_bi2:
            st.markdown("#### 🧪 Top 5 Tipos de Exames Mais Solicitados")
            tipo_counts = df_bi["tipo_exame"].value_counts().head(5).reset_index()
            tipo_counts.columns = ["Tipo de Exame", "Quantidade"]
            tipo_counts = tipo_counts.sort_values(by="Quantidade", ascending=True)
            
            cores_exames = ["#0284c7", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899"]
            
            fig_bar = px.bar(
                tipo_counts, 
                x="Quantidade", 
                y="Tipo de Exame", 
                orientation="h",
                text="Quantidade",
                color="Tipo de Exame",
                color_discrete_sequence=cores_exames
            )
            fig_bar.update_traces(
                textfont_size=12,
                textangle=0,
                textposition="outside",
                cliponaxis=False
            )
            fig_bar.update_layout(
                margin=dict(t=10, b=10, l=10, r=30),
                showlegend=False,
                xaxis_title="Total de Solicitações",
                yaxis_title="",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=True, gridcolor="#e2e8f0")
            )
            st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Ainda não há dados suficientes para gerar os indicadores de BI.")

if st.session_state.perfil_atual == "admin":
    with tab5:
        st.markdown("### Gerenciamento de Usuários do Sistema")
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
            btn_salvar_novo_user = st.form_submit_button("Confirmar e Cadastrar Novo Usuário")
            
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
                        st.success(f"Usuário criado com sucesso! O login **{novo_user_log.strip()}** já está ativo no sistema.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro (verifique se o usuário já existe): {e}")
                else:
                    st.warning("Preencha todos os campos do novo usuário antes de confirmar.")
                    
        st.markdown("---")
        st.markdown("### Usuários Cadastrados no Sistema")
        try:
            res_users = supabase.table("usuarios").select("id, username, nome_completo, perfil").execute()
            df_usuarios = pd.DataFrame(res_users.data)
        except Exception:
            df_usuarios = pd.DataFrame()
        st.dataframe(df_usuarios, use_container_width=True)
        
        st.markdown("---")
        st.markdown("### Ferramentas de Auditoria e Logs (Com Filtro por Usuário/Ação)")
        
        if "df_logs_filtrados" not in st.session_state:
            st.session_state.df_logs_filtrados = None

        with st.form("form_filtro_logs"):
            col_l1, col_l2 = st.columns([3, 1])
            with col_l1:
                filtro_log_usuario = st.text_input("Filtrar logs por Usuário (Opcional)", value="")
            with col_l2:
                st.markdown("<div style='margin-top: 27px;'></div>", unsafe_allow_html=True)
                btn_buscar_logs = st.form_submit_button("🔍 Buscar Logs", use_container_width=True)
                
            if btn_buscar_logs:
                try:
                    q_log = supabase.table("logs_sistema").select("*")
                    if filtro_log_usuario.strip():
                        q_log = q_log.ilike("usuario", f"%{filtro_log_usuario.strip()}%")
                    res_l = q_log.order("id", desc=True).execute()
                    st.session_state.df_logs_filtrados = res_l.data
                except Exception as e:
                    st.session_state.df_logs_filtrados = []
                    st.error(f"Erro ao buscar logs: {e}")

        if st.session_state.df_logs_filtrados is None:
            try:
                res_logs = supabase.table("logs_sistema").select("*").order("id", desc=True).execute()
                st.session_state.df_logs_filtrados = res_logs.data
            except Exception:
                st.session_state.df_logs_filtrados = []

        df_logs = pd.DataFrame(st.session_state.df_logs_filtrados)
        st.dataframe(df_logs, use_container_width=True)
        
        if not df_logs.empty:
            csv_logs = df_logs.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Baixar Logs Filtrados (CSV)", csv_logs, "logs_auditoria_teixeiras.csv", "csv")
