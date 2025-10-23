# 🔬 Experimentos de ML - Modelos Descartados

Esta pasta contém modelos experimentais que **falharam** durante o processo de desenvolvimento.

Mantemos esses arquivos para **fins de documentação acadêmica** (TCC) e análise histórica.

⚠️ **IMPORTANTE:** Esses modelos **NÃO devem ser usados em produção**.

---

## 📦 `discount_predictor_v2_1.pkl`

**Status:** ❌ REJEITADO  
**Data:** Outubro 2025  
**Motivo:** Performance significativamente inferior ao v2.0

### O que foi tentado

Expandir o modelo v2.0 (8 features) para v2.1 (11 features) adicionando 3 features de duração de promoção:

1. **discount_consecutive_days** - Quantos dias o jogo está em promoção consecutivamente
2. **discount_progress_ratio** - Progresso da promoção (0 a 2, onde 1 = duração mediana)
3. **discount_likely_ending** - Booleano indicando se a promoção está perto do fim (>50% da duração)

### Motivação

- Validação em 1.000 jogos revelou que v2.0 tinha **apenas 5.4% de acerto** em casos com desconto ativo
- 53 de 76 erros totais eram em jogos que já estavam em promoção
- Hipótese: Features de duração ajudariam a detectar quando uma promoção está terminando

### Metodologia

```python
# Feature engineering de duração
df['discount_consecutive_days'] = df.groupby(['appid', 'discount_group']).cumcount() + 1
df['discount_progress_ratio'] = df['discount_consecutive_days'] / df['median_discount_duration']
df['discount_likely_ending'] = (df['discount_progress_ratio'] >= 0.5) & (df['has_discount'] == 1)

# Mesmo RandomForest do v2.0
RandomForestClassifier(
    n_estimators=200,
    max_depth=15,
    class_weight='balanced',
    random_state=42
)
```

### Resultados (Set de Teste)

| Métrica | v2.0 | v2.1 | Variação | Status |
|---------|------|------|----------|--------|
| **Precision** | 90.46% | 25.67% | **-64.79%** | 📉 CRÍTICO |
| **F1-Score** | 74.34% | 38.11% | **-36.23%** | 📉 DEVASTADOR |
| **Recall** | 63.09% | 73.97% | +10.88% | 📈 Aumentou |
| **ROC-AUC** | 79.45% | 73.71% | -5.74% | 📉 Piorou |

### Confusion Matrix (v2.1)

```
Real/Predicted     Não Desconto    Tem Desconto
Não Desconto:         110,139         56,636  ← 56K FALSE POSITIVES!
Tem Desconto:           6,883         19,558
```

### Análise de Feature Importance

As features de duração **eram importantes**:
- `discount_consecutive_days`: **3º lugar** (10.55%)
- `discount_progress_ratio`: 5º lugar (6.76%)
- `discount_likely_ending`: 10º lugar (1.19%)

**Mas causaram desbalanceamento severo.**

### O que deu errado?

1. **Modelo "ansioso"**: As features de duração fizeram o modelo prever desconto em quase tudo
2. **Falsos positivos**: 56.636 casos preveram desconto quando não havia (vs precision 90% do v2.0)
3. **Overfitting em padrões**: Modelo aprendeu "tem desconto há X dias → vai continuar sempre"
4. **Trade-off ruim**: Recall aumentou (+10%), mas precision destruída (-65%)

Para um **sistema de recomendação**, precision baixa (25%) é **inaceitável** - ninguém confia em alertas falsos.

### Lições Aprendidas

✅ **Features de duração SÃO importantes** (ranking alto)  
❌ **Mas causam overfitting quando adicionadas naivamente**  
✅ **Modelo simples (v2.0) generaliza melhor**  
❌ **Complexity ≠ Better Performance**  
✅ **Precision > Recall** para sistemas de recomendação

### Decisão Final

**Reverter para v2.0**. 

- v2.0 tem 90% precision (confiável)
- v2.1 tem 26% precision (spam de false positives)
- Usuários preferem **menos alertas corretos** do que **muitos alertas errados**

---

## 🎓 Valor Acadêmico (TCC)

Este experimento demonstra:

1. **Método científico aplicado**: Hipótese → Implementação → Teste → Conclusão
2. **Análise de features**: Importance ≠ Usefulness
3. **Trade-offs em ML**: Precision vs Recall, Simplicidade vs Complexidade
4. **Validação rigorosa**: Métricas guiam decisões (não intuição)
5. **Honestidade científica**: Nem toda tentativa de melhoria funciona

**Resultado negativo é resultado válido** - documenta o que NÃO funciona e por quê.

---

## 📊 Dados de Treinamento

- **Dataset**: 725.268 registros de preços (2019-2020)
- **Jogos**: 1.505 paid games
- **Train/Test Split**: Temporal (2020-04-01)
  - Train: 529.029 registros (pré-2020)
  - Test: 193.216 registros (pós-2020)
- **Target**: desconto >= 20% nos próximos 30 dias
- **Class balance**: ~15% positivos (balanced com weights)

---

## 🔗 Referências

- Script de treinamento: `scripts/03_train_model_v2_1.py`
- Modelo em produção: `ml_model/discount_predictor.pkl` (v2.0)
- Validação real: `scripts/validate_model_v2.py` (1.000 jogos testados)
- Documentação completa: `README.md` (seção "Histórico de Evolução do Modelo")

---

**Última atualização:** Outubro 2025  
**Autor:** Gustavo Peruci  
**Projeto:** Pryzor - TCC Engenharia de Software
