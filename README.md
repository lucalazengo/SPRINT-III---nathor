# Otimizador de Pintura Nathor | PCP Inteligente

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red.svg)
![Pandas](https://img.shields.io/badge/Pandas-2.0+-green.svg)

Este repositório contém o código-fonte da solução "PCP Inteligente", uma aplicação de software desenvolvida para otimizar o sequenciamento da produção na linha de pintura da Nathor.

## 1. Sobre o Projeto

O sistema utiliza um algoritmo híbrido (heurística + meta-heurística) para gerar um cronograma de produção diário que equilibra as prioridades de negócio (datas de entrega, estoque) com a eficiência operacional (minimização de setups de cor e peça). A solução considera múltiplas restrições do chão de fábrica, como disponibilidade de gancheiras, fornecimento da metalurgia e capacidade de armazenamento, para gerar planos realistas e acionáveis.

O projeto é dividido em duas partes principais:
* **Pipelines de Engenharia de Dados:** Scripts autônomos para consolidar e limpar os dados de entrada.
* **Aplicação de Planejamento (Dashboard):** Uma interface web interativa em Streamlit para que a equipe de PCP possa executar simulações, calibrar parâmetros e analisar os resultados.

## 2. Estrutura do Projeto

A estrutura de diretórios foi organizada para separar dados, lógica e interface:

/
├── dashboard/      # Código da aplicação Streamlit
│   ├── app.py      # Ponto de entrada principal da aplicação
│   ├── pages/      # Páginas da aplicação (Planejamento, Acompanhamento)
│   └── modules/    # Módulos de lógica (optimizer, data_handler, pipelines)
├── data/
│   ├── raw/        # Local para os arquivos de dados brutos (entrada)
│   └── processed/  # Datasets limpos e consolidados (saída dos pipelines)
└── notebooks/      # Notebooks utilizados para análise e desenvolvimento

## 3. Guia de Instalação e Execução

Siga os passos abaixo para configurar e executar o projeto localmente.

### Passo 1: Pré-requisitos

* Python 3.10 ou superior
* Gerenciador de pacotes `pip`

### Passo 2: Preparação do Ambiente

1.  **Clone o repositório** (se aplicável) ou certifique-se de estar no diretório raiz do projeto (`SPRINT III - nathor`).

2.  **Crie e ative um ambiente virtual:**
    ```bash
    # Criar o ambiente
    python -m venv .venv

    # Ativar no Linux / macOS
    source .venv/bin/activate

    # Ativar no Windows
    .venv\Scripts\activate
    ```

3.  **Instale as dependências:**
    Crie um arquivo chamado `requirements.txt` na raiz do projeto com o seguinte conteúdo:
    ```
    pandas
    streamlit
    streamlit-option-menu
    openpyxl
    ```
    Em seguida, instale as bibliotecas com o comando:
    ```bash
    pip install -r requirements.txt
    ```

### Passo 3: Configuração dos Dados

1.  Garanta que todos os arquivos de dados brutos listados abaixo estejam presentes no diretório `data/raw/`.
    * `2025-06-13 - Estruturas - Produto x Tinta Pó - atualizado.csv`
    * `2025-06-13 - Dicionário cores.csv`
    * `dados.csv` (informações de gancheiras)
    * `Pedidos.csv`
    * `Saldo.csv`

### Passo 4: Execução dos Pipelines (Opcional)

Se os datasets processados em `data/processed/` precisarem ser gerados ou atualizados, execute os scripts de pipeline a partir da pasta `dashboard/modules/`:
```bash
# Para gerar o arquivo mestre de estruturas
python dashboard/modules/pipeline_dados.py

# Para gerar o arquivo consolidado de pedidos
python dashboard/modules/pedidos.py
Passo 5: Execução da Aplicação Principal
No terminal, certifique-se de estar no diretório dashboard.

Execute o seguinte comando para iniciar a aplicação Streamlit:

streamlit run app.py

4. Arquivos Gerados (Saídas)
A execução dos pipelines e da aplicação irá gerar os seguintes arquivos no diretório data/processed/:

Planilha_Estruturas - Produto_Cor_Dim.csv: O dataset mestre de engenharia, principal fonte de dados para a aplicação.

pedidos_consolidados.csv: O arquivo de pedidos consolidado, usado como entrada na aplicação.

cronograma_dia_X.xlsx / .csv: Os planos de produção detalhados para cada dia, gerados pela aplicação.

relatorio_excecoes.xlsx: Relatório com as ordens que não puderam ser planejadas e os respectivos motivos.

pipeline_log.txt: Log de execução do pipeline de engenharia de dados.

5. Próximos Passos e Recomendações
Qualidade dos Dados: A performance do otimizador depende diretamente da qualidade dos dados brutos. É crucial manter esses arquivos atualizados e consistentes.

Regras de Negócio: Para alterar capacidades de produção (FORNECIMENTO_METALURGIA, CAPACIDADE_GAIOLAS, etc.), a melhor prática é criar e manter um arquivo regras_de_negocio.xlsx em data/processed/, conforme a lógica implementada no pipeline.

Evolução: Para um ambiente de produção contínuo, recomenda-se substituir a leitura de arquivos CSV por conexões diretas ao banco de dados da empresa (ERP).