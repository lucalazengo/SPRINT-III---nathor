import pandas as pd
from datetime import datetime, timedelta
import copy
import random
import time

# --- 1. Definição do Problema e Parâmetros ---
SETUP_TIME_COR = 15
SETUP_TIME_PECA = 3
DAILY_CAPACITY_MINUTES = 18 * 60 + 35
VELOCIDADE_MONOVIA = 2.0  # metros/minuto

# --- 2. Funções do Algoritmo de Otimização (v2.0) ---

def calculate_cost_v2(sequence, initial_item=None):
    """Calcula o custo total de setup (cor e peça) de uma sequência."""
    if not sequence:
        return 0
    total_setup_cost = 0
    current_item = initial_item
    if current_item is not None:
        next_item = sequence[0]
        if current_item['Tinta'] != next_item['Tinta']:
            total_setup_cost += SETUP_TIME_COR
        if current_item['CODIGO_COMPONENTE'] != next_item['CODIGO_COMPONENTE']:
            total_setup_cost += SETUP_TIME_PECA
    for i in range(len(sequence) - 1):
        current_item = sequence[i]
        next_item = sequence[i+1]
        if current_item['Tinta'] != next_item['Tinta']:
            total_setup_cost += SETUP_TIME_COR
        if current_item['CODIGO_COMPONENTE'] != next_item['CODIGO_COMPONENTE']:
            total_setup_cost += SETUP_TIME_PECA
    return total_setup_cost

def calculate_prioritization_score(item):
    """Calcula a pontuação de prioridade para um item."""
    saldo = item['Estoque'] - item['Pedidos']
    due_date = item['Data_de_Entrega']
    prioridade_urgente = 1 if saldo >= 0 else 0
    prioridade_data = due_date.timestamp()
    prioridade_saldo = abs(saldo) if saldo < 0 else 0
    return (prioridade_urgente, prioridade_data, -prioridade_saldo)

def daily_sequencing_and_scheduling(unscheduled_items):
    """Cria a programação inicial usando a heurística de priorização."""
    schedule = []
    day_number = 1
    remaining_items = copy.deepcopy(unscheduled_items)
    while remaining_items:
        remaining_items.sort(key=calculate_prioritization_score)
        items_for_today_prioritized = []
        time_used_today_minutes = 0
        items_to_remove_from_main_list = []
        last_color_of_day = None
        for item in remaining_items:
            item_production_time_minutes = item['Tempo_Calculado'] * 60
            setup_cost_to_add = 0
            if items_for_today_prioritized:
                if last_color_of_day != item['Tinta']:
                    setup_cost_to_add = SETUP_TIME_COR
            if time_used_today_minutes + item_production_time_minutes + setup_cost_to_add <= DAILY_CAPACITY_MINUTES:
                items_for_today_prioritized.append(item)
                time_used_today_minutes += item_production_time_minutes
                if last_color_of_day != item['Tinta']:
                    time_used_today_minutes += setup_cost_to_add
                    last_color_of_day = item['Tinta']
                items_to_remove_from_main_list.append(item)
        if not items_for_today_prioritized:
            break
        color_groups = {}
        for item in items_for_today_prioritized:
            color = item['Tinta']
            if color not in color_groups:
                color_groups[color] = []
            color_groups[color].append(item)
        sorted_colors = sorted(color_groups.keys(), key=lambda c: calculate_prioritization_score(color_groups[c][0]))
        initial_daily_sequence = []
        for color in sorted_colors:
            initial_daily_sequence.extend(color_groups[color])
        current_day = {'day': day_number, 'items': initial_daily_sequence}
        schedule.append(current_day)
        remaining_items = [item for item in remaining_items if item not in items_to_remove_from_main_list]
        day_number += 1
    return schedule

def tabu_search_optimizer(daily_sequence, initial_item=None, tabu_tenure=7, max_iterations=100):
    """Otimiza a sequência de um único dia usando Busca Tabu."""
    current_solution = list(daily_sequence)
    best_solution = list(daily_sequence)
    best_cost = calculate_cost_v2(best_solution, initial_item)
    tabu_list = []
    for iteration in range(max_iterations):
        best_neighbor, best_neighbor_cost, best_move = None, float('inf'), None
        for i in range(len(current_solution)):
            for j in range(i + 1, len(current_solution)):
                neighbor = list(current_solution)
                neighbor[i], neighbor[j] = neighbor[j], neighbor[i]
                move = tuple(sorted((i, j)))
                neighbor_cost = calculate_cost_v2(neighbor, initial_item)
                if move not in tabu_list and neighbor_cost < best_neighbor_cost:
                    best_neighbor, best_neighbor_cost, best_move = neighbor, neighbor_cost, move
        if best_neighbor:
            current_solution = best_neighbor
            tabu_list.append(best_move)
            if len(tabu_list) > tabu_tenure:
                tabu_list.pop(0)
            if best_neighbor_cost < best_cost:
                best_solution, best_cost = best_neighbor, best_neighbor_cost
    return best_solution


# --- 3. Execução Principal ---

if __name__ == "__main__":
    try:
        # --- ETAPA DE PREPARAÇÃO DE DADOS ---
        print("Iniciando a preparação de dados...")

        # 1. Carregar os arquivos
        path_estruturas = r'../data/processed/Planilha_Estruturas - Produto_Cor_Dim.csv'
        path_pedidos = r'../data/processed/pedidos.csv'
        
        df_estruturas = pd.read_csv(path_estruturas, sep=';', encoding='latin1')
        df_pedidos = pd.read_csv(path_pedidos, sep=';', encoding='latin1')

        # Limpeza e conversão de tipos de dados
        df_pedidos['Data_Entrega'] = pd.to_datetime(df_pedidos['Data_Entrega'], errors='coerce')
        df_pedidos.dropna(subset=['Data_Entrega'], inplace=True)
        
        # 2. Gerar a lista de tarefas de pintura unificada
        lista_tarefas_pintura = []
        for _, pedido in df_pedidos.iterrows():
            necessidade_producao = int(pedido.get('Pedidos', 0)) - int(pedido.get('Estoque', 0))
            
            if necessidade_producao > 0:
                componentes_do_produto = df_estruturas[df_estruturas['CODIGO_PRODUTO'] == pedido['CODIGO_PRODUTO']]
                
                for _, componente in componentes_do_produto.iterrows():
                    if pd.isna(componente['DESCRICAO_COR']):
                        continue

                    pecas_gancheira = pd.to_numeric(componente.get('Peças p/ gancheira', 1), errors='coerce')
                    espacamento = pd.to_numeric(componente.get('Espaçamento', 0.5), errors='coerce')
                    
                    if pecas_gancheira and espacamento and pecas_gancheira > 0:
                        tempo_calculado_minutos = ((necessidade_producao / pecas_gancheira) * espacamento) / VELOCIDADE_MONOVIA
                    else:
                        tempo_calculado_minutos = 0

                    tarefa = {
                        'CODIGO_PRODUTO_FINAL': pedido['CODIGO_PRODUTO'],
                        'CODIGO_COMPONENTE': componente['CODIGO_COMPONENTE'],
                        'Tinta': componente['DESCRICAO_COR'],
                        'Quantidade_Planejada': necessidade_producao,
                        'Estoque': pedido['Estoque'],
                        'Pedidos': pedido['Pedidos'],
                        'Data_de_Entrega': pedido['Data_Entrega'],
                        'Tempo_Calculado': tempo_calculado_minutos / 60
                    }
                    lista_tarefas_pintura.append(tarefa)

        print(f"Preparação concluída. Total de {len(lista_tarefas_pintura)} lotes de componentes a serem planejados.")
        
        # --- ETAPA DE OTIMIZAÇÃO ---
        start_time = time.time()
        initial_schedule = daily_sequencing_and_scheduling(lista_tarefas_pintura)
        
        optimized_schedule = []
        print("Otimizando a sequência de cada dia com a Busca Tabu (v2.0)...")
        last_item_from_previous_day = None
        for day_data in initial_schedule:
            initial_daily_sequence = day_data['items']
            refined_daily_sequence = tabu_search_optimizer(initial_daily_sequence, initial_item=last_item_from_previous_day)
            refined_setup_cost = calculate_cost_v2(refined_daily_sequence, last_item_from_previous_day)
            production_time = sum(item['Tempo_Calculado'] * 60 for item in refined_daily_sequence)
            optimized_schedule.append({
                'day': day_data['day'],
                'items': refined_daily_sequence,
                'time_used_minutes': production_time + refined_setup_cost,
                'total_components': sum(item['Quantidade_Planejada'] for item in refined_daily_sequence),
                'setup_cost': refined_setup_cost
            })
            if refined_daily_sequence:
                last_item_from_previous_day = refined_daily_sequence[-1]
        print("Otimização concluída.")

        # --- ETAPA DE RESULTADOS ---
        total_setup_optimized = sum(day['setup_cost'] for day in optimized_schedule)
        total_production_time_optimized = sum(day['time_used_minutes'] for day in optimized_schedule)
        end_time = time.time()

        print("\n" + "="*50 + "\n")
        print("Gerando o Cronograma de Produção Diário (Otimizado com Dados Reais):\n")
        for day in optimized_schedule:
            print(f"--- Dia {day['day']} ---")
            print(f"Tempo Total de Trabalho: {day['time_used_minutes']:.2f} minutos ({day['time_used_minutes'] / 60:.2f} horas)")
            print(f"  (Tempo de Pintura: {day['time_used_minutes'] - day['setup_cost']:.2f} min | Tempo de Setup: {day['setup_cost']:.2f} min)")
            print("Itens a Serem Pintados (sequência otimizada):")
            for item in day['items']:
                saldo = item['Estoque'] - item['Pedidos']
                status = "URGENTE" if saldo < 0 else "normal"
                print(f"  - Componente: {item['CODIGO_COMPONENTE']}, Tinta: {item['Tinta']}, Qtd Lote: {item['Quantidade_Planejada']}, Status: {status}, Entrega Pedido: {item['Data_de_Entrega'].strftime('%Y-%m-%d')}")
        
        print("\n" + "="*50 + "\n")
        print("Resumo do Agendamento Otimizado:")
        print(f"Custo total de setup (Cor e Peça): {total_setup_optimized:.2f} minutos")
        print(f"Tempo total de trabalho: {total_production_time_optimized:.2f} minutos ({total_production_time_optimized / 60:.2f} horas)")
        print(f"Total de dias necessários: {len(optimized_schedule)}")
        print(f"Tempo de execução do algoritmo: {end_time - start_time:.4f} segundos")

    except FileNotFoundError as e:
        print(f"Erro: Arquivo não encontrado. Verifique o caminho: {e.filename}")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")