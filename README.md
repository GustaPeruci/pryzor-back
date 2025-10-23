# 🔧 Pryzor Backend - API e Machine Learning

> **Parte do TCC de Engenharia de Software**

Aqui fica o coração do Pryzor: a API FastAPI que serve os dados e o modelo de Machine Learning que faz as previsões.

---

## � O que tem aqui?

Este é o backend do projeto. Se você já leu o README principal, sabe que o Pryzor prevê descontos de jogos da Steam. Aqui é onde a mágica acontece:

- 🚀 **API REST** com FastAPI (11 endpoints funcionando)
- 🧠 **Modelo ML v2.0** treinado com Random Forest
- 💾 **Conexão MySQL** com 2.000 jogos e 725k registros de preços
- ✅ **Testes automatizados** para garantir que tudo funciona
- 📚 **Documentação interativa** com Swagger

### Métricas do modelo:
- **Precision:** 90.46% - quando prevê desconto, acerta 9 em 10 vezes
- **F1-Score:** 74.34% - balanço entre acertos e cobertura
- **Recall:** 63.09% - captura 63% dos descontos reais
- **Validação real:** 92.4% de acurácia em 1.000 jogos testados

**📖 Histórico completo:** Veja `ml_model/README.md` para detalhes do modelo v2.0 e `ml_model/experiments_failed/` para análise dos experimentos v2.1 e v3.0 que falharam.

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
│   ├── discount_predictor.pkl       # Modelo v2.0 ATIVO (2.5 MB)
│   ├── README.md                    # Documentação do modelo em produção
│   └── 📂 experiments_failed/       # Experimentos descartados (v2.1, v3.0)
│       ├── discount_predictor_v2_1.pkl
│       ├── 03_train_model_v2_1.py
│       └── README.md                # Por que os experimentos falharam
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

## 🚀 Rodando o Backend

### Antes de começar

Você vai precisar de:
- Python 3.8 ou superior
- MySQL 8.0 rodando
- 5 minutos de paciência 😊

### Passo 1: Ambiente virtual

```bash
# Clone o projeto (se ainda não fez)
cd pryzor-back

# Crie um ambiente virtual
python -m venv venv

# Ative o ambiente
venv\Scripts\activate     # Windows
source venv/bin/activate  # Mac/Linux
```

### Passo 2: Dependências

```bash
pip install -r requirements.txt
```

Isso vai instalar FastAPI, scikit-learn, pandas, MySQL connector e tudo mais que você precisa.

### Passo 3: Configure o banco

Crie um arquivo `.env` na raiz do `pryzor-back/`:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=sua_senha_aqui
DB_NAME=steam_pryzor
```

**Dica:** Use o arquivo `.env.example` como base. Só copiar e preencher com seus dados.

### Passo 4: Rodar a API

```bash
python src/main.py
```

Se tudo deu certo, você vai ver:
```
🚀 Iniciando Pryzor API MySQL Production + ML v2.0...
✅ Modelo ML v2.0 carregado com sucesso!
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**Pronto!** Acesse:
- **API:** http://127.0.0.1:8000
- **Documentação interativa (Swagger):** http://127.0.0.1:8000/docs

---

### 🗄️ Setup do Banco de Dados (Primeira vez)

Se é a primeira vez rodando o projeto, você precisa criar o banco e importar os dados:

#### 1. Criar banco e tabelas (em outro terminal)

```powershell
# PowerShell
Invoke-RestMethod -Uri "http://localhost:8000/api/admin/setup-database" -Method POST
```

```bash
# Bash/Linux
curl -X POST http://localhost:8000/api/admin/setup-database
```

✅ Aguarde a mensagem de sucesso: "Banco de dados criado com sucesso!"

#### 2. Importar dataset completo

⚠️ **IMPORTANTE:** Certifique-se que os arquivos CSV estão na pasta `data/`:
- `data/applicationInformation.csv`
- `data/PriceHistory/*.csv` (vários arquivos)

```powershell
# PowerShell
Invoke-RestMethod -Uri "http://localhost:8000/api/admin/import-dataset" -Method POST
```

```bash
# Bash/Linux
curl -X POST http://localhost:8000/api/admin/import-dataset
```

⏳ **Aguarde 5-10 minutos** - o processo importa ~2000 jogos e ~500k registros de preço

#### 3. Verificar se deu certo

```powershell
# Ver estatísticas do banco
Invoke-RestMethod -Uri "http://localhost:8000/api/stats" -Method GET
```

Você deve ver algo como:
```json
{
  "total_games": 2002,
  "total_price_records": 500000,
  "average_price": 15.99
}
```

✅ **Pronto!** O banco está populado e o sistema está pronto para uso.

---

## 📡 API Endpoints (Todos os 11 endpoints)

### 🏠 Sistema e Health Check

#### **GET /**
**Descrição:** Informações básicas da API  
**Retorna:** Nome, versão, links úteis e endpoints disponíveis  
**Exemplo:** http://127.0.0.1:8000/

#### **GET /health**
**Descrição:** Verifica se tudo está ok  
**Retorna:** Status da API, banco de dados e modelo ML  
**Exemplo:** http://127.0.0.1:8000/health

#### **GET /api/stats**
**Descrição:** Estatísticas gerais do sistema  
**Retorna:** Total de jogos, registros de preços, preço médio, min/max  
**Exemplo:** http://127.0.0.1:8000/api/stats

---

### 🎮 Jogos (Dados)

#### **GET /api/games**
**Descrição:** Lista jogos com paginação e busca  
**Parâmetros:**
- `limit` (int) - quantos jogos retornar (padrão: 50)
- `offset` (int) - paginação (padrão: 0)
- `search` (string) - buscar por nome

**Exemplo:** `/api/games?search=Counter&limit=10`

#### **GET /api/games/{appid}**
**Descrição:** Detalhes completos de um jogo específico  
**Retorna:** Info do jogo + histórico de preços dos últimos 30 dias  
**Exemplo:** `/api/games/730` (Counter-Strike: Global Offensive)

---

### 🧠 Machine Learning (Previsões)

#### **GET /api/ml/info**
**Descrição:** Informações sobre o modelo ML  
**Retorna:** Versão, métricas (F1, Precision, Recall), data de treino, features  
**Exemplo:** `/api/ml/info`

#### **GET /api/ml/health**
**Descrição:** Status do serviço ML  
**Retorna:** Se o modelo está carregado e operacional  
**Exemplo:** `/api/ml/health`

#### **GET /api/ml/predict/{appid}**
**Descrição:** Faz previsão de desconto para um jogo  
**Retorna:**
- `will_have_discount` - se vai ter desconto >20%
- `probability` - probabilidade (0-1)
- `confidence` - confiança na predição
- `recommendation` - "BUY" ou "WAIT"
- `recommendation_text` - texto explicativo
- `reasoning` - fatores que influenciaram

**Exemplo:** `/api/ml/predict/271590` (GTA V)

#### **POST /api/ml/predict/batch**
**Descrição:** Previsão em lote (até 50 jogos)  
**Body:**
```json
{
  "appids": [730, 440, 570]
}
```
**Retorna:** Array com todas as predições

---

### 🔧 Admin (Setup e Importação)

#### **POST /api/admin/setup-database**
**Descrição:** Cria banco de dados e tabelas necessárias  
**Retorna:** Confirmação de criação com detalhes  
**Uso:** Execute este endpoint ANTES de importar dados

**PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/admin/setup-database" -Method POST
```

**Resposta de sucesso:**
```json
{
  "status": "success",
  "message": "Banco de dados criado com sucesso!",
  "details": {
    "database": "steam_pryzor",
    "tables_created": ["games", "price_history"]
  }
}
```

#### **POST /api/admin/import-dataset**
**Descrição:** Importa CSV dataset completo para o banco  
**Requisitos:** 
- Arquivo `data/applicationInformation.csv` presente
- Pasta `data/PriceHistory/` com CSVs de preços
- Banco já criado com `/api/admin/setup-database`

**Retorna:** Estatísticas de importação (jogos importados, registros de preço, etc)

**PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/admin/import-dataset" -Method POST
```

**⚠️ IMPORTANTE:** 
- Este processo pode levar 5-10 minutos
- Importa ~2000 jogos e ~500k registros de preço
- É idempotente (pode executar múltiplas vezes sem duplicar dados)

**Resposta de sucesso:**
```json
{
  "status": "success",
  "message": "Dataset importado com sucesso!",
  "details": {
    "games": {
      "imported": 2002,
      "total_in_db": 2002
    },
    "price_history": {
      "files_processed": 1850,
      "records_imported": 500000,
      "total_in_db": 500000
    }
  }
}
```

---

## 🧪 Testes

Quer ter certeza que tudo funciona? Rode os testes:

```bash
python tests/test_ml_service.py
```

Ele vai testar:
- ✅ Se o modelo ML carrega
- ✅ Se as predições funcionam
- ✅ Se os endpoints respondem corretamente
- ✅ Casos especiais (jogos free-to-play, jogos inexistentes, etc)

Se quiser testar só o modelo sem rodar a API, é só apertar ENTER quando perguntar.

---

## 🧠 Sobre o Modelo de Machine Learning

### O básico

- **Algoritmo:** Random Forest (100 árvores de decisão)
- **Objetivo:** Prever se um jogo vai ter desconto >20% nos próximos 30 dias
- **Como foi treinado:** Com dados de 2019-2020, usando validação temporal

### Por que "validação temporal"?

Porque treinar um modelo de séries temporais com dados embaralhados (random split) é uma armadilha clássica. O modelo "vê o futuro" e as métricas ficam irreais.

A gente fez certo: treinou com dados até 2020-04-01 e testou com dados depois dessa data. Ou seja, o modelo não teve acesso aos dados do futuro durante o treino.

### Métricas reais

| Métrica | Valor | O que significa na prática |
|---------|-------|----------------------------|
| **Precision** | 90.46% | Quando diz "vai ter desconto", acerta 9 em 10 vezes |
| **F1-Score** | 74.34% | Balanço geral entre acertos e cobertura |
| **Recall** | 63.09% | Pega 63% de todos os descontos que realmente acontecem |
| **Accuracy** | 75.18% | Taxa geral de acerto |
| **ROC-AUC** | 79.45% | Capacidade de separar as classes |

**Por que Precision alta e Recall moderado?**  
É uma escolha. Preferimos ser conservadores - quando dizemos "vai ter desconto", você pode confiar. O trade-off é que perdemos alguns descontos (37% deles), mas os que pegamos são confiáveis.

### Features que o modelo usa

Todas as features são baseadas em data e preço. Nada de "colar" com dados futuros:

1. **discount_percent** (28.46%) - Desconto atual do jogo
2. **month** (27.94%) - Mês do ano (sazonalidade importa!)
3. **quarter** (19.31%) - Trimestre
4. **is_summer_sale** (7.61%) - Se está na Summer Sale (junho/julho)
5. **final_price** (7.25%) - Preço atual
6. **is_winter_sale** (6.72%) - Se está na Winter Sale (dezembro/janeiro)
7. **day_of_week** (2.32%) - Dia da semana
8. **is_weekend** (0.37%) - Se é fim de semana

Os números entre parênteses são a importância de cada feature (quanto mais alto, mais importante para o modelo).

---

## 📊 Dados no Banco

- **Jogos:** 2.000 jogos da Steam
- **Registros de preço:** 725.268 linhas de histórico
- **Período:** 2019-2020 (dados históricos)
- **Distribuição:** 56.98% com desconto, 43.02% sem desconto

### Por que dados de 2019-2020?

É o dataset que tínhamos disponível. O foco do TCC é demonstrar a **metodologia completa** (ETL, feature engineering, validação temporal, API, etc), não necessariamente ter dados super atualizados.

Em produção, o pipeline seria adaptado para pegar dados atualizados da Steam API regularmente.

---

## 📁 Estrutura das Pastas

Se você está navegando no código, aqui está o que cada pasta faz:

```
pryzor-back/
├── src/
│   ├── main.py                      # Coração da API (FastAPI)
│   ├── api/
│   │   ├── ml_discount_predictor.py # Serviço que usa o modelo ML
│   │   └── schemas.py               # Validação de dados (Pydantic)
│   └── database/
│       ├── config.py                # Configurações do MySQL
│       └── connection.py            # Gerencia conexões com o banco
│
├── scripts/
│   └── 02_train_model.py            # Script que treinou o modelo v2.0
│
├── ml_model/
│   └── discount_predictor.pkl       # Modelo treinado (26.6 MB)
│
├── data/
│   └── data_with_binary_target.csv  # Dataset usado no treino (679k linhas)
│
└── tests/
    └── test_ml_service.py           # Testes automatizados
```

---

## 🛠️ Tecnologias

O backend usa:

- **Python 3.11** - Linguagem base
- **FastAPI** - Framework web (assíncrono e rápido)
- **Uvicorn** - Servidor ASGI
- **scikit-learn** - Machine Learning (Random Forest)
- **pandas** - Manipulação de dados
- **mysql-connector-python** - Conexão com MySQL
- **Pydantic** - Validação de dados
- **pickle** - Serialização do modelo

Tudo listado no `requirements.txt`.

---

## � Como Interpretar as Respostas da API

### Resposta de Predição

Quando você consulta `/api/ml/predict/{appid}`, recebe algo assim:

```json
{
  "appid": 271590,
  "game_name": "Grand Theft Auto V",
  "will_have_discount": true,
  "probability": 0.78,
  "confidence": 0.56,
  "current_discount": 0,
  "current_price": 29.99,
  "recommendation": "AGUARDAR - Alta probabilidade de desconto melhor",
  "reasoning": [],
  "model_version": "2.0"
}
```

**O que cada campo significa:**

- **will_have_discount**: `true` = modelo prevê desconto >20% nos próximos 30 dias
- **probability**: 0.78 = 78% de chance (quanto maior, mais provável)
- **confidence**: 0.56 = quão "seguro" o modelo está (distância de 0.5 = incerteza)
- **recommendation**: texto amigável para mostrar ao usuário

### Como interpretar?

**Probabilidade:**
- **> 70%** - Alta chance → "Vale esperar"
- **50-70%** - Moderada → "Considere esperar"
- **< 50%** - Baixa → "Se tá bom, compra"

**Confiança:**
- **> 0.7** - Modelo muito confiante
- **0.4-0.7** - Confiança moderada
- **< 0.4** - Modelo meio em dúvida

**Recomendações possíveis:**
- `"AGUARDAR"` - Espera aí que vem desconto
- `"CONSIDERAR AGUARDAR"` - Pode esperar, mas não garanto
- `"COMPRAR AGORA"` - Desconto atual tá ótimo
- `"COMPRAR SE QUISER"` - Pouca chance de melhorar

### Casos especiais

**Jogo free-to-play:**
```json
{
  "will_have_discount": false,
  "probability": 0.0,
  "confidence": 1.0,
  "recommendation": "Jogo gratuito - sem necessidade de esperar"
}
```

**Jogo não encontrado:**
```json
{
  "error": "Jogo não encontrado",
  "appid": 999999
}
```

**Histórico insuficiente:**
```json
{
  "error": "Histórico de preços insuficiente",
  "min_required": 30,
  "found": 10
}
```

---

## 🎓 Para o TCC

Pontos que vale destacar na apresentação:

✅ **Validação temporal correta** - Evitamos data leakage, uma armadilha comum  
✅ **Pipeline completo** - ETL → Feature Engineering → Treino → Validação → API  
✅ **Código limpo** - Estrutura organizada, comentários, testes  
✅ **API funcional** - 11 endpoints testados, documentação Swagger  
✅ **Precision alta (90%)** - Sistema confiável para o usuário  

---

## 🤝 Contribuindo

Se você encontrar bugs ou tiver sugestões, fique à vontade para:
- Abrir uma issue
- Enviar um pull request
- Entrar em contato

---

## 👤 Autor

**Gustavo Peruci**  
🎓 TCC - Engenharia de Software - 2025  
🔗 [GitHub](https://github.com/GustaPeruci)

---

**Dúvidas?** Leia o README principal do projeto na raiz (`../README.md`).
