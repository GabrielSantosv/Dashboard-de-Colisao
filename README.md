# 📊 Dashboard de Acidentes de Trânsito (PRF)

Este projeto é uma ferramenta de Business Intelligence (BI) e análise exploratória de dados desenvolvida em Python para visualizar e analisar acidentes de trânsito ocorridos em rodovias federais brasileiras, utilizando dados abertos da **Polícia Rodoviária Federal (PRF)**.

O objetivo é fornecer uma visão clara sobre a gravidade, localização, causas principais e tendências temporais dos acidentes, auxiliando na identificação de padrões e pontos críticos.

<img width="1686" height="895" alt="image" src="https://github.com/user-attachments/assets/f624bbd1-af1a-4baf-9694-09a75ef0e18c" />

---

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python 3.x
- **Framework Web/Dashboards:** [Plotly Dash](https://dash.plotly.com/)
- **Visualização de Dados:** Plotly Express & Graph Objects
- **Manipulação de Dados:** Pandas & NumPy
- **Cache:** Flask-Caching (para otimização de performance)
- **Interface:** Dash Bootstrap Components & CSS Customizado

---

## 📂 Estrutura do Projeto

Abaixo está a organização do código para facilitar a navegação e compreensão (útil para desenvolvedores e agentes de IA):

```text
├── app.py                  # Ponto de entrada principal da aplicação.
├── requirements.txt        # Dependências do projeto.
├── assets/                 # Estilos CSS, ícones e imagens.
├── data/
│   └── raw/                # Arquivos CSV brutos (Dataset da PRF).
├── scripts/                # Scripts utilitários (ex: geração de dados demo).
└── src/
    └── traffic_accidents/  # Módulos principais do sistema.
        ├── app.py          # Definição do layout Dash e callbacks (lógica de interface).
        ├── data.py         # Pipeline de ingestão, limpeza e normalização de dados.
        ├── analysis.py     # Lógica matemática e agregações estatísticas.
        └── figures.py      # Funções para geração de gráficos Plotly.
```

---

## 🧠 Guia para IA (Contexto do Código)

Se você é um agente de IA ajudando neste projeto, aqui estão os detalhes cruciais de cada módulo:

### 1. Ingestão e Limpeza (`src/traffic_accidents/data.py`)
- **Normalização:** O script limpa nomes de colunas, remove caracteres especiais e converte tudo para minúsculas com underscores.
- **Uniformização de Dados:** Mapeia diferentes formatos de arquivos da PRF (que mudam de ano para ano) para um esquema unificado (`state`, `city`, `occurred_at`, `severity`, etc.).
- **Deduplicação:** Lida com arquivos agrupados por ocorrência vs. por pessoa.
- **Fallback:** Se os dados brutos estiverem ausentes, o sistema gera automaticamente um conjunto de dados de demonstração (`generate_demo_data`) para garantir que o app funcione.

### 2. Lógica de Negócio (`src/traffic_accidents/analysis.py`)
- Responsável por calcular KPIs (Taxa de fatalidade, proporção de acidentes graves).
- Agrupa dados por período (Madrugada, Manhã, Tarde, Noite), tipo de dia (Fim de semana vs. Útil) e localização.

### 3. Visualização (`src/traffic_accidents/figures.py`)
- Centraliza a criação de gráficos para manter a consistência visual.
- Inclui Mapas de Calor (Heatmaps), Séries Temporais, Gráficos de Rosca e Mapas Geográficos (Scatter Mapbox).
- Utiliza uma paleta de cores institucional e fontes específicas para garantir legibilidade.

### 4. Interface e Interatividade (`src/traffic_accidents/app.py`)
- Define um Dashboard de duas abas: **Visão Geral** e **Análise Detalhada**.
- **Filtros Dinâmicos:** Permite filtrar por Estado, Causa, Gravidade e Período de Tempo.
- **Cache:** Utiliza `SimpleCache` para evitar reprocessamento pesado de dados durante a navegação.

---

## 🚀 Como Executar

### Pré-requisitos
- Python instalado (recomendado >= 3.9)
- Pip (gerenciador de pacotes)

### Passo a Passo

1. **Clonar o repositório:**
   ```bash
   git clone https://github.com/seu-usuario/Dashboard-de-Colisao.git
   cd Dashboard-de-Colisao
   ```

2. **Instalar dependências:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Preparar os Dados:**
   - Coloque os arquivos `.csv` baixados do portal da PRF na pasta `data/raw/`.
   - O sistema reconhece automaticamente arquivos com padrões como `acidentes2026.csv`, `datatran2025.csv`, etc.

4. **Rodar a aplicação:**
   ```bash
   python app.py
   ```

5. **Acessar o Dashboard:**
   Abra o navegador e acesse: `http://127.0.0.1:8050/`

---

## 📈 Funcionalidades Entregues

- **KPIs de Segurança:** Total de acidentes, óbitos, feridos e taxa de gravidade.
- **Tendência Mensal:** Evolução do número de acidentes ao longo do tempo.
- **Top Localidades e Causas:** Rankings das UFs e tipos de acidentes mais frequentes.
- **Perfil Temporal:** Distribuição de acidentes por hora do dia e dia da semana.
- **Mapa Interativo:** Localização geográfica exata dos incidentes (quando coordenadas estão disponíveis).
- **Tabela de Dados:** Visualização bruta dos dados filtrados para conferência.

---

## 🔗 Fonte de Dados
Os dados são extraídos do Portal de Dados Abertos da PRF:
[https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos](https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf)
