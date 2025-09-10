# dashboard/modules/data_handler.py

import pandas as pd
import streamlit as st 
import numpy as np

# Velocidade padrão da monovia (m/min), usada no cálculo de tempo de produção
VELOCIDADE_MONOVIA = 2.0


def normalize_codigo(codigo):
    """
    Normaliza o código de produto para uma string limpa:
    - Remove valores NaN (retorna None).
    - Converte para string e remove espaços extras.
    - Elimina o sufixo ".0" (comum em planilhas exportadas).
    - Mantém apenas caracteres numéricos.
    """
    if pd.isna(codigo):
        return None
    codigo_str = str(codigo).strip()
    if codigo_str.endswith(".0"):
        codigo_str = codigo_str[:-2]
    return ''.join(filter(str.isdigit, codigo_str))


@st.cache_data
def load_structures_data(path):
    """
    Carrega o arquivo de estruturas de engenharia (CSV) e mantém em cache.
    - Usa encoding 'latin1' para compatibilidade com arquivos exportados.
    - Normaliza os códigos de produto já na leitura.
    - Em caso de erro, exibe mensagem no Streamlit.
    """
    try:
        df = pd.read_csv(path, sep=';', encoding='latin1')
        df['CODIGO_PRODUTO'] = df['CODIGO_PRODUTO'].apply(normalize_codigo)
        return df
    except FileNotFoundError:
        st.error(f"Arquivo de estruturas não encontrado em: {path}. Verifique o caminho no servidor.")
        return None


def prepare_task_list(uploaded_file, df_estruturas):
    """
    Prepara a lista de tarefas de pintura a partir:
    - Do arquivo de pedidos (upload do usuário).
    - Dos dados de estrutura de engenharia (df_estruturas).

    Principais etapas:
    1. Leitura e limpeza dos pedidos.
    2. Normalização de códigos de produto.
    3. Junção com as estruturas de engenharia.
    4. Cálculo da necessidade de produção.
    5. Cálculo do tempo estimado por tarefa.
    6. Retorno da lista de tarefas em formato de dicionários.
    """

    # Se não houver arquivo ou estrutura carregada, retorna lista vazia
    if uploaded_file is None or df_estruturas is None:
        return []

    # Lê o arquivo de pedidos enviado (CSV em bytes)
    df_pedidos = pd.read_csv(uploaded_file, sep=',', encoding='latin1')

    # Conversão e limpeza de colunas numéricas
    cols_numericas = ['Pedidos', 'Estoque']
    for col in cols_numericas:
        df_pedidos[col] = pd.to_numeric(df_pedidos[col], errors='coerce').fillna(0).astype(int)

    # Converte a data de entrega (formato PT-BR: dia/mês/ano)
    df_pedidos['Data_Entrega'] = pd.to_datetime(
        df_pedidos['Data_Entrega'], errors='coerce', dayfirst=True
    )

    # Remove linhas inválidas (sem data de entrega ou sem código de produto)
    df_pedidos.dropna(subset=['Data_Entrega', 'CODIGO_PRODUTO'], inplace=True)

    # --- Normalização dos códigos ---
    df_pedidos['CODIGO_PRODUTO'] = df_pedidos['CODIGO_PRODUTO'].apply(normalize_codigo)
    df_estruturas['CODIGO_PRODUTO'] = df_estruturas['CODIGO_PRODUTO'].apply(normalize_codigo)

    # Merge entre pedidos e estruturas (traz descrição, componentes, etc.)
    df_merged = pd.merge(
        df_pedidos, df_estruturas,
        on='CODIGO_PRODUTO', how='left',
        suffixes=('_pedido', '_estrutura')
    )

    lista_tarefas_pintura = []

    # Itera sobre cada pedido para montar as tarefas
    for _, item in df_merged.iterrows():
        necessidade = item['Pedidos'] - item['Estoque']  # cálculo da necessidade real

        # Só gera tarefa se houver necessidade e componente válido
        if necessidade > 0 and pd.notna(item.get('CODIGO_COMPONENTE')):

            # --- Tratamento de valores individuais da estrutura ---
            # Peças por gancheira
            raw_pecas_g = item.get('Peças p/ gancheira')
            numeric_pecas_g = pd.to_numeric(raw_pecas_g, errors='coerce')
            pecas_g = 1 if pd.isna(numeric_pecas_g) or numeric_pecas_g == 0 else int(numeric_pecas_g)

            # Estoque de gancheiras
            raw_estoque_g = item.get('Estoque Gancheiras')
            numeric_estoque_g = pd.to_numeric(raw_estoque_g, errors='coerce')
            estoque_g = 0 if pd.isna(numeric_estoque_g) else int(numeric_estoque_g)

            # Espaçamento (metros por peça)
            raw_espac = item.get('Espaçamento')
            numeric_espac = pd.to_numeric(raw_espac, errors='coerce')
            espac = 0.5 if pd.isna(numeric_espac) else float(numeric_espac)

            # Cálculo do tempo estimado de produção (em minutos)
            t_calc_min = ((necessidade / pecas_g) * espac) / VELOCIDADE_MONOVIA

            # Monta o dicionário representando a tarefa
            tarefa = {
                'DESCRICAO_PRODUTO': item.get('DESCRICAO_PRODUTO_pedido', 'N/A'),
                'Componente': item.get('Componente', 'N/A'),
                'CODIGO_PRODUTO_FINAL': item['CODIGO_PRODUTO'],  # produto final
                'CODIGO_COMPONENTE': item['CODIGO_COMPONENTE'],
                'CODIGO_PRODUTO': item['CODIGO_COMPONENTE'],  # redundância p/ otimização
                'Tinta': item.get('DESC_COR', 'N/A'),
                'Quantidade_Planejada': necessidade,
                'Estoque': item['Estoque'],
                'Pedidos': item['Pedidos'],
                'Data_de_Entrega': item['Data_Entrega'],
                'Tempo_Calculado_Minutos': t_calc_min,
                'Pecas_por_Gancheira': pecas_g,
                'ESTOQUE_GANCHEIRA': estoque_g,
                'DISTANCIA_M': espac,
                'PECAS_COM_PROCESSO_ADICIONAL': item.get('PECAS_COM_PROCESSO_ADICIONAL', 'Não'),
                'FORNECIMENTO_METALURGIA': item.get('FORNECIMENTO_METALURGIA', float('inf')),
                'CAPACIDADE_GAIOLAS': item.get('CAPACIDADE_GAIOLAS', float('inf'))
            }

            lista_tarefas_pintura.append(tarefa)

    # --- Tratamento final ---
    # Remove duplicatas que podem ser criadas pelo merge
    if lista_tarefas_pintura:
        df_final = pd.DataFrame(lista_tarefas_pintura).drop_duplicates(
            subset=['CODIGO_PRODUTO_FINAL', 'CODIGO_COMPONENTE', 'Componente', 'Tinta']
        )
        # Retorna lista de dicionários (formato fácil de manipular em Streamlit)
        return df_final.to_dict('records')

    # Caso não haja tarefas válidas
    return []
