# app/pages/planejamento.py

import streamlit as st
import pandas as pd
from modules import data_handler, optimizer
import io

def render_page():
    """Renderiza a página de planejamento em um fluxo vertical e coeso."""

    if 'df_estruturas' not in st.session_state or st.session_state['df_estruturas'] is None:
        st.error("Dados de estruturas não carregados. Por favor, reinicie a aplicação.")
        st.stop()

    st.header("Otimizador do Plano de Pintura")
    st.markdown("Siga os passos abaixo para gerar um cronograma de produção otimizado.")

    # --- Contêiner 1: Entradas e Configuração ---
    with st.container(border=True):
        st.subheader("Passo 1: Carregar Pedidos e Configurar")
        
        uploaded_file = st.file_uploader(
            "Selecione o arquivo de Pedidos do Mês (.csv)",
            type=['csv'],
            key='uploader_key'
        )
        
        with st.expander("Parâmetros de Otimização (Avançado)"):
            config = {
                'setup_cor': st.number_input("Setup de Cor (min)", value=15),
                'setup_peca': st.number_input("Setup de Peça (min)", value=3),
                'daily_capacity': st.number_input("Capacidade Diária (min)", value=1115),
                'tabu_tenure': st.number_input("Duração Tabu", value=7),
                'max_iterations': st.number_input("Iterações Máximas", value=100)
            }

    # --- Contêiner 2: Ação ---
    if uploaded_file:
        st.subheader("Passo 2: Gerar Cronograma")
        if st.button("Executar Otimização", type="primary", use_container_width=True):
            with st.spinner("Preparando dados..."):
                tarefas = data_handler.prepare_task_list(uploaded_file, st.session_state['df_estruturas'])
            
            with st.spinner(f"Otimizando {len(tarefas)} lotes... Esta operação é complexa e pode levar um momento."):
                cronograma_final = optimizer.run_full_optimization(tarefas, config)
                st.session_state['cronograma_final'] = cronograma_final
            
            st.success("Otimização concluída com sucesso!")
            st.balloons()

    # --- Contêiner 3: Resultados ---
    if 'cronograma_final' in st.session_state and st.session_state['cronograma_final']:
        st.divider()
        st.header("Passo 3: Análise dos Resultados")
        cronograma = st.session_state['cronograma_final']
        
        with st.container(border=True):
            st.subheader("Indicadores Chave de Performance (KPIs)")
            total_dias = len(cronograma)
            total_setup = sum(day['setup_cost'] for day in cronograma) / 60
            total_trabalho = sum(day['time_used_minutes'] for day in cronograma) / 60
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Dias de Produção", f"{total_dias} dias")
            kpi2.metric("Total Horas de Setup", f"{total_setup:.2f} h")
            kpi3.metric("Total Horas de Trabalho", f"{total_trabalho:.2f} h")
        
        with st.container(border=True):
            st.subheader("Cronograma Detalhado por Dia")
            tabs = st.tabs([f"Dia {i+1}" for i in range(len(cronograma))])
            for i, tab in enumerate(tabs):
                # conteúdo das abas: tabela e botões de download
                with tab:
                    dia_data = cronograma[i]
                    df_dia = pd.DataFrame(dia_data['items'])
                    st.dataframe(df_dia, use_container_width=True)

                    # CSV
                    output_csv = df_dia.to_csv(sep=';', index=False, encoding='latin1').encode('latin1')

                    # Excel
                    output_excel = io.BytesIO()
                    with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
                        df_dia.to_excel(writer, index=False, sheet_name=f'Dia_{dia_data["day"]}')

                    col_dl1, col_dl2 = st.columns(2)
                    col_dl1.download_button(
                        " Baixar CSV",
                        output_csv,
                        f"cronograma_dia_{dia_data['day']}.csv",
                        "text/csv",
                        use_container_width=True
                    )
                    col_dl2.download_button(
                        " Baixar Excel",
                        output_excel.getvalue(),
                        f"cronograma_dia_{dia_data['day']}.xlsx",
                        use_container_width=True
                    )
    else:
        st.info("Os resultados da otimização aparecerão aqui.", icon="📊")
