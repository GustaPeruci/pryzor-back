"""
Script de Treinamento do Modelo v2.1

Objetivo: Treinar modelo com features de DURAÇÃO de promoção
          para melhorar detecção de quando descontos vão continuar

Mudanças do v2.0 → v2.1:
- Mantém as 8 features originais
- Adiciona 3 features de duração:
  1. discount_consecutive_days: Quantos dias consecutivos em promoção
  2. discount_progress_ratio: % progresso da promoção (dias/mediana)
  3. discount_likely_ending: Booleano se promoção pode terminar

Features totais: 11 (8 originais + 3 novas)

Autor: Pryzor Team
Data: 23/10/2025
"""

import pandas as pd
import numpy as np
import pickle
from pathlib import Path
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import warnings

warnings.filterwarnings('ignore')


def load_and_prepare_data(data_dir: Path, app_info_path: Path):
    """Carrega e prepara dataset"""
    print("=" * 80)
    print("CARREGANDO DADOS")
    print("=" * 80)
    print()
    
    # Carregar informações dos jogos
    try:
        app_info = pd.read_csv(app_info_path, encoding='utf-8')
    except:
        try:
            app_info = pd.read_csv(app_info_path, encoding='latin-1')
        except:
            app_info = pd.read_csv(app_info_path, encoding='cp1252')
    
    print(f"✅ {len(app_info):,} jogos no catálogo")
    
    # Carregar históricos de preço
    price_files = list(data_dir.glob('*.csv'))
    print(f"📁 {len(price_files):,} arquivos de histórico")
    
    all_data = []
    for i, price_file in enumerate(price_files, 1):
        if i % 500 == 0:
            print(f"   Carregando arquivo {i}/{len(price_files)}...")
        
        appid = int(price_file.stem)
        df = pd.read_csv(price_file)
        df.columns = df.columns.str.lower()
        df = df.rename(columns={
            'initialprice': 'initial_price',
            'finalprice': 'final_price'
        })
        df['appid'] = appid
        all_data.append(df)
    
    df = pd.concat(all_data, ignore_index=True)
    df['date'] = pd.to_datetime(df['date'])
    df = df.merge(app_info[['appid', 'name', 'freetoplay']], on='appid', how='left')
    
    print(f"✅ {len(df):,} registros carregados")
    print(f"📅 Período: {df['date'].min().date()} a {df['date'].max().date()}")
    print()
    
    return df


def engineer_duration_features(df):
    """
    Engenharia das features de DURAÇÃO de promoção
    
    3 Novas Features:
    1. discount_consecutive_days: Dias consecutivos em promoção
    2. discount_progress_ratio: Progresso da promoção (0-1)
    3. discount_likely_ending: Se está próximo do fim (>= 50% do tempo médio)
    """
    print("=" * 80)
    print("ENGENHARIA DE FEATURES DE DURAÇÃO")
    print("=" * 80)
    print()
    
    # Ordenar por jogo e data
    df = df.sort_values(['appid', 'date']).reset_index(drop=True)
    
    # 1. Identificar se tem desconto significativo (>= 20%)
    df['has_discount'] = (df['discount'] >= 20).astype(int)
    
    # 2. Criar grupos de promoção (cada sequência de dias com desconto)
    df['discount_group'] = (
        (df['has_discount'] != df.groupby('appid')['has_discount'].shift(1))
        .cumsum()
    )
    
    # 3. FEATURE 1: Dias consecutivos em promoção
    print("📊 Calculando dias consecutivos em promoção...")
    df['discount_consecutive_days'] = df.groupby(['appid', 'discount_group']).cumcount() + 1
    df.loc[df['has_discount'] == 0, 'discount_consecutive_days'] = 0
    
    # 4. Calcular estatísticas de duração por jogo
    print("📊 Calculando estatísticas de duração...")
    discount_periods = df[df['has_discount'] == 1].groupby(['appid', 'discount_group']).size()
    
    # Mediana da duração das promoções por jogo
    median_duration = discount_periods.groupby('appid').median()
    df['median_discount_duration'] = df['appid'].map(median_duration).fillna(7)  # Default 7 dias
    
    # 5. FEATURE 2: Progresso da promoção (ratio)
    print("📊 Calculando progresso das promoções...")
    df['discount_progress_ratio'] = (
        df['discount_consecutive_days'] / df['median_discount_duration']
    )
    df['discount_progress_ratio'] = df['discount_progress_ratio'].clip(0, 2)  # Cap em 200%
    
    # 6. FEATURE 3: Promoção pode estar terminando
    print("📊 Identificando promoções próximas do fim...")
    df['discount_likely_ending'] = (
        (df['discount_progress_ratio'] >= 0.5) & 
        (df['has_discount'] == 1)
    ).astype(int)
    
    print()
    print("✅ Features de duração criadas:")
    print(f"   - discount_consecutive_days: Dias em promoção (média: {df[df['has_discount']==1]['discount_consecutive_days'].mean():.1f})")
    print(f"   - discount_progress_ratio: Progresso (média: {df[df['has_discount']==1]['discount_progress_ratio'].mean():.2f})")
    print(f"   - discount_likely_ending: Perto do fim ({df['discount_likely_ending'].sum():,} casos)")
    print()
    
    return df


def create_features_and_target(df, cutoff_date='2020-04-01', prediction_window=30):
    """Cria features e target com validação temporal"""
    print("=" * 80)
    print("CRIANDO FEATURES E TARGET")
    print("=" * 80)
    print()
    
    # Filtrar jogos pagos
    df = df[df['freetoplay'] == 0].copy()
    print(f"✅ Jogos pagos: {df['appid'].nunique():,}")
    
    # Ordenar por data
    df = df.sort_values(['appid', 'date']).reset_index(drop=True)
    
    # Criar features temporais originais
    df['month'] = df['date'].dt.month
    df['quarter'] = df['date'].dt.quarter
    df['day_of_week'] = df['date'].dt.dayofweek
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
    df['is_summer_sale'] = df['month'].isin([6, 7]).astype(int)
    df['is_winter_sale'] = df['month'].isin([12, 1]).astype(int)
    
    # Criar target: vai ter desconto >= 20% nos próximos X dias?
    print(f"📊 Criando target (janela de {prediction_window} dias)...")
    
    df['future_discount'] = df.groupby('appid')['discount'].shift(-prediction_window)
    df['will_have_discount'] = (df['future_discount'] >= 20).astype(int)
    
    # Remover linhas sem target
    df_clean = df.dropna(subset=['will_have_discount']).copy()
    
    print(f"✅ {len(df_clean):,} registros com target")
    print(f"   Positivos (terá desconto): {df_clean['will_have_discount'].sum():,} ({df_clean['will_have_discount'].mean()*100:.1f}%)")
    print()
    
    # Split temporal (treino antes do cutoff, teste depois)
    cutoff_dt = pd.to_datetime(cutoff_date)
    train = df_clean[df_clean['date'] < cutoff_dt].copy()
    test = df_clean[df_clean['date'] >= cutoff_dt].copy()
    
    print("📅 SPLIT TEMPORAL:")
    print(f"   Treino: {train['date'].min().date()} a {train['date'].max().date()} ({len(train):,} registros)")
    print(f"   Teste:  {test['date'].min().date()} a {test['date'].max().date()} ({len(test):,} registros)")
    print()
    
    # Features finais (8 originais + 3 novas = 11)
    feature_cols = [
        # Originais do v2.0
        'month', 'quarter', 'day_of_week', 'is_weekend',
        'is_summer_sale', 'is_winter_sale', 'final_price', 'discount',
        # Novas do v2.1
        'discount_consecutive_days', 'discount_progress_ratio', 'discount_likely_ending'
    ]
    
    X_train = train[feature_cols]
    y_train = train['will_have_discount']
    X_test = test[feature_cols]
    y_test = test['will_have_discount']
    
    print("🎯 FEATURES DO MODELO v2.1 (11 features):")
    print("   Originais (8):")
    print("     1. month, 2. quarter, 3. day_of_week, 4. is_weekend")
    print("     5. is_summer_sale, 6. is_winter_sale, 7. final_price, 8. discount")
    print("   Novas (3):")
    print("     9. discount_consecutive_days (dias em promoção)")
    print("    10. discount_progress_ratio (progresso 0-2)")
    print("    11. discount_likely_ending (binário)")
    print()
    
    return X_train, X_test, y_train, y_test, feature_cols


def train_model(X_train, y_train, feature_cols):
    """Treina RandomForest"""
    print("=" * 80)
    print("TREINANDO MODELO v2.1")
    print("=" * 80)
    print()
    
    print("🌲 Treinando RandomForest...")
    print("   Parâmetros:")
    print("     - n_estimators: 200")
    print("     - max_depth: 15")
    print("     - min_samples_split: 20")
    print("     - random_state: 42")
    print()
    
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        min_samples_split=20,
        random_state=42,
        n_jobs=-1,
        class_weight='balanced'
    )
    
    model.fit(X_train, y_train)
    
    print("✅ Modelo treinado!")
    print()
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("📊 IMPORTÂNCIA DAS FEATURES:")
    for idx, row in feature_importance.iterrows():
        bar = "█" * int(row['importance'] * 100)
        print(f"   {row['feature']:30s} {row['importance']*100:5.2f}% {bar}")
    print()
    
    return model, feature_importance


def evaluate_model(model, X_test, y_test):
    """Avalia modelo no conjunto de teste"""
    print("=" * 80)
    print("AVALIAÇÃO DO MODELO v2.1")
    print("=" * 80)
    print()
    
    # Predições
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    
    # Métricas
    print("📊 MÉTRICAS DE CLASSIFICAÇÃO:")
    print()
    print(classification_report(y_test, y_pred, 
                                target_names=['Sem desconto', 'Com desconto'],
                                digits=4))
    
    # ROC-AUC
    roc_auc = roc_auc_score(y_test, y_prob)
    print(f"🎯 ROC-AUC Score: {roc_auc:.4f}")
    print()
    
    # Matriz de confusão
    cm = confusion_matrix(y_test, y_pred)
    print("📊 MATRIZ DE CONFUSÃO:")
    print(f"                 Previsto:")
    print(f"                 Sem    Com")
    print(f"Real Sem:     {cm[0,0]:6d} {cm[0,1]:6d}")
    print(f"     Com:     {cm[1,0]:6d} {cm[1,1]:6d}")
    print()
    
    # Extrair métricas do classification report
    from sklearn.metrics import precision_recall_fscore_support
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average='binary', pos_label=1
    )
    
    metrics = {
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'roc_auc': roc_auc,
        'accuracy': (y_pred == y_test).mean()
    }
    
    return metrics


def save_model(model, feature_cols, metrics, output_path: Path):
    """Salva modelo e metadados"""
    print("=" * 80)
    print("SALVANDO MODELO v2.1")
    print("=" * 80)
    print()
    
    model_package = {
        'model': model,
        'feature_names': feature_cols,
        'version': '2.1',
        'training_date': datetime.now().isoformat(),
        'metrics': metrics,
        'description': 'RandomForest com features de duração de promoção',
        'changes_from_v2_0': [
            'Adicionadas 3 features de duração de promoção',
            'discount_consecutive_days: Dias consecutivos em promoção',
            'discount_progress_ratio: Progresso da promoção (0-2)',
            'discount_likely_ending: Booleano se promoção pode terminar'
        ]
    }
    
    with open(output_path, 'wb') as f:
        pickle.dump(model_package, f)
    
    print(f"💾 Modelo salvo em: {output_path}")
    print()
    print("📦 Conteúdo do pacote:")
    print(f"   - Versão: {model_package['version']}")
    print(f"   - Features: {len(feature_cols)}")
    print(f"   - F1-Score: {metrics['f1_score']:.4f}")
    print(f"   - ROC-AUC: {metrics['roc_auc']:.4f}")
    print()


def compare_with_v2_0(v2_1_metrics):
    """Compara métricas com v2.0"""
    print("=" * 80)
    print("COMPARAÇÃO v2.0 vs v2.1")
    print("=" * 80)
    print()
    
    # Métricas do v2.0 (do modelo atual)
    v2_0_metrics = {
        'precision': 0.9046,
        'recall': 0.6309,
        'f1_score': 0.7434,
        'roc_auc': 0.7945
    }
    
    print("📊 EVOLUÇÃO DAS MÉTRICAS:")
    print()
    print(f"                v2.0      v2.1     Diferença")
    print("-" * 50)
    
    for metric in ['precision', 'recall', 'f1_score', 'roc_auc']:
        v2_0 = v2_0_metrics[metric]
        v2_1 = v2_1_metrics[metric]
        diff = v2_1 - v2_0
        sign = "+" if diff > 0 else ""
        emoji = "📈" if diff > 0 else "📉" if diff < 0 else "➡️"
        
        print(f"{metric:12s}  {v2_0:6.4f}   {v2_1:6.4f}   {sign}{diff:+7.4f} {emoji}")
    
    print()
    
    # Avaliar se houve melhora
    if v2_1_metrics['f1_score'] > v2_0_metrics['f1_score']:
        print("✅ RESULTADO: Modelo v2.1 é MELHOR que v2.0!")
        print(f"   F1-Score aumentou {(v2_1_metrics['f1_score'] - v2_0_metrics['f1_score'])*100:+.2f}%")
    elif v2_1_metrics['f1_score'] < v2_0_metrics['f1_score']:
        print("⚠️  RESULTADO: Modelo v2.1 é PIOR que v2.0")
        print(f"   F1-Score diminuiu {(v2_1_metrics['f1_score'] - v2_0_metrics['f1_score'])*100:.2f}%")
        print("   Recomendação: Manter v2.0 em produção")
    else:
        print("➡️  RESULTADO: Modelos têm performance similar")
    
    print()


def main():
    """Função principal"""
    print("\n" + "=" * 80)
    print("TREINAMENTO DO MODELO v2.1 - Features de Duração")
    print("=" * 80)
    print()
    
    # Caminhos
    backend_root = Path(__file__).parent.parent
    price_dir = backend_root / "data" / "PriceHistory"
    app_info_file = backend_root / "data" / "applicationInformation.csv"
    output_file = backend_root / "ml_model" / "discount_predictor_v2_1.pkl"
    
    # 1. Carregar dados
    df = load_and_prepare_data(price_dir, app_info_file)
    
    # 2. Engenharia de features de duração
    df = engineer_duration_features(df)
    
    # 3. Criar features e target
    X_train, X_test, y_train, y_test, feature_cols = create_features_and_target(df)
    
    # 4. Treinar modelo
    model, feature_importance = train_model(X_train, y_train, feature_cols)
    
    # 5. Avaliar
    metrics = evaluate_model(model, X_test, y_test)
    
    # 6. Comparar com v2.0
    compare_with_v2_0(metrics)
    
    # 7. Salvar
    save_model(model, feature_cols, metrics, output_file)
    
    print("=" * 80)
    print("✅ TREINAMENTO CONCLUÍDO!")
    print("=" * 80)
    print()
    print("📝 PRÓXIMOS PASSOS:")
    print("   1. Validar modelo v2.1 com o script validate_model_v2.py")
    print("   2. Comparar resultados com v2.0")
    print("   3. Se melhor, fazer deploy do v2.1")
    print("   4. Se pior, manter v2.0 e investigar alternativas")
    print()


if __name__ == "__main__":
    main()
