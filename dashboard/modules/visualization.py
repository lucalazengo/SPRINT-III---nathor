# app/modules/visualization.py

import pandas as pd
import plotly.figure_factory as ff
from datetime import datetime, timedelta

def create_gantt_chart(optimized_schedule, config):
    """
    Cria um gráfico de Gantt detalhado, mostrando cada lote de pintura individualmente,
    a partir do cronograma otimizizado.
    """
    gantt_data = []
    # Define um tempo de início arbitrário para a simulação visual
    simulation_start_time = datetime.now().replace(hour=5, minute=10, second=0, microsecond=0)
    
    color_map = {
        "PRETO": "#111111", "BRANCO": "#FAFAFA", "AZUL": "#0D6EFD", "VERMELHO": "#DC3545",
        "VERDE": "#198754", "AMARELO": "#FFC107", "ROSA": "#D63384", "LARANJA": "#FD7E14",
        "CINZA": "#6C757D", "ROXO": "#6F42C1", "DEFAULT": "#374151"
    }

    last_item_overall = None
    
    for day in optimized_schedule:
        # Define o início do dia de trabalho
        current_time = simulation_start_time.replace(hour=5, minute=10) + timedelta(days=day['day'] - 1)
        
        # O primeiro item do dia considera o último item do dia anterior para o setup
        if last_item_overall:
            if last_item_overall['Tinta'] != day['items'][0]['Tinta']:
                current_time += timedelta(minutes=config['setup_cor'])
            if last_item_overall['CODIGO_COMPONENTE'] != day['items'][0]['CODIGO_COMPONENTE']:
                current_time += timedelta(minutes=config['setup_peca'])

        for i, item in enumerate(day['items']):
            # Calcula a duração do setup entre as tarefas internas do dia
            if i > 0:
                prev_item = day['items'][i-1]
                if prev_item['Tinta'] != item['Tinta']:
                    current_time += timedelta(minutes=config['setup_cor'])
                if prev_item['CODIGO_COMPONENTE'] != item['CODIGO_COMPONENTE']:
                    current_time += timedelta(minutes=config['setup_peca'])
            
            task_duration_minutes = item['Tempo_Calculado_Minutos']
            task_start_time = current_time
            task_end_time = task_start_time + timedelta(minutes=task_duration_minutes)

            # Adiciona a tarefa ao Gantt
            gantt_data.append(dict(
                Task=f"{item['CODIGO_COMPONENTE']} ({item['Quantidade_Planejada']} un)",
                Start=task_start_time.strftime("%Y-%m-%d %H:%M:%S"),
                Finish=task_end_time.strftime("%Y-%m-%d %H:%M:%S"),
                Resource=item['Tinta'], # Agora o recurso é a Tinta, para agrupar e colorir corretamente
            ))
            
            # Atualiza o tempo atual
            current_time = task_end_time
        
        # Guarda o último item do dia para o cálculo de setup do dia seguinte
        if day['items']:
            last_item_overall = day['items'][-1]
    
    if not gantt_data:
        return None

    # As chaves em color_map agora correspondem aos valores em 'Resource'
    fig = ff.create_gantt(
        gantt_data,
        colors=color_map,
        index_col='Resource',
        show_colorbar=True,
        group_tasks=True,
        showgrid_x=True,
        title="Cronograma Detalhado de Lotes de Pintura"
    )
    
    fig.update_layout(
        xaxis_title="Linha do Tempo",
        yaxis_title="Cor da Tinta",
        plot_bgcolor='#1F2937',
        paper_bgcolor='#1F2937',
        font_color='#F9FAFB',
        legend_title_text='Legenda'
    )
    return fig