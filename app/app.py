# app.py

import streamlit as st
from streamlit_option_menu import option_menu
from modules import data_handler
from pages import planejamento 

st.set_page_config(
    page_title="Nathor | PCP Inteligente",
    page_icon="app/assets/logo.png",
    layout="wide",
    initial_sidebar_state="expanded" # Garante que a sidebar comece expandida
)

# Função para carregar e injetar o CSS local
def load_local_css(file_path):
    try:
        with open(file_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"Arquivo CSS não encontrado em: {file_path}")

# Carrega o estilo e os dados de engenharia
load_local_css("app/styles/style.css")
st.session_state['df_estruturas'] = data_handler.load_structures_data('data/processed/Planilha_Estruturas - Produto_Cor_Dim.csv')

# --- Renderização da Sidebar com Contêineres Separados ---
with st.sidebar:
    # Contêiner exclusivo para o logo
    with st.container():
        st.image("app/assets/logo.png", width=180)

    # Contêiner exclusivo para o menu
    with st.container():
        selected = option_menu(
            menu_title=None,
            options=["Início", "Planejamento"],
            icons=["house-door-fill", "speedometer2"],
            default_index=0,
        )

# --- Roteamento das Páginas ---
if selected == "Início":
    st.title("🤖 Bem-vindo ao Planejador de Pintura Inteligente")
    st.markdown("### Este sistema otimiza o sequenciamento da produção de pintura para minimizar custos e maximizar a eficiência.")
    st.info("👈 **Selecione 'Planejamento' na barra lateral para começar a otimização.**", icon="ℹ️")
    if st.session_state['df_estruturas'] is None:
        st.error("Erro Crítico: Não foi possível carregar o arquivo de estruturas de engenharia.")

elif selected == "Planejamento":
    planejamento.render_page()