# ==============================================================================
# MÓDULO DE AUTOMAÇÃO PARA CRIAÇÃO DO DATASET CONSOLIDADO
# ==============================================================================
#
# Objetivo:
# Este script consolida todo o processo de engenharia de dados para criar
# o dataset 'Planilha_Estruturas - Produto_Cor_Dim'. Ele realiza as seguintes
# etapas de forma automatizada:
#
# 1.  Configuração do Ambiente: Importa bibliotecas e define os caminhos
#     dos diretórios de dados.
# 2.  Carregamento dos Dados Brutos: Lê os arquivos CSV de entrada.
# 3.  Processamento do Dicionário de Cores: Padroniza e limpa as informações
#     de cores.
# 4.  Extração de Cores da Estrutura: Mapeia as descrições de pintura para
#     cores padronizadas.
# 5.  Junção de Dados: Enriquece a base principal com códigos de cores e
#     dados técnicos dos componentes.
# 6.  Limpeza Final: Corrige e converte os tipos de dados para garantir
#     consistência.
# 7.  Adição de Atributos Simulados: Inclui novas colunas para futuras análises.
# 8.  Exportação: Salva o dataset final e consolidado nos formatos CSV e Excel.
#
# Para executar, certifique-se de que os arquivos de dados brutos estejam na
# pasta '../data/raw'.
#
# ==============================================================================

# --- CÉLULA 1: CONFIGURAÇÃO DO AMBIENTE E DEFINIÇÃO DE CAMINHOS ---

import sys
import os
import pandas as pd
import numpy as np
import re

print(">>> Iniciando o processo de automação...")
print("-" * 50)

# Definição dos Caminhos Principais
print("1. Configurando o ambiente e definindo os caminhos...")
BASE_DIR = './data'
RAW_DATA_PATH = os.path.join(BASE_DIR, 'raw')
PROCESSED_DATA_PATH = os.path.join(BASE_DIR, 'processed')

# Criação do Diretório de Saída, se não existir
os.makedirs(PROCESSED_DATA_PATH, exist_ok=True)

print(f"Diretório de dados brutos: {RAW_DATA_PATH}")
print(f"Diretório de dados processados: {PROCESSED_DATA_PATH}")
print("Configuração concluída com sucesso.")
print("-" * 50)

# --- CÉLULA 2: CARREGAMENTO DOS DADOS BRUTOS ---

print("2. Carregando os dados brutos...")
try:
    file_path_cores = os.path.join(RAW_DATA_PATH, '2025-06-13 - Dicionário cores.csv')
    df_cores_raw = pd.read_csv(file_path_cores, sep=';', encoding='utf-8')
    print("   - Arquivo 'Dicionário cores.csv' carregado.")

    file_path_estruturas = os.path.join(RAW_DATA_PATH, '2025-06-13 - Estruturas - Produto x Tinta Pó - atualizado.csv')
    df_estruturas_raw = pd.read_csv(file_path_estruturas, sep=';', encoding='utf-8')
    print("   - Arquivo 'Estruturas - Produto x Tinta Pó.csv' carregado.")

    file_path_gancheiras = os.path.join(RAW_DATA_PATH, 'dados.csv')
    df_gancheiras_raw = pd.read_csv(file_path_gancheiras, sep=';', encoding='utf-8')
    print("   - Arquivo 'dados.csv' (gancheiras) carregado.")
    print("Carregamento de dados brutos concluído.")
    print("-" * 50)

except FileNotFoundError as e:
    print(f"ERRO: Arquivo não encontrado. Verifique o caminho: {e.filename}")
    sys.exit() # Interrompe a execução se um arquivo não for encontrado

# --- CÉLULA 3: PROCESSAMENTO - CRIAÇÃO DO DICIONÁRIO DE CORES PADRONIZADO ---

print("3. Processando e padronizando o dicionário de cores...")

def limpar_e_unificar_apelidos(lista_apelidos):
    apelidos_unicos = set()
    for apelido in lista_apelidos:
        apelido_limpo = str(apelido).lower().strip().rstrip(',')
        if apelido_limpo:
            apelidos_unicos.add(apelido_limpo)
    return sorted(list(apelidos_unicos))

df_consolidado = df_cores_raw.groupby('CODIGO_COMPONENTE').agg(
    VARIACOES_APELIDO=('COR_APELIDO', list),
    DESCRICAO_COR=('DESCRICAO_COMPONENTE', 'first')
).reset_index()

df_consolidado['VARIACOES_APELIDO'] = df_consolidado['VARIACOES_APELIDO'].apply(limpar_e_unificar_apelidos)

prefixos_remover = ['TINTA POLIESTER', 'TINTA POLIEST', 'TINTA EM PO', 'TINTA HIBRID']
regex_prefixos = r'^(' + '|'.join(prefixos_remover) + ')'
df_consolidado['DESC_COR'] = df_consolidado['DESCRICAO_COR'].str.replace(
    regex_prefixos, '', regex=True, flags=re.IGNORECASE
).str.strip().str.lower()

df_consolidado = df_consolidado.rename(columns={'CODIGO_COMPONENTE': 'CODIGO_COR'})
df_cores_processed = df_consolidado[['CODIGO_COR', 'DESCRICAO_COR', 'DESC_COR', 'VARIACOES_APELIDO']]

print("Dicionário de cores processado com sucesso.")
print("-" * 50)

# --- CÉLULA 4: PROCESSAMENTO - EXTRAÇÃO DE CORES DA ESTRUTURA DE PRODUTOS ---

print("4. Mapeando e extraindo cores das descrições de pintura...")

MAPA_DE_CORES = [
    (['GRAFITEMETALICOFOSCO'], 'grafite metalico fosco'), (['AZULBRILHANTEFLEX'], 'azul brilhante flex'),
    (['PRETOGRAFITE'], 'tgic free preto grafite'), (['AMARELODOURADO'], 'amarelo dourado'),
    (['ROSAESCURO', 'ROSAESCU'], 'rosa escuro'), (['AZULESCURO'], 'azul escuro'),
    (['ROSACLARO', 'ROSACLAR'], 'rosa claro'), (['AZULCLARO', 'AZULCLARINHO'], 'azul claro'),
    (['ROSAMETALICO', 'ROSAMETALI'], 'rosa metalico aro 26'), (['PRETOFOSCO'], 'preto fosco'),
    (['ROSACHICLETE', 'ROSACHICL'], 'rosa chiclete'), (['CORALPINK', 'CORALPI'], 'coral pink'),
    (['AZULBEBE'], 'tgic free azul bebe'), (['ROSABEBE'], 'tgic free rosa bebe'),
    (['ROSAPEROL'], 'tgic free rosa perolizado'), (['ABRACADEIRASELIM16/BALANCE'], 'preta'),
    (['AZULFLEX'], 'tgic free azul flex'), (['LILAS-BANDEIRANTE', 'LILASBANDEIRANTE'], 'lilas - bandeirantes'),
    (['VERDEAQ', 'VERDEAQUA'], 'verde'), (['GRAFITE'], 'grafite metalico fosco'),
    (['BRANCO', 'BRANCA'], 'branca'), (['VERMELHO'], 'vermelho'), (['CINZA'], 'cinza'),
    (['LILAS'], 'lilas - bandeirantes'), (['ROSA'], 'rosa metalico aro 26'), (['VERDE'], 'verde'),
    (['COBRE'], 'preto fosco'), (['AMARELO'], 'amarelo dourado'), (['PRETO'], 'preta'),
    (['PRATA'], 'tgic free prata'), (['LARANJA'], 'laranja fosco')
]

def mapear_e_extrair_cor(descricao):
    if not isinstance(descricao, str) or not descricao.upper().startswith('PINTURA'):
        return np.nan
    descricao_limpa = re.sub(r'[\s-]', '', descricao.upper())
    for variacoes, cor_final in MAPA_DE_CORES:
        for variacao in variacoes:
            if variacao in descricao_limpa:
                return cor_final
    return 'nao_mapeado'

df_estruturas_processed = df_estruturas_raw.copy()
df_estruturas_processed['DESC_COR'] = df_estruturas_processed['DESCRICAO_COMPONENTE'].apply(mapear_e_extrair_cor)

# Validação do mapeamento
pintura_rows = df_estruturas_processed['DESCRICAO_COMPONENTE'].str.upper().str.startswith('PINTURA', na=False)
falhas = df_estruturas_processed[pintura_rows & (df_estruturas_processed['DESC_COR'] == 'nao_mapeado')]
total_falhas = len(falhas)
print(f"Mapeamento de cores concluído. Total de falhas: {total_falhas}")
if total_falhas > 0:
    print("   - ATENÇÃO: Algumas descrições de pintura não foram mapeadas e serão ignoradas nas junções.")

df_estruturas_processed['DESC_COR'].replace('nao_mapeado', np.nan, inplace=True)
print("-" * 50)

# --- CÉLULA 5: JUNÇÃO (MERGE) - VINCULANDO CÓDIGOS DE COR À ESTRUTURA ---

print("5. Vinculando códigos de cor à estrutura de produtos...")
df_cores_lookup = df_cores_processed[['DESC_COR', 'CODIGO_COR', 'DESCRICAO_COR']].drop_duplicates(subset=['DESC_COR'])

df_merged_cores = pd.merge(
    df_estruturas_processed,
    df_cores_lookup,
    on='DESC_COR',
    how='left'
)
print("Junção com dicionário de cores concluída.")
print("-" * 50)

# --- CÉLULA 6: JUNÇÃO (MERGE) - ADICIONANDO DADOS DE GANCHEIRAS ---

print("6. Adicionando dados técnicos de componentes (gancheiras)...")
df_com_gancheiras = df_merged_cores.rename(columns={'PINTURA_ITEM': 'Componente'})

df_gancheiras_clean = df_gancheiras_raw.rename(columns={
    'PeÃ§as p/ gancheira': 'Pecas_p_gancheira', 'PINOS ': 'PINOS', 'Peso (kg)': 'Peso_kg'
})

df_gancheiras_lookup = df_gancheiras_clean.drop_duplicates(subset=['Componente'])

df_final = pd.merge(
    df_com_gancheiras,
    df_gancheiras_lookup,
    on='Componente',
    how='left'
)
print("Junção com dados de gancheiras concluída.")
print("-" * 50)

# --- CÉLULA 7: LIMPEZA E CONVERSÃO FINAL DOS TIPOS DE DADOS ---

print("7. Limpando e convertendo os tipos de dados finais...")
df_cleaned = df_final.copy()

colunas_para_float = ['Espaçamento', 'Peso_kg', 'Altura', 'Largura']
for col in colunas_para_float:
    if col in df_cleaned.columns:
        extracted_series = df_cleaned[col].astype(str).str.extract(r'(\d+[.,]?\d*)', expand=False)
        cleaned_series = extracted_series.str.replace(',', '.', regex=False)
        df_cleaned[col] = pd.to_numeric(cleaned_series, errors='coerce')

colunas_para_int = [
    'CODIGO_PRODUTO', 'CODIGO_COMPONENTE', 'CODIGO_COR',
    'Pecas_p_gancheira', 'PINOS', 'Estoque Gancheiras'
]
for col in colunas_para_int:
     if col in df_cleaned.columns:
        # Renomeia a coluna problemática se ela existir
        if 'Peças p/ gancheira' in df_cleaned.columns and col == 'Pecas_p_gancheira':
            df_cleaned.rename(columns={'Peças p/ gancheira': 'Pecas_p_gancheira_temp'}, inplace=True)
            col = 'Pecas_p_gancheira_temp'

        df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce').astype('Int64')

# Renomeia de volta para o nome original, se a coluna existir
if 'Pecas_p_gancheira_temp' in df_cleaned.columns:
    df_cleaned.rename(columns={'Pecas_p_gancheira_temp': 'Peças p/ gancheira'}, inplace=True)


print("Limpeza de tipos de dados concluída.")
print("-" * 50)


# --- CÉLULA 8: SIMULAÇÃO DE NOVOS ATRIBUTOS ---

print("8. Adicionando colunas simuladas para análise futura...")
num_rows = len(df_cleaned)

# Adiciona 'PECAS_COM_PROCESSO_ADICIONAL'
df_cleaned['PECAS_COM_PROCESSO_ADICIONAL'] = np.random.choice(
    ['Sim', 'Não'], size=num_rows, p=[0.2, 0.8]
)

# Adiciona 'FORNECIMENTO_METALURGIA'
df_cleaned['FORNECIMENTO_METALURGIA'] = np.random.randint(500, 2501, size=num_rows)

# Adiciona 'CAPACIDADE_GAIOLAS'
df_cleaned['CAPACIDADE_GAIOLAS'] = np.random.randint(1000, 4001, size=num_rows)

print("Novas colunas adicionadas com sucesso.")
print("-" * 50)

# --- CÉLULA 9: EXPORTAÇÃO DO DATASET FINAL CONSOLIDADO ---

print("9. Exportando o dataset final consolidado...")
output_filename = 'Planilha_Estruturas - Produto_Cor_Dim'
output_path_csv = os.path.join(PROCESSED_DATA_PATH, f'{output_filename}.csv')
output_path_xlsx = os.path.join(PROCESSED_DATA_PATH, f'{output_filename}.xlsx')

# Exportando os arquivos
df_cleaned.to_csv(output_path_csv, index=False, sep=';', encoding='ISO-8859-1')
df_cleaned.to_excel(output_path_xlsx, index=False)

print("\n" + "="*50)
print("PROCESSO CONCLUÍDO COM SUCESSO!")
print("O dataset final consolidado foi salvo em:")
print(f"   - CSV: {output_path_csv}")
print(f"   - Excel: {output_path_xlsx}")
print("="*50)