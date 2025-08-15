# app/modules/data_handler.py

import pandas as pd
import streamlit as st 

VELOCIDADE_MONOVIA = 2.0

@st.cache_data 
def load_structures_data(path):
    """Carrega e cacheia os dados de estruturas de engenharia."""
    try:
        df = pd.read_csv(path, sep=';', encoding='latin1')
        return df
    except FileNotFoundError:
        st.error(f"Arquivo de estruturas não encontrado em: {path}. Verifique o caminho no servidor.")
        return None

def prepare_task_list(uploaded_file, df_estruturas):
    """Lê o arquivo de pedidos, junta com as estruturas e gera a lista de tarefas, com tratamento de dados robusto."""
    if uploaded_file is None or df_estruturas is None:
        return []

    df_pedidos = pd.read_csv(uploaded_file, sep=',', encoding='latin1')

    # Limpeza e preparação dos dados de pedidos
    cols_numericas = ['Pedidos', 'Estoque']
    for col in cols_numericas:
        df_pedidos[col] = pd.to_numeric(df_pedidos[col], errors='coerce').fillna(0).astype(int)
    df_pedidos['Data_Entrega'] = pd.to_datetime(df_pedidos['Data_Entrega'], errors='coerce', dayfirst=True)
    df_pedidos.dropna(subset=['Data_Entrega', 'CODIGO_PRODUTO'], inplace=True)
    
    lista_tarefas_pintura = []
    for _, pedido in df_pedidos.iterrows():
        necessidade = pedido['Pedidos'] - pedido['Estoque']
        if necessidade > 0:
            componentes = df_estruturas[df_estruturas['CODIGO_PRODUTO'] == pedido['CODIGO_PRODUTO']]
            for _, comp in componentes.iterrows():
                if pd.isna(comp['DESCRICAO_COR']): continue
                
                # Tratamento robusto para valores individuais
                raw_pecas_g = comp.get('Peças p/ gancheira')
                numeric_pecas_g = pd.to_numeric(raw_pecas_g, errors='coerce')
                pecas_g = 1 if pd.isna(numeric_pecas_g) or numeric_pecas_g == 0 else int(numeric_pecas_g)
                
                raw_estoque_g = comp.get('Estoque Gancheiras')
                numeric_estoque_g = pd.to_numeric(raw_estoque_g, errors='coerce')
                estoque_g = 0 if pd.isna(numeric_estoque_g) else int(numeric_estoque_g)

                raw_espac = comp.get('Espaçamento')
                numeric_espac = pd.to_numeric(raw_espac, errors='coerce')
                espac = 0.5 if pd.isna(numeric_espac) else float(numeric_espac)
                
                t_calc_min = ((necessidade / pecas_g) * espac) / VELOCIDADE_MONOVIA

                tarefa = {
                    'DESCRICAO_PRODUTO': pedido.get('DESCRICAO_PRODUTO', 'N/A'),
                    'DESCRICAO_COMPONENTE': comp.get('DESCRICAO_COMPONENTE', 'N/A'),
                    'CODIGO_PRODUTO_FINAL': pedido['CODIGO_PRODUTO'],
                    'CODIGO_COMPONENTE': comp['CODIGO_COMPONENTE'],
                    'Tinta': comp['DESCRICAO_COR'],
                    'Quantidade_Planejada': necessidade,
                    'Saldo': pedido.get('Saldo', 0),
                    'Estoque': pedido['Estoque'],
                    'Pedidos': pedido['Pedidos'],
                    'Data_de_Entrega': pedido['Data_Entrega'],
                    'Tempo_Calculado_Minutos': t_calc_min,
                    'Pecas_por_Gancheira': pecas_g,
                    'Estoque Gancheiras': estoque_g
                }
                lista_tarefas_pintura.append(tarefa)
    return lista_tarefas_pintura