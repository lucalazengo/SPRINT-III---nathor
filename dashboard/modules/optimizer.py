# app/modules/optimizer.py

import pandas as pd
from datetime import datetime, timedelta
import copy
import math

# --- Funções de Lógica e Otimização (Baseadas no seu notebook) ---

def calculate_cost(sequence, setup_cor, setup_peca, initial_item=None):
    """Calcula o custo total de setup (cor e peça) de uma sequência."""
    total_setup_cost = 0
    
    # Adiciona o custo de setup inicial se houver um item do dia anterior
    if initial_item and sequence:
        current_item = initial_item
        next_item = sequence[0]
        if current_item['Tinta'] != next_item['Tinta']:
            total_setup_cost += setup_cor
        if current_item['CODIGO_PRODUTO'] != next_item['CODIGO_PRODUTO']:
            total_setup_cost += setup_peca

    # Calcula os custos de setup internos da sequência
    for i in range(len(sequence) - 1):
        current_item, next_item = sequence[i], sequence[i + 1]
        if current_item['Tinta'] != next_item['Tinta']:
            total_setup_cost += setup_cor
        if current_item['CODIGO_PRODUTO'] != next_item['CODIGO_PRODUTO']:
            total_setup_cost += setup_peca
            
    return total_setup_cost

def calculate_prioritization_score(item):
    """Calcula a pontuação de prioridade para um item."""
    saldo = item['Estoque'] - item['Pedidos']
    due_date = item['Data_de_Entrega']
    prioridade_urgente = 1 if saldo >= 0 else 0
    prioridade_data = due_date.timestamp()
    prioridade_saldo = abs(saldo) if saldo < 0 else 0
    return (prioridade_urgente, prioridade_data, -prioridade_saldo)

def create_initial_schedule(all_items, daily_capacity, setup_cor, setup_peca):
    """Cria a programação inicial usando a heurística de priorização."""
    schedule = []
    rejected_tasks = []
    
    # Filtra tarefas inviáveis
    schedulable_items = []
    for item in all_items:
        item['id_tarefa'] = f"{item['CODIGO_PRODUTO_FINAL']}_{item['CODIGO_COMPONENTE']}_{item['Tinta']}"
        gancheiras_necessarias = math.ceil(item['Quantidade_Planejada'] / item['Pecas_por_Gancheira'])
        if gancheiras_necessarias > item['ESTOQUE_GANCHEIRA']:
            item['Motivo_Rejeicao'] = f"Gancheiras Insuficientes (Necessário: {gancheiras_necessarias}, Disponível: {item['ESTOQUE_GANCHEIRA']})"
            rejected_tasks.append(item)
        else:
            schedulable_items.append(item)

    # Agenda as tarefas viáveis
    day_number = 1
    remaining_items = copy.deepcopy(schedulable_items)
    while remaining_items:
        remaining_items.sort(key=calculate_prioritization_score)
        items_for_today, time_used, to_remove = [], 0, []
        last_color = None
        last_piece_code = None
        
        for item in remaining_items:
            prod_time = item['Tempo_Calculado_Minutos']
            setup_cost_to_add = 0
            if items_for_today:
                if last_color != item['Tinta']:
                    setup_cost_to_add += setup_cor
                if last_piece_code != item['CODIGO_PRODUTO']:
                    setup_cost_to_add += setup_peca

            if time_used + prod_time + setup_cost_to_add <= daily_capacity:
                items_for_today.append(item)
                time_used += prod_time + setup_cost_to_add
                last_color = item['Tinta']
                last_piece_code = item['CODIGO_PRODUTO']
                to_remove.append(item)
                
        if not items_for_today:
            break
            
        # Agrupamento por cor dentro do dia
        color_groups = {}
        for item in items_for_today:
            color = item['Tinta']
            if color not in color_groups:
                color_groups[color] = []
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
    current_solution = list(daily_sequence)
    best_solution = list(daily_sequence)
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
    initial_schedule, rejected_tasks = create_initial_schedule(
        task_list, 
        config['daily_capacity'], 
        config['setup_cor'], 
        config['setup_peca']
    )
    
    optimized_schedule = []
    last_item = None
    for day_data in initial_schedule:
        refined_seq = tabu_search_optimizer(day_data['items'], config, initial_item=last_item)
        setup_cost = calculate_cost(refined_seq, config['setup_cor'], config['setup_peca'], last_item)
        prod_time = sum(item['Tempo_Calculado_Minutos'] for item in refined_seq)
        optimized_schedule.append({
            'day': day_data['day'], 
            'items': refined_seq,
            'time_used_minutes': prod_time + setup_cost,
            'setup_cost': setup_cost
        })
        if refined_seq:
            last_item = refined_seq[-1]
            
    return optimized_schedule, rejected_tasks