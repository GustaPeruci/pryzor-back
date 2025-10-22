# Scripts de ML - Pryzor Backend

Este diretório contém scripts para preparação de dados e treinamento de modelos de Machine Learning.

## 📁 Estrutura

```
pryzor-back/scripts/
├── README.md                      ← Este arquivo
├── prepare_binary_target.py       ← [Dia 1-2] Criar target binário
└── train_baseline_model.py        ← [Dia 3-4] Treinar modelo baseline (a criar)
```

---

## 🔧 Scripts Disponíveis

### 1. `prepare_binary_target.py` ✅

**Objetivo:** Preparar dataset com target binário para classificação.

**Problema reformulado:** Prever se um jogo terá desconto >20% nos próximos 30 dias.

**Input:**
- `../../applicationInformation.csv` (catálogo de jogos)
- `../../PriceHistory/*.csv` (histórico de preços diário)

**Output:**
- `../data/data_with_binary_target.csv` (679,998 registros)

**Features criadas:**
- `will_have_discount` (target: 0 ou 1)
- `month` (1-12)
- `day_of_week` (0-6, 0=segunda)
- `is_weekend` (0 ou 1)
- `is_summer_sale` (junho-julho)
- `is_winter_sale` (dezembro-janeiro)
- `quarter` (1-4)

**Como executar:**
```bash
cd pryzor-back
python scripts/prepare_binary_target.py
```

**Resultados:**
- ✅ 1,507 jogos processados
- ✅ 679,998 registros (períodos diários de 2019-04 a 2020-07)
- ✅ Classes balanceadas: 42.49% (sem desconto) / 57.51% (com desconto)

---

### 2. `train_baseline_model.py` 🔜

**Objetivo:** Treinar modelo baseline RandomForest para validar viabilidade do problema.

**Status:** A ser criado no Dia 3-4

**Meta:** F1-Score ≥ 0.50

**Features previstas:**
- Temporais: month, is_summer_sale, is_winter_sale, day_of_week
- Históricas: discount_percent (atual), final_price (atual)
- **SEM vazamento de alvo:** não usar avg_final_price, price_range, etc

**Algoritmo:** RandomForestClassifier (scikit-learn)

**Validação:** 70% treino / 30% teste (train_test_split)

---

## 📊 Pipeline de Dados

```
applicationInformation.csv
PriceHistory/*.csv
         ↓
prepare_binary_target.py
         ↓
data_with_binary_target.csv (679k registros)
         ↓
train_baseline_model.py
         ↓
../ml_model/discount_predictor.pkl
```

---

## 🔗 Integração com Backend

Após treinamento, o modelo será carregado em:
- `src/api/discount_service.py` (Dia 6)

Endpoint previsto:
```
POST /api/predict-discount
{
  "appid": 578080,
  "current_date": "2020-06-15"
}

Response:
{
  "discount_probability": 0.68,
  "recommendation": "Aguardar - alta probabilidade de desconto"
}
```

---

## 📝 Notas Técnicas

### Tratamento de Encoding
Todos os scripts usam fallback `UTF-8 → Latin1` para compatibilidade com dados Steam.

### Caminhos Relativos
- Script localizado: `pryzor-back/scripts/`
- Dados brutos: `Pryzor/` (raiz do projeto)
- Output: `pryzor-back/data/`

### Dependências
Ver `../requirements.txt`:
- pandas
- numpy
- scikit-learn
- tqdm
- matplotlib (para visualizações futuras)

---

**Última atualização:** 21/10/2025
