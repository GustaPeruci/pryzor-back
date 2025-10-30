"""
Script para gerar target binário (will_have_discount) para cada registro de preço.

Para cada linha, verifica se nos próximos 30 dias haverá desconto >= 20%.
Salva resultado em data/data_with_binary_target.csv

Autor: GitHub Copilot
Data: 30/10/2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import timedelta

# Caminhos
backend_root = Path(__file__).parent.parent
price_dir = backend_root / "data" / "PriceHistory"
app_info_file = backend_root / "data" / "applicationInformation.csv"
out_file = backend_root / "data" / "data_with_binary_target.csv"

print("📖 Carregando informações dos jogos...")
try:
    app_info = pd.read_csv(app_info_file, encoding='utf-8')
except UnicodeDecodeError:
    try:
        app_info = pd.read_csv(app_info_file, encoding='latin-1')
    except:
        app_info = pd.read_csv(app_info_file, encoding='cp1252')

print("📁 Lendo arquivos de histórico de preço...")
price_files = list(price_dir.glob('*.csv'))
all_rows = []

for price_file in price_files:
    appid = int(price_file.stem)
    df = pd.read_csv(price_file)
    df.columns = df.columns.str.lower()
    df = df.rename(columns={
        'initialprice': 'initial_price',
        'finalprice': 'final_price',
        'discount': 'discount'
    })
    df['appid'] = appid
    df['date'] = pd.to_datetime(df['date'])
    all_rows.append(df)

print(f"✅ {len(all_rows)} arquivos lidos")
df_full = pd.concat(all_rows, ignore_index=True)

# Merge com informações dos jogos
if 'appid' in app_info.columns:
    df_full = df_full.merge(app_info[['appid', 'name', 'freetoplay']], on='appid', how='left')

print(f"✅ {len(df_full):,} registros totais")

# Gerar target binário: haverá desconto >= 20% nos próximos 30 dias?
def compute_target(df):
    df = df.sort_values('date')
    will_have_discount = []
    for idx, row in df.iterrows():
        current_date = row['date']
        # Filtrar próximos 30 dias
        future = df[(df['date'] > current_date) & (df['date'] <= current_date + timedelta(days=30))]
        # Verifica se há desconto >= 20% nos próximos 30 dias
        has_discount = (future['discount'] >= 20).any()
        will_have_discount.append(int(has_discount))
    return will_have_discount

print("🔄 Calculando target binário para cada jogo...")
df_full['will_have_discount'] = 0
for appid in df_full['appid'].unique():
    mask = df_full['appid'] == appid
    df_app = df_full[mask]
    df_full.loc[mask, 'will_have_discount'] = compute_target(df_app)

print("✅ Target binário gerado!")

# Features temporais
print("🕒 Gerando features temporais...")
df_full['month'] = df_full['date'].dt.month
df_full['quarter'] = ((df_full['date'].dt.month - 1) // 3) + 1
df_full['day_of_week'] = df_full['date'].dt.dayofweek
df_full['is_weekend'] = (df_full['day_of_week'] >= 5).astype(int)
df_full['is_summer_sale'] = df_full['date'].dt.month.isin([6,7]).astype(int)
df_full['is_winter_sale'] = df_full['date'].dt.month.isin([12,1]).astype(int)

# Renomear desconto para discount_percent
if 'discount' in df_full.columns:
    df_full['discount_percent'] = df_full['discount']

# Salvar resultado
print(f"💾 Salvando em {out_file}")
df_full.to_csv(out_file, index=False)
print("✅ Arquivo salvo!")
