# app/pages/planejamento.py

import streamlit as st
import pandas as pd
from modules import data_handler, optimizer
import io
from datetime import datetime

def render_page():
    """Renderiza a página de planejamento com uma arquitetura de abas robusta."""
    
    # --- 1. INICIALIZAÇÃO E CARGA DE DADOS ---
    df_estruturas = st.session_state.get('df_estruturas')
    if df_estruturas is None:
        st.error("Dados de estruturas não carregados. Por favor, reinicie a aplicação.")
        st.stop()

    if 'CODIGO_PRODUTO' in df_estruturas.columns:
        df_estruturas['CODIGO_PRODUTO_STR'] = df_estruturas['CODIGO_PRODUTO'].astype('Int64').astype(str)

    # Inicializa os estados da sessão para persistência dos dados
    if 'manual_orders' not in st.session_state: st.session_state.manual_orders = pd.DataFrame()
    if 'uploaded_orders' not in st.session_state: st.session_state.uploaded_orders = pd.DataFrame()
    if 'tarefas_calibradas' not in st.session_state: st.session_state.tarefas_calibradas = pd.DataFrame()

    st.header("Otimizador do Plano de Pintura")

    # --- 2. ESTRUTURA DE ABAS PARA ENTRADA DE DADOS ---
    tab1, tab2, tab3 = st.tabs([
        "📤 Carregar Arquivo", 
        "✍️ Adicionar Manualmente", 
        "📋 Revisar, Calibrar e Otimizar"
    ])

    with tab1:
        st.subheader("Carregar Múltiplos Pedidos de um Arquivo")
        uploaded_file = st.file_uploader(
            "Selecione o arquivo de Pedidos do Mês (.csv)",
            type=['csv'],
            key='uploader_key'
        )
        if uploaded_file:
            st.session_state.uploaded_orders = pd.read_csv(uploaded_file, sep=',')
            st.session_state.manual_orders = pd.DataFrame() # Prioriza o arquivo carregado
            st.success(f"Arquivo '{uploaded_file.name}' carregado. Vá para a aba 'Revisar, Calibrar e Otimizar'.")

        with tab2:
            codigo_produto_input = st.text_input(
                "Digite o Código do Produto e clique Enter", 
                placeholder="Aguardando código...",
                help="Após digitar o código, pressione Enter para buscar a descrição."
            )
            descricao_encontrada = ""
            produto_valido = False
            if codigo_produto_input:
                match = df_estruturas[df_estruturas['CODIGO_PRODUTO_STR'] == codigo_produto_input.strip()]
                if not match.empty:
                    descricao_encontrada = match['DESCRICAO_PRODUTO'].iloc[0]
                    produto_valido = True
                    st.info(f"Produto encontrado: **{descricao_encontrada}**")
                else:
                    st.warning("Código do produto não encontrado.")
            
            with st.form("form_add_pedido", clear_on_submit=True):
                st.text_input("Descrição do Produto", value=descricao_encontrada, disabled=True)
                col_form1, col_form2 = st.columns(2)
                pedidos = col_form1.number_input("Quantidade de Pedidos", min_value=1, step=10)
                estoque = col_form2.number_input("Estoque Atual", min_value=0, step=10)
                data_entrega = st.date_input("Data de Entrega", min_value=datetime.today())
                
                submitted = st.form_submit_button(
                    "➕ Confirmar Adição do Pedido", 
                    use_container_width=True,
                    disabled=not produto_valido
                )
                if submitted:
                    novo_pedido = {
                        "CODIGO_PRODUTO": codigo_produto_input.strip(),
                        "DESCRICAO_PRODUTO": descricao_encontrada,
                        "Pedidos": int(pedidos), "Estoque": int(estoque),
                        "Data_Entrega": data_entrega.strftime('%d/%m/%Y')
                    }
                    st.session_state.manual_orders.append(novo_pedido)
                    st.session_state.tarefas_calibradas = pd.DataFrame()
                    st.toast(f"Pedido para '{descricao_encontrada}' adicionado!", icon="👍")
    
    with tab3:
        st.subheader("Pedidos a Serem Otimizados")
        
        df_pedidos_fonte = pd.DataFrame()
        if not st.session_state.manual_orders.empty:
            df_pedidos_fonte = st.session_state.manual_orders
        elif not st.session_state.uploaded_orders.empty:
            df_pedidos_fonte = st.session_state.uploaded_orders

        if df_pedidos_fonte.empty:
            st.info("Nenhum pedido carregado ou adicionado ainda. Use as abas anteriores para fornecer os dados.")
        else:
            # Prepara o stream de dados para o data_handler
            csv_buffer = io.StringIO()
            df_pedidos_fonte.to_csv(csv_buffer, index=False, sep=',')
            csv_buffer.seek(0)
            pedidos_input_stream = io.BytesIO(csv_buffer.read().encode('latin1'))
            
            # Gera a lista de tarefas preliminares
            tarefas_iniciais = data_handler.prepare_task_list(pedidos_input_stream, df_estruturas)
            
            if not tarefas_iniciais:
                 st.warning("Nenhuma tarefa com necessidade de produção (Pedidos > Estoque) foi encontrada nos dados fornecidos.")
            else:
                st.markdown("#### Mesa de Calibração")
                st.info("Ajuste as regras de negócio abaixo para refletir a realidade da fábrica antes de otimizar.", icon="✍️")
                
                df_para_calibrar = pd.DataFrame(tarefas_iniciais)
                df_para_calibrar['PECAS_COM_PROCESSO_ADICIONAL'] = df_para_calibrar['PECAS_COM_PROCESSO_ADICIONAL'].apply(lambda x: True if x == 'Sim' else False)
                
                df_calibrado = st.data_editor(
                    df_para_calibrar,
                    column_config={
                        "PECAS_COM_PROCESSO_ADICIONAL": st.column_config.CheckboxColumn("Processo Adicional?", default=False),
                        "FORNECIMENTO_METALURGIA": st.column_config.NumberColumn("Forn. Metalurgia (un/dia)", format="%d", required=True),
                        "CAPACIDADE_GAIOLAS": st.column_config.NumberColumn("Cap. Gaiolas (un)", format="%d", required=True),
                    },
                    disabled=[col for col in df_para_calibrar.columns if col not in ['PECAS_COM_PROCESSO_ADICIONAL', 'FORNECIMENTO_METALURGIA', 'CAPACIDADE_GAIOLAS']],
                    use_container_width=True, key="data_editor_tarefas"
                )
                
                df_calibrado['PECAS_COM_PROCESSO_ADICIONAL'] = df_calibrado['PECAS_COM_PROCESSO_ADICIONAL'].apply(lambda x: 'Sim' if x else 'Não')
                
                st.divider()
                st.subheader("Executar Otimização")
                with st.expander("Parâmetros de Otimização (Avançado)"):
                    config = {
                        'horizonte_dias': st.number_input("Horizonte de Planejamento (dias)", min_value=1, max_value=30, value=7),
                        'setup_cor': st.number_input("Setup de Cor (min)", value=15),
                        'setup_peca': st.number_input("Setup de Peça (min)", value=3),
                        'daily_capacity': st.number_input("Capacidade Diária (min)", value=1115),
                        'tabu_tenure': st.number_input("Duração Tabu", value=7),
                        'max_iterations': st.number_input("Iterações Máximas", value=100)
                    }

                if st.button("Gerar Cronograma Otimizado", type="primary", use_container_width=True):
                    tarefas_para_otimizar = df_calibrado.to_dict('records')
                    with st.spinner(f"Otimizando {len(tarefas_para_otimizar)} lotes..."):
                        cronograma, rejeitados = optimizer.run_full_optimization(tarefas_para_otimizar, config)
                        st.session_state['cronograma_final'] = cronograma
                        st.session_state['tarefas_rejeitadas'] = rejeitados
                    st.success("Otimização concluída!")

    # --- Seção de Resultados ---
    if 'cronograma_final' in st.session_state and st.session_state['cronograma_final']:
        st.divider()
        st.header("Análise dos Resultados")
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
                    col_dl1.download_button("📥 Baixar CSV", output_csv, f"cronograma_dia_{dia_data['day']}.csv", "text/csv", use_container_width=True)
                    col_dl2.download_button("📥 Baixar Excel", output_excel.getvalue(), f"cronograma_dia_{dia_data['day']}.xlsx", use_container_width=True)