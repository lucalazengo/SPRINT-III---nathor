# app.py

import streamlit as st
from streamlit_option_menu import option_menu
from modules import data_handler
from pages import planejamento, acompanhamento

st.set_page_config(
    page_title="Nathor | PCP Inteligente",
    page_icon="dashboard/assets/logo.png",
    layout="wide"
)

# Função para carregar e injetar o CSS local
def load_local_css(file_path):
    try:
        with open(file_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"Arquivo CSS não encontrado em: {file_path}")

# Carrega o estilo e os dados de engenharia
load_local_css("dashboard/styles/style.css")
st.session_state['df_estruturas'] = data_handler.load_structures_data('data/processed/Planilha_Estruturas - Produto_Cor_Dim.csv')

# --- Renderização da Sidebar ---
with st.sidebar:
    st.image("dashboard/assets/logo.png", width=180)
    st.markdown("---")
    selected = option_menu(
        menu_title=None,
        options=["Início", "Planejamento", "Acompanhamento"],
        icons=["house-door-fill", "speedometer2", "clipboard-data-fill"],
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "#2C2C2C"},
            "icon": {"color": "#FAFAFA", "font-size": "20px"}, 
            "nav-link": {
                "font-size": "16px",
                "text-align": "left",
                "margin":"0px",
                "--hover-color": "#444444"
            },
            "nav-link-selected": {"background-color": "#ee6105"},
        }
    )

# --- Roteamento das Páginas ---
if selected == "Início":
    # --- CONTEÚDO DA PÁGINA INICIAL ATUALIZADO ---
    st.title("Bem-vindo ao Planejador de Pintura Inteligente")
    
    # Adiciona o contêiner com as informações do projeto, como solicitado
    with st.container(border=True):
        st.markdown("#### Sobre o Projeto")
        st.write("""
            Este projeto foi desenvolvido por **Manuel Finda Evaristo** e **Manuel Lucala Zengo** com o objetivo de criar uma ferramenta inteligente para o Planejamento e Controle da Produção (PCP) 
            de pintura na Nathor.
        """)
    
    st.info("Utilize o menu à esquerda para navegar entre as diferentes seções da aplicação.", icon="ℹ️")

    if st.session_state['df_estruturas'] is None:
        st.error("Erro Crítico: Não foi possível carregar o arquivo de estruturas de engenharia.")

elif selected == "Planejamento":
    planejamento.render_page()

elif selected == "Acompanhamento":
    acompanhamento.render_page()