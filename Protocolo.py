import streamlit as st
from supabase import create_client, Client

# Configuração da página do Streamlit
st.set_page_config(
    page_title="Gestão de Protocolos e Exames",
    page_icon="📋",
    layout="wide"
)

# Configuração de Conexão com o Supabase 
# (Substitua pelas suas chaves ou utilize st.secrets)
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "SUA_URL_AQUI")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "SUA_CHAVE_AQUI")

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# Cabeçalho Principal
st.title("📋 Sistema de Gestão de Protocolos")
st.markdown("---")

# Criação de Abas
tab1, tab2 = st.tabs(["Novo Protocolo", "Consultar Registos"])

with tab1:
    st.header("Registar Novo Protocolo")
    
    # -------------------------------------------------------------
    # 1. CARREGAR TIPOS DE EXAMES DO SUPABASE (COM CORREÇÃO DE SEGURANÇA)
    # -------------------------------------------------------------
    try:
        res_tipos = supabase.table("tipos_exames").select("nome").order("nome").execute()
        # Garante que pegamos apenas os nomes válidos e removemos duplicados
        lista_exames_cadastrados = [t["nome"] for t in res_tipos.data if t.get("nome")] if res_tipos.data else []
    except Exception as e:
        lista_exames_cadastrados = []
        st.warning(f"Não foi possível carregar a lista de exames cadastrados: {e}")

    # Formulário de Registo
    with st.form("form_novo_protocolo", clear_on_submit=True):
        st.subheader("Informações do Paciente e Exame")
        
        nome_paciente = st.text_input("Nome do Paciente")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Seleção de Exame Existente
            opcao_exame = st.selectbox(
                "Selecionar Exame Cadastrado",
                options=["-- Selecione --"] + lista_exames_cadastrados
            )
            
        with col2:
            # Opção para adicionar um novo tipo de exame caso não esteja na lista
            exame_novo_input = st.text_input("Ou digite um Novo Tipo de Exame (opcional)")
        
        observacoes = st.text_area("Observações Clínicas")
        
        btn_submeter = st.form_submit_button("Guardar Protocolo")
        
        if btn_submeter:
            # Determinar qual exame será salvo
            exame_final = ""
            if exame_novo_input and exame_novo_input.strip():
                exame_final = exame_novo_input.strip().title()
                
                # Opcional: Inserir automaticamente o novo tipo na tabela tipos_exames se não existir
                try:
                    if exame_final not in lista_exames_cadastrados:
                        supabase.table("tipos_exames").insert({"nome": exame_final}).execute()
                except Exception as ex:
                    # Caso já exista ou dê erro de duplicado, apenas ignora para não travar o fluxo
                    pass
                    
            elif opcao_exame and opcao_exame != "-- Selecione --":
                exame_final = opcao_exame
            
            # Validação básica
            if not nome_paciente or not exame_final:
                st.error("Por favor, preencha o nome do paciente e selecione/digite um exame.")
            else:
                try:
                    # Inserir o protocolo na tabela principal (ex: 'protocolos')
                    dados_protocolo = {
                        "paciente": nome_paciente,
                        "tipo_exame": exame_final,
                        "observacoes": observacoes
                    }
                    
                    response = supabase.table("protocolos").insert(dados_protocolo).execute()
                    
                    st.success(f"Protocolo para **{nome_paciente}** ({exame_final}) guardado com sucesso!")
                    st.rerun() # Atualiza a página para refletir novos exames cadastrados
                    
                except Exception as err:
                    st.error(f"Erro ao guardar no Supabase: {err}")

with tab2:
    st.header("Consultar Protocolos Registados")
    
    try:
        res_protocolos = supabase.table("protocolos").select("*").execute()
        dados = res_protocolos.data
        
        if dados:
            st.dataframe(dados, use_container_width=True)
        else:
            st.info("Nenhum protocolo registado até o momento.")
    except Exception as e:
        st.error(f"Erro ao carregar os protocolos: {e}")
