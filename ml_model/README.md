# 🤖 Modelo de Machine Learning em Produção

## 📦 Modelo Atual: v2.0

**Arquivo:** `discount_predictor.pkl`  
**Status:** ✅ ATIVO EM PRODUÇÃO  
**Data de treinamento:** Outubro 2025  
**Última validação:** 23/10/2025 (1.000 jogos)

---

## 📊 Métricas de Performance

### Teste (Set Holdout - 193K registros)

| Métrica | Valor | Interpretação |
|---------|-------|---------------|
| **Precision** | 90.46% | 9 em 10 alertas de desconto estão corretos |
| **F1-Score** | 74.34% | Balanço geral excelente |
| **Recall** | 63.09% | Captura 63% das oportunidades reais |
| **ROC-AUC** | 79.45% | Boa capacidade de discriminação |

### Validação Real (1.000 jogos aleatórios)

| Cenário | Acurácia | Observação |
|---------|----------|------------|
| **Geral** | 92.4% | 924 previsões corretas de 1.000 |
| **Sem desconto** | 97.7% | Quase perfeito no cenário principal |
| **Desconto ativo** | 5.4% | Ponto fraco conhecido (53 erros) |
| **Preço aumentou** | 100% | Nenhum erro tipo Stardew Valley |

---

## 🎯 Características Técnicas

### Algoritmo
- **RandomForestClassifier**
  - n_estimators: 200
  - max_depth: 15
  - class_weight: balanced
  - random_state: 42

### Features (8)
1. `month` - Mês do ano (1-12)
2. `quarter` - Trimestre (1-4)
3. `day_of_week` - Dia da semana (0-6)
4. `is_weekend` - Final de semana? (0/1)
5. `is_summer_sale` - Steam Summer Sale? (0/1)
6. `is_winter_sale` - Steam Winter Sale? (0/1)
7. `final_price` - Preço final atual (USD)
8. `discount` - Desconto percentual atual (0-100)

### Target
- **will_have_discount**: Binário (0/1)
- **Definição:** Desconto >= 20% nos próximos 30 dias

### Validação
- **Método:** Temporal split
- **Train:** Dados até 31/03/2020 (529K registros)
- **Test:** Dados de 01/04/2020 em diante (193K registros)
- **Sem data leakage:** Features não usam informações futuras

---

## 💡 Pontos Fortes

✅ **Alta confiabilidade** - 90% precision significa poucos falsos alarmes  
✅ **Conservador** - Prefere não alertar do que alertar errado  
✅ **Simples e interpretável** - 8 features claras  
✅ **Validado em produção** - 92.4% acerto em 1.000 casos reais  
✅ **Generaliza bem** - Funciona para jogos novos e antigos  

---

## ⚠️ Limitações Conhecidas

❌ **Desconto ativo** - Apenas 5.4% acerto quando jogo já está em promoção  
❌ **Dados até 2020** - Não captura mudanças recentes da Steam (2021-2025)  
❌ **Target binário** - Não prevê QUANDO o desconto vai acontecer, só SE vai  
❌ **Sem dados de vendas** - Não considera popularidade ou sazonalidade de vendas  

**Justificativa:** Para a maioria dos casos (97.7%), o modelo funciona perfeitamente. Os 5.4% de erro em descontos ativos representam cenários raros.

---

## 🔬 Histórico de Versões

### v2.0 (ATUAL) ✅
- **Status:** Produção
- **F1-Score:** 74.34%
- **Precision:** 90.46%
- **Decisão:** Mantido como melhor modelo disponível

### v2.1 (DESCARTADO) ❌
- **Status:** Experimento falho
- **F1-Score:** 38.11% (-36% vs v2.0)
- **Precision:** 25.67% (-65% vs v2.0)
- **Decisão:** Revertido - features de duração causaram overfitting
- **Localização:** `experiments_failed/`

### v3.0 (DESCARTADO) ❌
- **Status:** Experimento falho
- **F1-Score:** ~45% (-29% vs v2.0)
- **Decisão:** Multi-classe não funciona com dados desbalanceados
- **Localização:** Não preservado (só histórico documentado)

**Ver:** `experiments_failed/README.md` para análise completa dos experimentos.

---

## 🚀 Como Usar Este Modelo

### Python (Direto)

```python
import pickle
import pandas as pd

# Carregar modelo
with open('ml_model/discount_predictor.pkl', 'rb') as f:
    data = pickle.load(f)
    model = data['model']
    features = data['features']

# Preparar dados
X = pd.DataFrame({
    'month': [10],
    'quarter': [4],
    'day_of_week': [2],
    'is_weekend': [0],
    'is_summer_sale': [0],
    'is_winter_sale': [0],
    'final_price': [59.99],
    'discount': [0]
})

# Predição
prediction = model.predict(X)[0]
probability = model.predict_proba(X)[0][1]

print(f"Vai ter desconto? {bool(prediction)}")
print(f"Probabilidade: {probability:.2%}")
```

### API (Recomendado)

```bash
# Via FastAPI
GET http://localhost:8000/api/ml/predict/271590

# Resposta
{
  "appid": 271590,
  "game_name": "Grand Theft Auto V",
  "will_have_discount": true,
  "probability": 0.78,
  "recommendation": "AGUARDAR",
  "current_price": 119.90,
  "model_version": "2.0"
}
```

---

## 📁 Arquivos Relacionados

- **Modelo:** `discount_predictor.pkl` (este arquivo)
- **Script treino:** `scripts/02_train_model.py`
- **Script validação:** `scripts/validate_model_v2.py`
- **Serviço API:** `src/api/ml_discount_predictor.py`
- **Testes:** `tests/test_ml_service.py`
- **Experimentos falhos:** `experiments_failed/`

---

## 🔐 Integridade

**Checksum (informativo):**
- Tamanho: ~2.5 MB
- Features: 8
- Estimadores: 200
- Classes: 2 (binário)

**Não alterar este arquivo manualmente!** Retreinar usando `scripts/02_train_model.py`.

---

## 📞 Suporte

**Projeto:** Pryzor - Previsão de Descontos Steam  
**TCC:** Engenharia de Software 2025  
**Autor:** Gustavo Peruci  
**Documentação completa:** `/README.md`

---

**Última atualização:** 23 de Outubro de 2025
