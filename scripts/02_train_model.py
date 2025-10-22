"""
Script para treinar modelo baseline de predição de descontos.

Objetivo: Prever se um jogo terá desconto >20% nos próximos 30 dias.
Tipo: Classificação binária (0 = não, 1 = sim)

Este script:
1. Carrega dataset com target binário (data_with_binary_target.csv)
2. Seleciona features SEM vazamento de alvo
3. Treina RandomForestClassifier com VALIDAÇÃO TEMPORAL (não aleatória)
4. Calcula métricas: F1-Score, Precision, Recall, Accuracy
5. Salva modelo treinado (.pkl)

IMPORTANTE: Usa split temporal (antes/depois de 2020-04-01) para evitar
vazamento temporal comum em séries temporais.

Meta: F1-Score ≥ 0.50 (com validação temporal correta)

Autor: Pryzor Team
Data: 21/10/2025
Versão: 2.0 (corrigido split temporal)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import pickle
import warnings

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    accuracy_score,
    roc_auc_score
)

warnings.filterwarnings('ignore')


def load_dataset(file_path: Path) -> pd.DataFrame:
    """
    Carrega dataset com target binário.
    
    Args:
        file_path: Caminho para data_with_binary_target.csv
    
    Returns:
        DataFrame com todas as colunas
    """
    print(f"📖 Carregando dataset de {file_path}...")
    df = pd.read_csv(file_path)
    print(f"✅ {len(df):,} registros carregados")
    print(f"📊 Colunas: {list(df.columns)}")
    print()
    return df


def prepare_features(df: pd.DataFrame) -> tuple:
    """
    Prepara features e target para treinamento.
    
    IMPORTANTE: NÃO usar features que causem vazamento de alvo:
    - ❌ avg_final_price (derivado do target)
    - ❌ price_range (derivado do target)
    - ❌ is_premium, is_budget (derivados do target)
    
    Features permitidas:
    - ✅ Temporais: month, day_of_week, is_weekend, quarter, is_summer_sale, is_winter_sale
    - ✅ Preço atual: final_price (preço do dia atual, não média histórica)
    - ✅ Desconto atual: discount_percent (desconto do dia atual)
    
    Args:
        df: DataFrame original
    
    Returns:
        X (features), y (target), feature_names (lista de nomes)
    """
    print("🔧 PREPARANDO FEATURES")
    print("-" * 80)
    
    # Features selecionadas (SEM vazamento de alvo)
    feature_columns = [
        # Temporais (sazonalidade é importante!)
        'month',
        'day_of_week',
        'is_weekend',
        'quarter',
        'is_summer_sale',
        'is_winter_sale',
        
        # Valores do dia atual (não médias históricas)
        'final_price',
        'discount_percent',
    ]
    
    # Verificar se todas as features existem
    missing_features = [col for col in feature_columns if col not in df.columns]
    if missing_features:
        raise ValueError(f"Features faltando no dataset: {missing_features}")
    
    # Remover linhas com valores nulos
    df_clean = df.dropna(subset=feature_columns + ['will_have_discount'])
    
    print(f"📊 Features selecionadas ({len(feature_columns)}):")
    for i, feat in enumerate(feature_columns, 1):
        print(f"   {i:2d}. {feat}")
    print()
    
    print(f"🧹 Linhas removidas (valores nulos): {len(df) - len(df_clean):,}")
    print(f"✅ Linhas válidas: {len(df_clean):,}")
    print()
    
    # Separar features e target
    X = df_clean[feature_columns].values
    y = df_clean['will_have_discount'].values
    
    print(f"📐 Shape de X: {X.shape}")
    print(f"📐 Shape de y: {y.shape}")
    print()
    
    # Estatísticas do target
    unique, counts = np.unique(y, return_counts=True)
    print("📊 DISTRIBUIÇÃO DO TARGET:")
    print("-" * 40)
    for label, count in zip(unique, counts):
        pct = (count / len(y)) * 100
        label_name = "Não terá desconto" if label == 0 else "Terá desconto >20%"
        print(f"   Classe {label} ({label_name}): {count:>8,} ({pct:>5.2f}%)")
    print()
    
    return X, y, feature_columns


def train_model(X_train, y_train, random_state=42):
    """
    Treina RandomForestClassifier.
    
    Hiperparâmetros escolhidos:
    - n_estimators=100: Número de árvores (mais = melhor, mas mais lento)
    - max_depth=15: Profundidade máxima (evita overfitting)
    - min_samples_split=20: Mínimo de amostras para split
    - min_samples_leaf=10: Mínimo de amostras em folha
    - class_weight='balanced': Balanceia classes automaticamente
    
    Args:
        X_train: Features de treino
        y_train: Target de treino
        random_state: Seed para reprodutibilidade
    
    Returns:
        Modelo treinado
    """
    print("🌲 TREINANDO RANDOM FOREST")
    print("-" * 80)
    
    # Configurar modelo
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=15,
        min_samples_split=20,
        min_samples_leaf=10,
        class_weight='balanced',
        random_state=random_state,
        n_jobs=-1,  # Usar todos os cores
        verbose=0
    )
    
    print("⚙️  Hiperparâmetros:")
    print(f"   - n_estimators: 100")
    print(f"   - max_depth: 15")
    print(f"   - min_samples_split: 20")
    print(f"   - min_samples_leaf: 10")
    print(f"   - class_weight: balanced")
    print()
    
    print("🏋️  Treinando modelo...")
    start_time = datetime.now()
    
    model.fit(X_train, y_train)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"✅ Modelo treinado em {duration:.2f} segundos")
    print()
    
    return model


def evaluate_model(model, X_test, y_test, feature_names):
    """
    Avalia modelo no conjunto de teste.
    
    Métricas calculadas:
    - Accuracy: % de acertos totais
    - Precision: De todos os "sim" previstos, quantos eram corretos?
    - Recall: De todos os "sim" reais, quantos foram detectados?
    - F1-Score: Média harmônica entre Precision e Recall (métrica principal)
    - ROC-AUC: Área sob a curva ROC
    
    Args:
        model: Modelo treinado
        X_test: Features de teste
        y_test: Target de teste
        feature_names: Nomes das features
    
    Returns:
        Dict com métricas
    """
    print("📊 AVALIAÇÃO NO CONJUNTO DE TESTE")
    print("=" * 80)
    
    # Predições
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    # Calcular métricas
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_pred_proba)
    
    # Confusion Matrix
    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()
    
    # Exibir resultados
    print()
    print("🎯 MÉTRICAS PRINCIPAIS")
    print("-" * 80)
    print(f"   Accuracy:  {accuracy:.4f} ({accuracy*100:.2f}%)")
    print(f"   Precision: {precision:.4f} ({precision*100:.2f}%)")
    print(f"   Recall:    {recall:.4f} ({recall*100:.2f}%)")
    print(f"   F1-Score:  {f1:.4f} ({f1*100:.2f}%) ⭐")
    print(f"   ROC-AUC:   {roc_auc:.4f}")
    print()
    
    # Matriz de confusão
    print("🔢 MATRIZ DE CONFUSÃO")
    print("-" * 80)
    print(f"   True Negatives  (TN): {tn:>8,}  (predito: não, real: não)")
    print(f"   False Positives (FP): {fp:>8,}  (predito: sim, real: não)")
    print(f"   False Negatives (FN): {fn:>8,}  (predito: não, real: sim)")
    print(f"   True Positives  (TP): {tp:>8,}  (predito: sim, real: sim)")
    print()
    
    # Relatório detalhado
    print("📋 RELATÓRIO DE CLASSIFICAÇÃO")
    print("-" * 80)
    print(classification_report(
        y_test, y_pred,
        target_names=['Não terá desconto', 'Terá desconto'],
        digits=4
    ))
    
    # Feature Importance
    print("🔍 IMPORTÂNCIA DAS FEATURES (Top 10)")
    print("-" * 80)
    feature_importances = pd.DataFrame({
        'feature': feature_names,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    for idx, row in feature_importances.head(10).iterrows():
        print(f"   {row['feature']:20s}: {row['importance']:.4f}")
    print()
    
    # Retornar métricas
    metrics = {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'roc_auc': roc_auc,
        'confusion_matrix': cm,
        'feature_importances': feature_importances
    }
    
    return metrics


def save_model(model, feature_names, metrics, output_path: Path):
    """
    Salva modelo treinado e metadados.
    
    Args:
        model: Modelo treinado
        feature_names: Lista de nomes das features
        metrics: Dict com métricas de avaliação
        output_path: Caminho para salvar o .pkl
    """
    print("💾 SALVANDO MODELO")
    print("-" * 80)
    
    # Criar diretório se não existir
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Empacotar modelo com metadados
    model_package = {
        'model': model,
        'feature_names': feature_names,
        'metrics': metrics,
        'trained_at': datetime.now().isoformat(),
        'model_type': 'RandomForestClassifier',
        'target': 'will_have_discount (binary)',
        'version': '2.0',
        'validation_method': 'temporal_split (cutoff: 2020-04-01)',
        'notes': 'Modelo treinado com validação temporal adequada para evitar vazamento de dados'
    }
    
    # Salvar
    with open(output_path, 'wb') as f:
        pickle.dump(model_package, f)
    
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"✅ Modelo salvo em: {output_path}")
    print(f"📦 Tamanho do arquivo: {file_size_mb:.2f} MB")
    print()


def main():
    """Função principal para treinar modelo baseline."""
    
    print("=" * 80)
    print("TREINAMENTO DE MODELO BASELINE - Pryzor")
    print("Objetivo: Prever desconto >20% nos próximos 30 dias")
    print("=" * 80)
    print()
    
    # Caminhos
    backend_root = Path(__file__).parent.parent  # pryzor-back/
    data_file = backend_root / "data" / "data_with_binary_target.csv"
    model_dir = backend_root / "ml_model"
    model_file = model_dir / "discount_predictor.pkl"
    
    print(f"📂 Backend root: {backend_root}")
    print(f"📄 Dataset: {data_file}")
    print(f"💾 Modelo será salvo em: {model_file}")
    print()
    
    # Verificar se dataset existe
    if not data_file.exists():
        print(f"❌ Erro: Dataset não encontrado em {data_file}")
        print("   Execute primeiro: python scripts/prepare_binary_target.py")
        return
    
    # 1. Carregar dataset
    df_full = load_dataset(data_file)
    
    # 2. SPLIT TEMPORAL (CRÍTICO para séries temporais!)
    print("✂️  DIVIDINDO DATASET COM VALIDAÇÃO TEMPORAL")
    print("-" * 80)
    print("⚠️  IMPORTANTE: Usando split temporal (não aleatório)")
    print("   Isso evita vazamento temporal (treino não vê dados futuros)")
    print()
    
    # Converter coluna de data
    df_full['date'] = pd.to_datetime(df_full['date'])
    
    # Definir data de corte (70/30 aproximado)
    # Período total: 2019-04-07 a 2020-07-13 (~15 meses)
    # Corte: 2020-04-01 (70% = ~10.5 meses treino, 30% = ~4.5 meses teste)
    cutoff_date = pd.to_datetime('2020-04-01')
    
    print(f"📅 Período total: {df_full['date'].min().date()} a {df_full['date'].max().date()}")
    print(f"📅 Data de corte: {cutoff_date.date()}")
    print(f"   ├─ Treino: antes de {cutoff_date.date()}")
    print(f"   └─ Teste:  a partir de {cutoff_date.date()}")
    print()
    
    # Criar máscaras temporais
    train_mask = df_full['date'] < cutoff_date
    test_mask = df_full['date'] >= cutoff_date
    
    df_train = df_full[train_mask].copy()
    df_test = df_full[test_mask].copy()
    
    print(f"   Treino: {len(df_train):>8,} amostras ({len(df_train)/len(df_full)*100:.1f}%)")
    print(f"   Teste:  {len(df_test):>8,} amostras ({len(df_test)/len(df_full)*100:.1f}%)")
    print()
    
    # 3. Preparar features de treino e teste separadamente
    print("🔧 Preparando features de TREINO...")
    X_train, y_train, feature_names = prepare_features(df_train)
    
    print("🔧 Preparando features de TESTE...")
    X_test, y_test, _ = prepare_features(df_test)
    
    print()
    
    # 4. Treinar modelo
    model = train_model(X_train, y_train)
    
    # 5. Avaliar modelo
    metrics = evaluate_model(model, X_test, y_test, feature_names)
    
    # 6. Salvar modelo
    save_model(model, feature_names, metrics, model_file)
    
    # 7. Decisão baseada em F1-Score
    print("=" * 80)
    print("RESUMO FINAL")
    print("=" * 80)
    print()
    
    f1 = metrics['f1_score']
    
    print(f"🎯 F1-Score obtido: {f1:.4f} ({f1*100:.2f}%)")
    print()
    
    # Interpretação do resultado
    if f1 >= 0.50:
        print("✅ EXCELENTE! F1-Score ≥ 0.50")
        print()
        print("📌 RECOMENDAÇÃO: Seguir PLANO A (Foco em ML)")
        print()
        print("Próximos passos:")
        print("  1. Atualizar ml_model/evaluation_report.md com métricas")
        print("  2. Integrar modelo na API (src/api/discount_service.py)")
        print("  3. Preparar slides focando em resultados de ML")
        print()
        print("Narrativa para TCC:")
        print("  'Modelo preditivo com métricas sólidas e aplicável ao problema real.'")
    
    elif 0.40 <= f1 < 0.50:
        print("⚠️  MODERADO. F1-Score entre 0.40 e 0.50")
        print()
        print("📌 RECOMENDAÇÃO: Seguir PLANO A.5 (Híbrido)")
        print()
        print("Próximos passos:")
        print("  1. Tentar melhorar features (adicionar histórico de 7/14 dias)")
        print("  2. Ajustar hiperparâmetros (GridSearch)")
        print("  3. Se não melhorar: balancear ML + Engenharia na apresentação")
        print()
        print("Narrativa para TCC:")
        print("  'Modelo captura padrões, mas limitado por features disponíveis.'")
    
    else:  # f1 < 0.40
        print("❌ BAIXO. F1-Score < 0.40")
        print()
        print("📌 RECOMENDAÇÃO: PIVOTAR para PLANO B (Foco em Engenharia)")
        print()
        print("Próximos passos:")
        print("  1. Aceitar modelo como Proof of Concept")
        print("  2. Focar em arquitetura, pipeline ETL, engenharia de dados")
        print("  3. Preparar slides enfatizando processo, não resultados")
        print()
        print("Narrativa para TCC:")
        print("  'Pipeline completo de ML em produção. Modelo valida metodologia,")
        print("   mas requer features externas (reviews, popularidade) para")
        print("   melhorar performance.'")
    
    print()
    print("=" * 80)
    print(f"✅ Treinamento concluído! Modelo salvo em: {model_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
