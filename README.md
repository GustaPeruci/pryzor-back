# 🎯 Pryzor Back-end - Sistema de Predição de Descontos Steam

**Trabalho de Conclusão de Curso (TCC) - Engenharia de Software**  
**Autor:** Gustavo Peruci  
**Instituição:** [Sua Universidade]  
**Ano:** 2025

---

## 📋 Sobre o Projeto

Sistema backend para predição de descontos em jogos da plataforma Steam, desenvolvido como parte do Trabalho de Conclusão de Curso. Utiliza Machine Learning (Random Forest) com validação temporal para prever se um jogo terá desconto significativo (>20%) nos próximos 30 dias.

### Características Principais:
- ✅ **API RESTful** com FastAPI
- ✅ **Modelo ML v2.0** - RandomForest com validação temporal
- ✅ **Banco de Dados MySQL** para armazenamento de dados históricos
- ✅ **Precision de 90.46%** - alta confiança nas predições
- ✅ **F1-Score de 74.34%** - 30.5% melhor que baseline

---

## 📁 Estrutura do Projeto

```
pryzor-back/
├── 📂 src/                          # Código-fonte da API
│   ├── main.py                      # API FastAPI (endpoints)
│   ├── 📂 api/
│   │   ├── ml_discount_predictor.py # Serviço de predição ML
│   │   └── schemas.py               # Schemas Pydantic
│   └── 📂 database/
│       ├── config.py                # Configuração MySQL
│       └── connection.py            # Gerenciamento de conexões
│
├── 📂 scripts/                      # Scripts de ML/ETL
│   ├── 02_train_model.py            # Treinamento do modelo
│   └── README.md                    # Documentação dos scripts
│
├── 📂 ml_model/                     # Modelos treinados
│   └── discount_predictor.pkl       # Modelo RandomForest v2.0 (26.6 MB)
│
├── 📂 data/                         # Datasets
│   └── data_with_binary_target.csv  # Dataset para treinamento (679k registros)
│
├── 📂 tests/                        # Testes automatizados
│   └── test_ml_service.py           # Testes do serviço ML
│
├── 📂 docs/                         # Documentação do projeto
│   ├── ML_MODEL.md                  # Documentação do modelo ML
│   └── INTEGRATION.md               # Guia de integração
│
├── requirements.txt                 # Dependências Python
├── .env.example                     # Exemplo de variáveis de ambiente
└── README.md                        # Este arquivo
```

---

## 🚀 Como Executar

### 1. Pré-requisitos

- Python 3.8+
- MySQL 8.0+
- pip (gerenciador de pacotes Python)

### 2. Instalação

```bash
# Clone o repositório
git clone [URL_DO_REPOSITORIO]
cd pryzor-back

# Crie um ambiente virtual (recomendado)
python -m venv venv

# Ative o ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instale as dependências
pip install -r requirements.txt
```

### 3. Configuração do Banco de Dados

Crie um arquivo `.env` na raiz do projeto (use `.env.example` como base):

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=sua_senha
DB_NAME=steam_pryzor
```

### 4. Iniciar a API

```bash
# Na pasta pryzor-back/
python src/main.py
```

A API estará disponível em: http://127.0.0.1:8000

**Documentação interativa:** http://127.0.0.1:8000/docs

---

## 📡 Endpoints da API

### Sistema

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/` | Informações da API |
| GET | `/health` | Health check do sistema |
| GET | `/api/stats` | Estatísticas gerais |

### Dados

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/games` | Lista jogos (com paginação e filtros) |
| GET | `/api/games/{appid}` | Detalhes de um jogo específico |

### Machine Learning

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/ml/info` | Informações do modelo ML |
| GET | `/api/ml/health` | Health check do serviço ML |
| GET | `/api/ml/predict/{appid}` | Predição para um jogo |
| POST | `/api/ml/predict/batch` | Predições em lote (até 50 jogos) |

---

## 🧪 Testes

### Executar todos os testes:

```bash
python tests/test_ml_service.py
```

### Teste rápido (sem API):

```bash
# Quando solicitado sobre a API, pressione ENTER para pular
python tests/test_ml_service.py
```

### Teste completo (com API):

```bash
# Terminal 1: Iniciar API
python src/main.py

# Terminal 2: Executar testes
python tests/test_ml_service.py
```

---

## 🤖 Modelo de Machine Learning

### Especificações Técnicas:

- **Algoritmo:** Random Forest Classifier (scikit-learn)
- **Versão:** 2.0
- **Validação:** Temporal split (treino: antes 2020-04-01, teste: depois)
- **Features:** 8 features temporais/contextuais
- **Target:** Binário (terá desconto >20% em 30 dias: Sim/Não)

### Métricas (Conjunto de Teste):

| Métrica | Valor |
|---------|-------|
| **F1-Score** | 74.34% |
| **Precision** | 90.46% |
| **Recall** | 63.09% |
| **Accuracy** | 75.18% |
| **ROC-AUC** | 79.45% |

### Features Utilizadas:

1. `discount_percent` (28.46%) - Desconto atual
2. `month` (27.94%) - Mês do ano
3. `quarter` (19.31%) - Trimestre
4. `is_summer_sale` (7.61%) - Summer Sale (jun/jul)
5. `final_price` (7.25%) - Preço final
6. `is_winter_sale` (6.72%) - Winter Sale (dez/jan)
7. `day_of_week` (2.32%) - Dia da semana
8. `is_weekend` (0.37%) - Final de semana

---

## 📊 Dataset

- **Fonte:** Steam Store API
- **Período:** 2019-2020
- **Total de registros:** 679,998
- **Jogos únicos:** ~1,500
- **Distribuição:** 
  - Classe 0 (sem desconto): 43.02%
  - Classe 1 (com desconto): 56.98%

---

## 🎓 Aspectos Acadêmicos

### Metodologia:

1. **ETL (Extract, Transform, Load)**
   - Coleta de dados via Steam API
   - Limpeza e transformação
   - Armazenamento em MySQL

2. **Feature Engineering**
   - Criação de features temporais
   - Detecção de sazonalidade (Steam Sales)
   - Normalização de dados

3. **Modelagem**
   - Seleção do algoritmo (Random Forest)
   - Validação temporal (evitar data leakage)
   - Otimização de hiperparâmetros

4. **Avaliação**
   - Métricas apropriadas (F1, Precision, Recall)
   - Comparação com baseline
   - Análise de feature importance

### Contribuições:

- ✅ Validação temporal adequada para dados de séries temporais
- ✅ Alta precision (90.46%) para recomendações confiáveis
- ✅ Arquitetura RESTful escalável
- ✅ Documentação completa e código reproduzível

---

## 📚 Documentação Adicional

- **[docs/ML_MODEL.md](docs/ML_MODEL.md)** - Documentação completa do modelo ML
- **[docs/INTEGRATION.md](docs/INTEGRATION.md)** - Guia de integração
- **[scripts/README.md](scripts/README.md)** - Documentação dos scripts

---

## 🛠️ Tecnologias Utilizadas

- **Python 3.8+** - Linguagem de programação
- **FastAPI** - Framework web assíncrono
- **scikit-learn** - Machine Learning
- **pandas** - Manipulação de dados
- **MySQL** - Banco de dados relacional
- **Pydantic** - Validação de dados

---

## 📝 Licença

Este projeto foi desenvolvido para fins acadêmicos como parte do Trabalho de Conclusão de Curso.

---

## 👤 Autor

**Gustavo Peruci**
- GitHub: [@GustaPeruci](https://github.com/GustaPeruci)
- Repositório: [n2_ad](https://github.com/GustaPeruci/n2_ad)

---

## 🙏 Agradecimentos

- Steam API pela disponibilização dos dados
- Orientador(a) do TCC
- Comunidade open-source (scikit-learn, FastAPI, etc.)
