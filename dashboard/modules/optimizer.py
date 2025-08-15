# app/modules/optimizer.py

import pandas as pd
from datetime import datetime, timedelta
import copy
import math

# --- Funções de Lógica e Otimização ---

def calculate_cost(sequence, setup_cor, setup_peca, initial_item=None):
    """Calcula o custo total de setup (cor e peça) de uma sequência."""
    if not sequence: return 0
    total_setup_cost = 0
    current_item = initial_item
    if current_item is not None:
        next_item = sequence[0]
        if current_item['Tinta'] != next_item['Tinta']: total_setup_cost += setup_cor
        if current_item['CODIGO_COMPONENTE'] != next_item['CODIGO_COMPONENTE']: total_setup_cost += setup_peca
    for i in range(len(sequence) - 1):
        current_item, next_item = sequence[i], sequence[i+1]
        if current_item['Tinta'] != next_item['Tinta']: total_setup_cost += setup_cor
        if current_item['CODIGO_COMPONENTE'] != next_item['CODIGO_COMPONENTE']: total_setup_cost += setup_peca
    return total_setup_cost

def calculate_prioritization_score(item):
    """Calcula a pontuação de prioridade para um item."""
    saldo = item['Estoque'] - item['Pedidos']
    due_date = item['Data_de_Entrega']
    return (1 if saldo >= 0 else 0, due_date.timestamp(), -abs(saldo) if saldo < 0 else 0)

def create_initial_schedule(all_items, daily_capacity, setup_cor):
    """
    Cria a programação inicial usando a heurística de priorização.
    Separa as tarefas em agendáveis e rejeitadas.
    """
    schedule = []
    rejected_tasks = []
    
    schedulable_items = []
    for item in all_items:
        item['id_tarefa'] = f"{item['CODIGO_PRODUTO_FINAL']}_{item['CODIGO_COMPONENTE']}_{item['Tinta']}"
        
        # CORRIGIDO: Usa os nomes de chave corretos que vêm do data_handler
        gancheiras_necessarias = math.ceil(item['Quantidade_Planejada'] / item['Pecas_por_Gancheira'])
        if gancheiras_necessarias > item['Estoque Gancheiras']:
            item['Motivo_Rejeicao'] = f"Gancheiras Insuficientes (Necessário: {gancheiras_necessarias}, Disponível: {item['Estoque Gancheiras']})"
            rejected_tasks.append(item)
        else:
            schedulable_items.append(item)

    day_number = 1
    remaining_items = copy.deepcopy(schedulable_items)
    while remaining_items:
        remaining_items.sort(key=calculate_prioritization_score)
        items_for_today, time_used, to_remove, last_color = [], 0, [], None
        
        for item in remaining_items:
            prod_time = item['Tempo_Calculado_Minutos']
            setup_cost = setup_cor if items_for_today and last_color != item['Tinta'] else 0
            
            if time_used + prod_time + setup_cost <= daily_capacity:
                items_for_today.append(item)
                time_used += prod_time + setup_cost
                last_color = item['Tinta']
                to_remove.append(item)
                
        if not items_for_today: break
            
        color_groups = {}
        for item in items_for_today:
            color = item['Tinta']
            if color not in color_groups: color_groups[color] = []
            color_groups[color].append(item)
        
        sorted_colors = sorted(color_groups.keys(), key=lambda c: calculate_prioritization_score(color_groups[c][0]))
        initial_daily_sequence = [item for color in sorted_colors for item in color_groups[color]]
        schedule.append({'day': day_number, 'items': initial_daily_sequence})
        
        ids_to_remove = {item['id_tarefa'] for item in to_remove}
        remaining_items = [item for item in remaining_items if item['id_tarefa'] not in ids_to_remove]
        day_number += 1
        
    return schedule, rejected_tasks

def tabu_search_optimizer(daily_sequence, config, initial_item=None):
    """Otimiza a sequência de um único dia usando Busca Tabu."""
    current_solution, best_solution = list(daily_sequence), list(daily_sequence)
    best_cost = calculate_cost(best_solution, config['setup_cor'], config['setup_peca'], initial_item)
    tabu_list = []
    for _ in range(config.get('max_iterations', 100)):
        best_neighbor, best_neighbor_cost, best_move = None, float('inf'), None
        for i in range(len(current_solution)):
            for j in range(i + 1, len(current_solution)):
                neighbor = list(current_solution)
                neighbor[i], neighbor[j] = neighbor[j], neighbor[i]
                move = tuple(sorted((i, j)))
                neighbor_cost = calculate_cost(neighbor, config['setup_cor'], config['setup_peca'], initial_item)
                if move not in tabu_list and neighbor_cost < best_neighbor_cost:
                    best_neighbor, best_neighbor_cost, best_move = neighbor, neighbor_cost, move
        if best_neighbor:
            current_solution = best_neighbor
            tabu_list.append(best_move)
            if len(tabu_list) > config.get('tabu_tenure', 7):
                tabu_list.pop(0)
            if best_neighbor_cost < best_cost:
                best_solution, best_cost = best_neighbor, neighbor_cost
    return best_solution

def run_full_optimization(task_list, config):
    """Orquestra o processo completo de otimização."""
    initial_schedule, rejected_tasks = create_initial_schedule(task_list, config['daily_capacity'], config['setup_cor'])
    
    optimized_schedule = []
    last_item = None
    for day_data in initial_schedule:
        refined_seq = tabu_search_optimizer(day_data['items'], config, initial_item=last_item)
        setup_cost = calculate_cost(refined_seq, config['setup_cor'], config['setup_peca'], last_item)
        prod_time = sum(item['Tempo_Calculado_Minutos'] for item in refined_seq)
        optimized_schedule.append({
            'day': day_data['day'], 'items': refined_seq,
            'time_used_minutes': prod_time + setup_cost,
            'setup_cost': setup_cost
        })
        if refined_seq: last_item = refined_seq[-1]
        
    return optimized_schedule, rejected_tasks