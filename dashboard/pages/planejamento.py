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
    if uploaded_file:
        st.subheader("Gerar Cronograma")
        if st.button("Executar Otimização", type="primary", use_container_width=True):
            with st.spinner("Preparando dados..."):
                tarefas = data_handler.prepare_task_list(uploaded_file, st.session_state['df_estruturas'])
            with st.spinner(f"Otimizando {len(tarefas)} lotes..."):
                cronograma, rejeitados = optimizer.run_full_optimization(tarefas, config)
                st.session_state['cronograma_final'] = cronograma
                st.session_state['tarefas_rejeitadas'] = rejeitados
            st.success("Otimização concluída!")
            st.balloons()
    if 'cronograma_final' in st.session_state:
        st.divider()
        st.header("Passo 3: Análise dos Resultados")
        cronograma = st.session_state['cronograma_final']
        rejeitados = st.session_state.get('tarefas_rejeitadas', [])
        if rejeitados:
            with st.container(border=True):
                st.warning(f"Atenção: {len(rejeitados)} lotes não puderam ser planejados.", icon="⚠️")
                df_rejeitados = pd.DataFrame(rejeitados)
                output_excel_rejeitados = io.BytesIO()
                with pd.ExcelWriter(output_excel_rejeitados, engine='xlsxwriter') as writer:
                    df_rejeitados.to_excel(writer, index=False, sheet_name='Rejeitados')
                st.download_button(
                    label="📥 Baixar Relatório de Exceções (.xlsx)",
                    data=output_excel_rejeitados.getvalue(),
                    file_name="relatorio_excecoes.xlsx"
                )
        with st.container(border=True):
            st.subheader("Indicadores Chave de Performance (KPIs)")
            total_dias, total_setup, total_trabalho = len(cronograma), sum(d['setup_cost'] for d in cronograma)/60, sum(d['time_used_minutes'] for d in cronograma)/60
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Dias de Produção", f"{total_dias} dias")
            kpi2.metric("Total Horas de Setup", f"{total_setup:.2f} h")
            kpi3.metric("Total Horas de Trabalho", f"{total_trabalho:.2f} h")
        with st.container(border=True):
            st.subheader("Cronograma Detalhado por Dia")
            tabs = st.tabs([f"Dia {i+1}" for i in range(len(cronograma))])
            for i, tab in enumerate(tabs):
                with tab:
                    dia_data = cronograma[i]
                    df_dia_original = pd.DataFrame(dia_data['items'])
                    df_dia_para_exibicao = df_dia_original.copy()
                    df_dia_para_exibicao['Data_de_Entrega'] = df_dia_para_exibicao['Data_de_Entrega'].dt.strftime('%d/%m/%Y')
                    st.dataframe(df_dia_para_exibicao, use_container_width=True)
                    output_csv = df_dia_para_exibicao.to_csv(sep=';', index=False, encoding='latin1').encode('latin1')
                    output_excel = io.BytesIO()
                    with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
                        df_dia_para_exibicao.to_excel(writer, index=False, sheet_name=f'Dia_{dia_data["day"]}')
                    col_dl1, col_dl2 = st.columns(2)
                    col_dl1.download_button("📥 Baixar CSV", output_csv, f"cronograma_dia_{dia_data['day']}.csv", "text/csv")
                    col_dl2.download_button("📥 Baixar Excel", output_excel.getvalue(), f"cronograma_dia_{dia_data['day']}.xlsx")