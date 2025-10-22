# 🧹 PLANO DE LIMPEZA E REORGANIZAÇÃO - PRYZOR BACK-END

## 📋 Análise da Estrutura Atual

### Arquivos Identificados:

```
pryzor-back/
├── src/
│   ├── main.py                           ✅ MANTER (API principal)
│   ├── etl_production_railway.py         ❌ REMOVER (não usado)
│   ├── api/
│   │   ├── ml_discount_predictor.py      ✅ MANTER (modelo v2.0 - ATIVO)
│   │   ├── discount_service.py           ❌ REMOVER (modelo antigo)
│   │   ├── ml_service.py                 ❌ REMOVER (modelo antigo)
│   │   ├── services.py                   ❌ REMOVER (usa SQLAlchemy, não MySQL)
│   │   └── schemas.py                    ✅ MANTER (schemas da API)
│   └── database/
│       ├── config.py                     ✅ MANTER
│       ├── connection.py                 ✅ MANTER
│       └── models.py                     ⚠️ REVISAR (usa SQLAlchemy)
│
├── scripts/
│   ├── train_baseline_model.py           ✅ RENOMEAR → train_model.py
│   └── README.md                         ✅ MANTER
│
├── ml_model/
│   └── discount_predictor.pkl            ✅ MANTER (modelo v2.0)
│
├── data/
│   └── data_with_binary_target.csv       ✅ MANTER (dataset treinamento)
│
├── tests/
│   └── (vazio)                           ⚠️ MOVER test_ml_integration.py aqui
│
├── test_ml_integration.py                ✅ MOVER → tests/
├── README_ML_V2.md                       ✅ RENOMEAR → docs/ML_MODEL.md
├── INTEGRATION_SUCCESS.md                ✅ RENOMEAR → docs/INTEGRATION.md
├── requirements.txt                      ✅ MANTER
├── .env.example                          ✅ MANTER
└── Dockerfile                            ⚠️ REVISAR
```

---

## 🎯 Ações de Limpeza

### 1. REMOVER Arquivos Obsoletos/Não Usados

**Serviços antigos (modelo OLD):**
- ❌ `src/api/discount_service.py` - Tenta carregar modelo antigo da pasta `ml_model_OLD_backup`
- ❌ `src/api/ml_service.py` - Usa `SteamPriceMLPipeline` que não existe mais
- ❌ `src/api/services.py` - Usa SQLAlchemy (não estamos usando)
- ❌ `src/etl_production_railway.py` - ETL para Railway (não usado)

**Database models antigos:**
- ⚠️ `src/database/models.py` - Usa SQLAlchemy, mas o projeto usa MySQL direto

### 2. MOVER Arquivos para Estrutura Acadêmica

**Criar pasta `docs/`:**
```
docs/
├── ML_MODEL.md              (era README_ML_V2.md)
├── INTEGRATION.md           (era INTEGRATION_SUCCESS.md)
└── API_ENDPOINTS.md         (novo - documentar endpoints)
```

**Reorganizar `tests/`:**
```
tests/
├── test_ml_integration.py   (mover da raiz)
└── test_api.py              (novo - testes da API)
```

**Reorganizar `scripts/`:**
```
scripts/
├── 01_prepare_dataset.py    (novo nome: prepare_binary_target.py)
├── 02_train_model.py        (renomear: train_baseline_model.py)
└── README.md                (atualizar)
```

### 3. RENOMEAR para Padrão Acadêmico

**Scripts de treinamento (numerados):**
- `prepare_binary_target.py` → `01_prepare_dataset.py`
- `train_baseline_model.py` → `02_train_model.py`

**Documentação:**
- `README_ML_V2.md` → `docs/ML_MODEL.md`
- `INTEGRATION_SUCCESS.md` → `docs/INTEGRATION.md`

**Testes:**
- `test_ml_integration.py` → `tests/test_ml_service.py`

---

## 📁 Estrutura Final Proposta

```
pryzor-back/
├── 📂 src/                              # Código-fonte da API
│   ├── main.py                          # ✅ API FastAPI (endpoint principal)
│   ├── 📂 api/
│   │   ├── ml_discount_predictor.py     # ✅ Serviço ML v2.0
│   │   └── schemas.py                   # ✅ Schemas Pydantic
│   └── 📂 database/
│       ├── config.py                    # ✅ Configuração MySQL
│       └── connection.py                # ✅ Gerenciamento de conexões
│
├── 📂 scripts/                          # Scripts de ML/ETL
│   ├── 01_prepare_dataset.py            # Preparação do dataset
│   ├── 02_train_model.py                # Treinamento do modelo
│   └── README.md                        # Documentação dos scripts
│
├── 📂 ml_model/                         # Modelos treinados
│   └── discount_predictor.pkl           # Modelo RandomForest v2.0
│
├── 📂 data/                             # Datasets
│   └── data_with_binary_target.csv      # Dataset para treinamento
│
├── 📂 tests/                            # Testes automatizados
│   ├── test_ml_service.py               # Testes do serviço ML
│   └── test_api.py                      # Testes dos endpoints
│
├── 📂 docs/                             # Documentação do projeto
│   ├── ML_MODEL.md                      # Documentação do modelo
│   ├── INTEGRATION.md                   # Guia de integração
│   └── API_ENDPOINTS.md                 # Documentação da API
│
├── requirements.txt                     # Dependências Python
├── .env.example                         # Exemplo de variáveis de ambiente
├── Dockerfile                           # Containerização (opcional)
└── README.md                            # README principal
```

---

## ✅ Vantagens da Nova Estrutura

### Organização Acadêmica:
- ✅ Scripts numerados (ordem de execução clara)
- ✅ Documentação separada em `docs/`
- ✅ Testes organizados em `tests/`
- ✅ Código-fonte limpo em `src/`

### Manutenibilidade:
- ✅ Remove código obsoleto (modelos antigos)
- ✅ Elimina duplicação (3 serviços → 1 serviço)
- ✅ Nomes descritivos e padronizados

### Para o TCC:
- ✅ Estrutura profissional e organizada
- ✅ Fácil de navegar durante apresentação
- ✅ Documentação clara e acessível
- ✅ Segue boas práticas de engenharia de software

---

## 🚀 Próximos Passos

1. **Criar pasta `docs/`**
2. **Mover arquivos de documentação**
3. **Renomear scripts (numeração)**
4. **Mover testes para `tests/`**
5. **Remover arquivos obsoletos**
6. **Atualizar imports no código**
7. **Criar README principal atualizado**
8. **Testar tudo após reorganização**

---

## ⚠️ Arquivos a NÃO Remover (Mesmo se Não Usados)

- ✅ `Dockerfile` - Pode ser útil para deploy
- ✅ `.env.example` - Documenta variáveis necessárias
- ✅ `src/database/models.py` - Pode ser útil no futuro

---

## 📝 Notas

**Arquivos removidos serão:**
1. Documentados antes da remoção
2. Salvos em commit Git (caso precise recuperar)
3. Listados em um arquivo `CHANGELOG.md`

**AGUARDANDO APROVAÇÃO PARA EXECUTAR**
