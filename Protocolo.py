import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="Gestão de Demandas de Saúde",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicialização Oficial do Supabase
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"].rstrip("/")
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# Funções CRUD utilizando diretamente a tabela do Supabase
def carregar_demandas():
    try:
        response = supabase.table("pacientes_demandas").select("*").order("id", desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        return []

def salvar_demandas(nome, telefone, cartao_sus, demanda, reportado):
    try:
        # Define o status automaticamente com base no campo 'reportado'
        status_inicial = "Delegado" if reportado and reportado.strip() != "" else "Em Aberto"
        
        dados = {
            "nome": nome,
            "telefone": telefone,
            "cartao_sus": cartao_sus,
            "demanda": demanda,
            "reportado": reportado,
            "status": status_inicial
        }
        response = supabase.table("pacientes_demandas").insert(dados).execute()
        return response
    except Exception as e:
        raise Exception(f"Erro ao guardar na base de dados: {e}")

def atualizar_status(demanda_id, novo_status):
    try:
        atualizacao = {"status": novo_status}
        if novo_status == "Encerrado":
            atualizacao["data_resolucao"] = datetime.now().isoformat()
            
        supabase.table("pacientes_demandas").update(atualizacao).eq("id", demanda_id).execute()
    except Exception as e:
        st.error(f"Erro ao atualizar status: {e}")

# Interface Principal
st.title("🩺 Gestão de Atendimentos - Secretaria de Saúde")
st.markdown("---")

# Barra Lateral para Registo de Nova Demanda
st.sidebar.header("📝 Novo Atendimento")

with st.sidebar.form("form_demanda", clear_on_submit=True):
    nome = st.text_input("Nome do Paciente *")
    telefone = st.text_input("Telefone / WhatsApp (ex: 912345678)")
    cartao_sus = st.text_input("Cartão SUS")
    demanda = st.text_area("Descrição da Demanda / Caso *")
    reportado = st.text_input("Reportado por / Origem (Se preenchido, status vira 'Delegado')")
    
    submitted = st.form_submit_button("Registar Demanda", use_container_width=True)
    
    if submitted:
        if nome and demanda:
            try:
                salvar_demandas(nome, telefone, cartao_sus, demanda, reportado)
                st.sidebar.success("Demanda registada com sucesso!")
                st.rerun()
            except Exception as ex:
                st.sidebar.error(f"Erro ao guardar: {ex}")
        else:
            st.sidebar.error("Preencha os campos obrigatórios (Nome e Demanda).")

# Carregar Dados e Apresentar no Painel
try:
    dados_demandas = carregar_demandas()
    
    if not dados_demandas:
        st.info("Ainda não existem demandas registadas. Utilize o menu lateral para criar o primeiro atendimento.")
    else:
        df = pd.DataFrame(dados_demandas)
        
        # --- Secção de Métricas (KPIs) ---
        total_atendimentos = len(df)
        em_aberto = len(df[df["status"] == "Em Aberto"]) if "status" in df.columns else 0
        delegados = len(df[df["status"] == "Delegado"]) if "status" in df.columns else 0
        encerrados = len(df[df["status"] == "Encerrado"]) if "status" in df.columns else 0
        
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Total de Atendimentos", total_atendimentos)
        kpi2.metric("Em Aberto", em_aberto)
        kpi3.metric("Delegados", delegados)
        kpi4.metric("Encerrados", encerrados)
        
        st.markdown("---")
        
        # --- Filtros e Controlo ---
        st.subheader("🔍 Filtros e Pesquisa")
        col_f1, col_f2 = st.columns(2)
        
        with col_f1:
            filtro_status = st.selectbox("Filtrar por Status", ["Todos", "Em Aberto", "Delegado", "Encerrado"])
        
        with col_f2:
            busca_nome = st.text_input("Pesquisar por Nome ou Cartão SUS", placeholder="Digite o nome ou cartão...")
            
        df_filtrado = df.copy()
        if filtro_status != "Todos" and "status" in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado["status"] == filtro_status]
            
        if busca_nome and "nome" in df_filtrado.columns:
            df_filtrado = df_filtrado[
                df_filtrado["nome"].str.contains(busca_nome, case=False, na=False) | 
                df_filtrado["cartao_sus"].str.contains(busca_nome, case=False, na=False)
            ]

        st.markdown("---")
        st.subheader(f"📋 Lista de Atendimentos ({len(df_filtrado)})")
        
        for index, row in df_filtrado.iterrows():
            status_atual = row.get('status', 'Em Aberto')
            
            emoji_status = "🟡" if status_atual == "Em Aberto" else ("🔵" if status_atual == "Delegado" else "🟢")
            
            with st.expander(f"{emoji_status} **{row.get('nome', 'Sem Nome')}** — Status: **{status_atual}**"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**📞 Telefone:** {row.get('telefone', 'Não informado')}")
                    st.markdown(f"**🆔 Cartão SUS:** {row.get('cartao_sus', 'Não informado')}")
                    st.markdown(f"**📝 Demanda:** {row.get('demanda', 'N/A')}")
                    st.markdown(f"**👤 Reportado por / Origem:** {row.get('reportado', 'N/A')}")
                    
                    tel = row.get('telefone')
                    if tel:
                        tel_limpo = "".join(filter(str.isdigit, str(tel)))
                        st.markdown(f"[💬 Enviar Mensagem WhatsApp](https://wa.me/55{tel_limpo})", unsafe_allow_html=True)

                with col2:
                    opcoes_status = ["Em Aberto", "Delegado", "Encerrado"]
                    idx_atual = opcoes_status.index(status_atual) if status_atual in opcoes_status else 0
                    
                    novo_estado = st.selectbox(
                        "Atualizar Status", 
                        opcoes_status, 
                        index=idx_atual,
                        key=f"status_{row.get('id', index)}"
                    )
                    
                    if novo_estado != status_atual:
                        atualizar_status(row['id'], novo_estado)
                        st.success("Estado atualizado com sucesso!")
                        st.rerun()

except Exception as e:
    st.error(f"Erro ao carregar os dados: {e}")
