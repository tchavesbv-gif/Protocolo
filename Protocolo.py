import streamlit as st

def renderizar_impressao_lote(protocolos_lote):
    """
    Função para renderizar e imprimir o lote de protocolos na proporção de 4 por folha.
    """
    st.subheader("🖨️ Impressão em Lote de Protocolos (4 por Folha)")
    
    # Botão de comando de impressão do navegador
    st.markdown("""
        <button onclick="window.print()" style="
            background-color: #2b6cb0; 
            color: white; 
            padding: 10px 20px; 
            border: none; 
            border-radius: 5px; 
            font-size: 16px; 
            cursor: pointer;
            margin-bottom: 20px;">
            🖨️ Imprimir Lote Agora
        </button>
    """, unsafe_allow_html=True)

    # Estilos CSS específicos para o layout de grade (2x2) e quebra de página correta
    css_estilos = """
    <style>
        /* Esconde elementos do Streamlit na hora de imprimir */
        @media print {
            header, footer, .stSidebar, button {
                display: none !important;
            }
            body {
                background: white;
                color: black;
            }
            .pagina-lote {
                page-break-after: always;
            }
        }

        /* Container da página de impressão (Folha A4) */
        .pagina-lote {
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-template-rows: 1fr 1fr;
            gap: 15px;
            width: 100%;
            height: 100vh; /* Ocupa a altura da página para forçar a distribuição 2x2 */
            box-sizing: border-box;
            padding: 10px;
            page-break-after: always;
        }

        /* Card individual de cada protocolo */
        .card-protocolo {
            border: 1px dashed #666;
            padding: 15px;
            border-radius: 8px;
            background-color: #fff;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            font-family: Arial, sans-serif;
            font-size: 12px;
            box-sizing: border-box;
            overflow: hidden;
        }

        .card-header {
            font-weight: bold;
            font-size: 14px;
            border-bottom: 1px solid #ccc;
            padding-bottom: 5px;
            margin-bottom: 8px;
            color: #333;
        }
    </style>
    """
    
    st.markdown(css_estilos, unsafe_allow_html=True)

    # Agrupando os protocolos em blocos de 4 por página
    tamanho_pagina = 4
    for i in range(0, len(protocolos_lote), tamanho_pagina):
        lote_atual = protocolos_lote[i:i + tamanho_pagina]
        
        # Início da página (grid 2x2)
        html_pagina = '<div class="pagina-lote">'
        
        for p in lote_atual:
            # Personalize os campos conforme as colunas reais da sua tabela (ex: id, paciente, servico, data)
            num_prot = p.get('id', p.get('numero', 'N/A'))
            paciente = p.get('paciente', 'Não informado')
            servico = p.get('servico', p.get('tipo_exame', 'N/A'))
            data = p.get('data_criacao', 'N/A')
            
            html_pagina += f"""
                <div class="card-protocolo">
                    <div>
                        <div class="card-header">PROTOCOLO: #{num_prot}</div>
                        <p><b>Paciente:</b> {paciente}</p>
                        <p><b>Serviço/Exame:</b> {servico}</p>
                        <p><b>Data:</b> {data}</p>
                    </div>
                    <div style="text-align: right; font-size: 10px; color: #777; border-top: 1px solid #eee; padding-top: 4px;">
                        Secretaria Municipal de Saúde - Teixeiras
                    </div>
                </div>
            """
        
        # Preenche com espaços vazios caso a última página tenha menos de 4 protocolos
        faltando = tamanho_pagina - len(lote_atual)
        for _ in range(faltando):
            html_pagina += '<div style="border: none;"></div>'
            
        html_pagina += '</div>'
        
        # Renderiza a página no Streamlit
        st.markdown(html_pagina, unsafe_allow_html=True)

# Exemplo de uso para teste caso queira rodar:
if __name__ == "__main__":
    st.title("Gerenciamento de Lotes")
    # Exemplo simulando dados de protocolos cadastrados
    exemplo_protocolos = [
        {"id": 101, "paciente": "Maria Silva", "servico": "Hemograma Completo", "data_criacao": "30/09/2026"},
        {"id": 102, "paciente": "João Santos", "servico": "Raio-X de Tórax", "data_criacao": "30/09/2026"},
        {"id": 103, "paciente": "Ana Oliveira", "servico": "Glicemia de Jejum", "data_criacao": "30/09/2026"},
        {"id": 104, "paciente": "Carlos Souza", "servico": "Ultrassonografia", "data_criacao": "30/09/2026"},
        {"id": 105, "paciente": "Fernanda Lima", "servico": "Cardiograma", "data_criacao": "30/09/2026"},
    ]
    if st.button("Simular Visualização de Lote"):
        renderizar_impressao_lote(exemplo_protocolos)
