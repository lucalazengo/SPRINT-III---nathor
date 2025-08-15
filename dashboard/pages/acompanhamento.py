# app/pages/acompanhamento.py

import streamlit as st
import pandas as pd

def render_page():
    """Renderiza o Painel de Pulso Operacional para acompanhamento da produção."""
    
    st.header("Painel de Acompanhamento da Produção")

    # --- Verificação de pré-requisito: um cronograma deve existir ---
    if 'cronograma_final' not in st.session_state or not st.session_state['cronograma_final']:
        st.warning(" Nenhum cronograma foi gerado ainda. Por favor, vá para a página de 'Planejamento' e gere um cronograma primeiro.", icon="⚠️")
        st.stop()

    # --- Inicialização dos dados de progresso ---
    if 'progresso_producao' not in st.session_state:
        st.session_state.progresso_producao = {}

    cronograma = st.session_state['cronograma_final']
    
    # --- Seletor de Dia ---
    dias_disponiveis = [f"Dia {d['day']}" for d in cronograma]
    dia_selecionado_str = st.selectbox("Selecione o dia para acompanhar:", dias_disponiveis)
    
    dia_selecionado_num = int(dia_selecionado_str.split(" ")[1])
    dados_dia = next((d for d in cronograma if d['day'] == dia_selecionado_num), None)

    if dados_dia:
        df_dia = pd.DataFrame(dados_dia['items'])
        
        # --- Preparação do DataFrame para Edição ---
        df_dia['id_tarefa'] = [f"dia{dia_selecionado_num}_{i}" for i in range(len(df_dia))]
        df_dia['Produzido'] = df_dia['id_tarefa'].apply(
            lambda x: st.session_state.progresso_producao.get(x, 0)
        )
        df_dia['Status'] = df_dia.apply(
            lambda row: "Concluído" if row['Produzido'] >= row['Quantidade_Planejada'] else ("Em Andamento" if row['Produzido'] > 0 else "Pendente"),
            axis=1
        )
        
        # --- CÁLCULO DAS NOVAS MÉTRICAS ---
        total_horas_trabalho = dados_dia.get('time_used_minutes', 0) / 60
        total_horas_setup = dados_dia.get('setup_cost', 0) / 60
        
        # Calcula o total de mudanças de peça no dia
        mudancas_de_peca = 0
        if len(df_dia) > 1:
            for i in range(len(df_dia) - 1):
                if df_dia.iloc[i]['CODIGO_COMPONENTE'] != df_dia.iloc[i+1]['CODIGO_COMPONENTE']:
                    mudancas_de_peca += 1

        # --- KPIs DO DIA SELECIONADO ---
        total_planejado_dia = df_dia['Quantidade_Planejada'].sum()
        total_produzido_dia = df_dia['Produzido'].sum()
        progresso_percentual = (total_produzido_dia / total_planejado_dia * 100) if total_planejado_dia > 0 else 0

        st.subheader(f"Métricas do {dia_selecionado_str}")
        
        # KPIs de Produção
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Planejado (un)", f"{total_planejado_dia}")
        kpi2.metric("Produzido (un)", f"{total_produzido_dia}")
        kpi3.metric("Progresso do Dia", f"{progresso_percentual:.1f}%")
        st.progress(int(progresso_percentual))

        st.markdown("---")

        # KPIs de Eficiência
        kpi4, kpi5, kpi6 = st.columns(3)
        kpi4.metric("Total Horas de Trabalho", f"{total_horas_trabalho:.2f} h")
        kpi5.metric("Total Horas de Setup", f"{total_horas_setup:.2f} h")
        kpi6.metric("Mudanças de Peça no Dia", f"{mudancas_de_peca} trocas")

        st.divider()

        # --- Tabela Interativa de Produção ---
        st.subheader("Registre a produção por lote:")
        
        colunas_visiveis = [
            'DESCRICAO_PRODUTO', 'Componente', 'Tinta', 
            'Quantidade_Planejada', 'Produzido', 'Status'
        ]
        
        df_editado = st.data_editor(
            df_dia[colunas_visiveis],
            column_config={
                "Produzido": st.column_config.NumberColumn(
                    "Quantidade Produzida",
                    help="Insira a quantidade produzida para este lote.",
                    min_value=0,
                    step=1,
                ),
                "Status": st.column_config.TextColumn("Status")
            },
            use_container_width=True,
            disabled=['DESCRICAO_PRODUTO', 'Componente', 'Tinta', 'Quantidade_Planejada', 'Status']
        )
        
        # --- Lógica para salvar o progresso ---
        for index, row in df_editado.iterrows():
            id_tarefa = df_dia.loc[index, 'id_tarefa']
            quantidade_produzida = row['Produzido']
            st.session_state.progresso_producao[id_tarefa] = quantidade_produzida