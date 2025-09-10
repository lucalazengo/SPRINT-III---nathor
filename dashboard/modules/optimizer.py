# app/modules/optimizer.py

import pandas as pd
from datetime import datetime, timedelta
import copy
import math

# --- PARÂMETROS GLOBAIS (APENAS CONSTANTES TÉCNICAS) ---
MONOVIA_LENGHT_METERS = 168

# --- FUNÇÕES DE LÓGICA E OTIMIZAÇÃO (VERSÃO FINAL COM HORIZONTE DE PLANEJAMENTO) ---

def preprocessar_pedidos(lista_de_pedidos):
    """Aplica regras de negócio (antecipação) lidas dos próprios dados."""
    pedidos_ajustados = copy.deepcopy(lista_de_pedidos)
    DIAS_ANTECIPACAO = 2
    for item in pedidos_ajustados:
        if item.get('PECAS_COM_PROCESSO_ADICIONAL') == 'Sim':
            item['Data_de_Entrega'] -= timedelta(days=DIAS_ANTECIPACAO)
            item['Observacao'] = f'Entrega antecipada em {DIAS_ANTECIPACAO} dias'
    return pedidos_ajustados

def calculate_cost(sequence, setup_cor, setup_peca, initial_item=None):
    """Calcula o custo total de setup de uma sequência."""
    total_setup_cost = 0
    if not sequence: return 0
    if initial_item:
        if initial_item['Tinta'] != sequence[0]['Tinta']: total_setup_cost += setup_cor
        if initial_item['CODIGO_PRODUTO'] != sequence[0]['CODIGO_PRODUTO']: total_setup_cost += setup_peca
    for i in range(len(sequence) - 1):
        if sequence[i]['Tinta'] != sequence[i+1]['Tinta']: total_setup_cost += setup_cor
        if sequence[i]['CODIGO_PRODUTO'] != sequence[i+1]['CODIGO_PRODUTO']: total_setup_cost += setup_peca
    return total_setup_cost

def calculate_prioritization_score(item):
    """Calcula a pontuação de prioridade para um item."""
    saldo = item['Estoque'] - item['Pedidos']
    due_date = item['Data_de_Entrega']
    return (1 if saldo >= 0 else 0, due_date.timestamp(), -abs(saldo) if saldo < 0 else 0)

def create_initial_schedule(unscheduled_items, config):
    """
    ESTÁGIO 1: Planeja a produção diária com um 'Horizonte de Planejamento'.
    """
    schedule, permanently_rejected = [], []
    plannable_items = []

    # FILTRO 1 (PERMANENTE): Restrição de Gancheiras
    for item in unscheduled_items:
        item['id_tarefa'] = f"{item['CODIGO_PRODUTO_FINAL']}_{item['CODIGO_COMPONENTE']}_{item['Tinta']}"
        gancheiras_necessarias = math.ceil(item['Quantidade_Planejada'] / item['Pecas_por_Gancheira'])
        comprimento_na_monovia = gancheiras_necessarias * item['DISTANCIA_M']
        falta_gancheiras = gancheiras_necessarias > item['ESTOQUE_GANCHEIRA']
        reutilizacao_nao_ocorre = comprimento_na_monovia <= MONOVIA_LENGHT_METERS
        if falta_gancheiras and reutilizacao_nao_ocorre:
            item['Motivo_Rejeicao'] = f"Gancheiras Insuficientes ({gancheiras_necessarias} > {item['ESTOQUE_GANCHEIRA']}) e Monovia Curta"
            permanently_rejected.append(item)
        else:
            plannable_items.append(item)

    day_number = 1
    # Simula a data de início do planejamento como sendo a data atual
    current_planning_date = datetime.now()
    
    while plannable_items:
        # --- LÓGICA DO HORIZONTE DE PLANEJAMENTO ---
        horizonte_dias = config.get('horizonte_dias', 7) # Pega o valor do config, com 7 como padrão
        data_limite = current_planning_date + timedelta(days=horizonte_dias)

        # Filtra apenas os itens dentro do horizonte de planejamento
        itens_no_horizonte = [item for item in plannable_items if item['Data_de_Entrega'] <= data_limite]
        
        # Fallback: Se não houver itens no horizonte, pega o mais urgente de todos para não parar a produção.
        if not itens_no_horizonte and plannable_items:
            plannable_items.sort(key=calculate_prioritization_score)
            itens_no_horizonte = plannable_items
        
        # A priorização agora acontece apenas nos itens dentro do horizonte
        itens_no_horizonte.sort(key=calculate_prioritization_score)
        
        # --- FIM DA LÓGICA DO HORIZONTE ---

        consumo_metalurgia_diario, consumo_gaiolas_diario = {}, {}
        items_for_today, items_not_today = [], []
        time_used_today, last_color, last_piece_code = 0, None, None

        for item in itens_no_horizonte:
            cod_produto, qtd_planejada = item['CODIGO_PRODUTO'], item['Quantidade_Planejada']
            motivo_falha_diaria = None

            # FILTROS DIÁRIOS (Metalurgia, Gaiolas, Tempo)
            fornecimento_max = item.get('FORNECIMENTO_METALURGIA', float('inf'))
            consumo_metalurgia_diario.setdefault(cod_produto, 0)
            if consumo_metalurgia_diario[cod_produto] + qtd_planejada > fornecimento_max:
                motivo_falha_diaria = f"Excede Fornecimento Metalurgia (Max: {fornecimento_max})"
            
            if not motivo_falha_diaria:
                capacidade_max = item.get('CAPACIDADE_GAIOLAS', float('inf'))
                consumo_gaiolas_diario.setdefault(cod_produto, 0)
                if consumo_gaiolas_diario[cod_produto] + qtd_planejada > capacidade_max:
                    motivo_falha_diaria = f"Excede Capacidade Gaiolas (Max: {capacidade_max})"

            if not motivo_falha_diaria:
                item_time = item['Tempo_Calculado_Minutos']
                setup_cost = 0
                if items_for_today:
                    if last_color != item['Tinta']: setup_cost += config['setup_cor']
                    if last_piece_code != cod_produto: setup_cost += config['setup_peca']
                if time_used_today + item_time + setup_cost > config['daily_capacity']:
                    motivo_falha_diaria = "Excede Tempo de Produção do Dia"

            if motivo_falha_diaria is None:
                items_for_today.append(item)
                time_used_today += item_time + setup_cost
                if cod_produto in consumo_metalurgia_diario: consumo_metalurgia_diario[cod_produto] += qtd_planejada
                if cod_produto in consumo_gaiolas_diario: consumo_gaiolas_diario[cod_produto] += qtd_planejada
                last_color, last_piece_code = item['Tinta'], cod_produto
            else:
                item['Motivo_Rejeicao_Temporario'] = motivo_falha_diaria
                items_not_today.append(item)
        
        # Itens que sobraram para os próximos dias
        ids_agendados = {item['id_tarefa'] for item in items_for_today}
        plannable_items = [item for item in plannable_items if item['id_tarefa'] not in ids_agendados]

        if not items_for_today and plannable_items:
            item_rejeitado = plannable_items[0]
            item_rejeitado['Motivo_Rejeicao'] = item_rejeitado.get('Motivo_Rejeicao_Temporario', "Não coube no cronograma (gargalo de capacidade)")
            permanently_rejected.append(item_rejeitado)
            plannable_items.pop(0)
            continue

        if not items_for_today and not plannable_items:
            break

        schedule.append({'day': day_number, 'items': items_for_today})
        day_number += 1
        current_planning_date += timedelta(days=1)
        
    for item in plannable_items:
        item['Motivo_Rejeicao'] = "Não coube no cronograma (sem capacidade futura)"
        permanently_rejected.append(item)
        
    return schedule, permanently_rejected

def tabu_search_optimizer(daily_sequence, config, initial_item=None):
    """ESTÁGIO 2: Otimiza a sequência de um único dia."""
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
                if move in tabu_list: continue
                neighbor_cost = calculate_cost(neighbor, config['setup_cor'], config['setup_peca'], initial_item)
                if neighbor_cost < best_neighbor_cost:
                    best_neighbor, best_neighbor_cost, best_move = neighbor, neighbor_cost, move
        if best_neighbor:
            current_solution = best_neighbor
            tabu_list.append(best_move)
            if len(tabu_list) > config.get('tabu_tenure', 7): tabu_list.pop(0)
            if best_neighbor_cost < best_cost: best_solution, best_cost = best_neighbor, neighbor_cost
    return best_solution

def run_full_optimization(task_list, config):
    """Orquestra o processo completo de otimização."""
    pedidos_prontos = preprocessar_pedidos(task_list)
    initial_schedule, rejected_tasks = create_initial_schedule(pedidos_prontos, config)
    
    optimized_schedule = []
    last_item = None
    for day_data in initial_schedule:
        refined_seq = tabu_search_optimizer(day_data['items'], config, initial_item=last_item)
        setup_cost = calculate_cost(refined_seq, config['setup_cor'], config['setup_peca'], last_item)
        prod_time = sum(item['Tempo_Calculado_Minutos'] for item in refined_seq)
        optimized_schedule.append({
            'day': day_data['day'], 'items': refined_seq,
            'time_used_minutes': prod_time + setup_cost, 'setup_cost': setup_cost
        })
        if refined_seq: last_item = refined_seq[-1]
            
    return optimized_schedule, rejected_tasks