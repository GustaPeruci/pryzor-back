# Dados Processados - Pryzor

Este diretório contém datasets processados para treinamento de modelos de ML.

## 📁 Arquivos

### `data_with_binary_target.csv` ✅

**Descrição:** Dataset consolidado com target binário para classificação.

**Origem:**
- Script: `scripts/prepare_binary_target.py`
- Dados brutos: `applicationInformation.csv` + `PriceHistory/*.csv`

**Características:**
- **Registros:** 679,998
- **Jogos:** 1,507
- **Período:** 2019-04-07 a 2020-07-13 (~15 meses)
- **Granularidade:** 1 linha = 1 dia de 1 jogo

**Colunas:**

| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `date` | string | Data (YYYY-MM-DD) | "2019-04-07" |
| `appid` | int | ID do jogo na Steam | 578080 |
| `name` | string | Nome do jogo | "PUBG" |
| `final_price` | float | Preço final no dia (USD) | 29.99 |
| `discount_percent` | int | % de desconto no dia | 0, 20, 50 |
| **`will_have_discount`** | **int** | **Target: terá desconto >20% nos próximos 30 dias?** | **0 ou 1** |
| `month` | int | Mês (1-12) | 4 |
| `day_of_week` | int | Dia da semana (0=segunda, 6=domingo) | 0 |
| `is_weekend` | int | É fim de semana? | 0 ou 1 |
| `is_summer_sale` | int | É período de Summer Sale? (jun-jul) | 0 ou 1 |
| `is_winter_sale` | int | É período de Winter Sale? (dez-jan) | 0 ou 1 |
| `quarter` | int | Trimestre (1-4) | 2 |

**Distribuição do Target:**
- Classe 0 (não terá desconto): 288,899 (42.49%)
- Classe 1 (terá desconto): 391,099 (57.51%)
- ✅ **Classes razoavelmente balanceadas**

**Uso:**
```python
import pandas as pd

df = pd.read_csv('data/data_with_binary_target.csv')
print(df.shape)  # (679998, 12)
print(df['will_have_discount'].value_counts())
```

---

## 🚫 Atenção: Arquivos Grandes

- Este diretório está no `.gitignore`
- Dataset tem ~40MB (não versionar no Git)
- Para recriar: executar `scripts/prepare_binary_target.py`

---

## 📊 Estatísticas Descritivas

```
Preço médio: $16.73
Preço mínimo: $0.49
Preço máximo: $199.00
Desconto médio: 10.64%
Desconto máximo: 100%
```

---

**Última atualização:** 21/10/2025
