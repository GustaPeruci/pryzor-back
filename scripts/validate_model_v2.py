"""
Script de Validação do Modelo v2.0 em Casos Reais

Objetivo: Testar modelo v2.0 em 50 jogos aleatórios (não gratuitos)
          para verificar acurácia das predições comparando:
          - Penúltimo preço (usado para predição)
          - Último preço (resultado real)

Metodologia:
1. Selecionar 50 jogos aleatórios pagos do dataset
2. Para cada jogo:
   - Pegar penúltimo registro (simula momento da predição)
   - Fazer predição com modelo v2.0
   - Comparar com último registro (resultado real)
3. Calcular métricas de acerto/erro
4. Identificar padrões de falhas

Autor: Pryzor Team
Data: 23/10/2025
"""

import pandas as pd
import numpy as np
import pickle
from pathlib import Path
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')


def load_model(model_path: Path):
    """Carrega modelo treinado"""
    print("📦 CARREGANDO MODELO v2.0")
    print("-" * 80)
    
    with open(model_path, 'rb') as f:
        model_pkg = pickle.load(f)
    
    print(f"✅ Modelo carregado: {model_pkg.get('version', 'unknown')}")
    print(f"📊 Features: {len(model_pkg['feature_names'])}")
    print(f"🎯 F1-Score: {model_pkg['metrics']['f1_score']:.4f}")
    print()
    
    return model_pkg


def load_dataset(data_dir: Path, app_info_path: Path):
    """Carrega dataset completo de múltiplos arquivos CSV"""
    print("📖 CARREGANDO DATASET")
    print("-" * 80)
    
    # Carregar informações dos jogos (tentar diferentes encodings)
    try:
        app_info = pd.read_csv(app_info_path, encoding='utf-8')
    except UnicodeDecodeError:
        try:
            app_info = pd.read_csv(app_info_path, encoding='latin-1')
        except:
            app_info = pd.read_csv(app_info_path, encoding='cp1252')
    
    print(f"✅ {len(app_info):,} jogos no catálogo")
    
    # Listar todos os arquivos CSV de histórico de preço
    price_files = list(data_dir.glob('*.csv'))
    print(f"📁 {len(price_files):,} arquivos de histórico encontrados")
    
    # Carregar todos os históricos
    all_data = []
    for price_file in price_files:
        appid = int(price_file.stem)  # Nome do arquivo é o appid
        df = pd.read_csv(price_file)
        
        # Renomear colunas para lowercase
        df.columns = df.columns.str.lower()
        
        # Renomear colunas específicas
        df = df.rename(columns={
            'initialprice': 'initial_price',
            'finalprice': 'final_price'
        })
        
        df['appid'] = appid
        all_data.append(df)
    
    df = pd.concat(all_data, ignore_index=True)
    df['date'] = pd.to_datetime(df['date'])
    
    # Merge com informações dos jogos
    df = df.merge(app_info[['appid', 'name', 'freetoplay']], on='appid', how='left')
    
    print(f"✅ {len(df):,} registros de preço carregados")
    print(f"📅 Período: {df['date'].min().date()} a {df['date'].max().date()}")
    print()
    
    return df


def select_test_games(df, n_games=1000, min_records=60):
    """
    Seleciona jogos aleatórios para teste
    
    Critérios:
    - Jogos pagos (freetoplay = 0)
    - Pelo menos 60 registros (para ter histórico)
    - Deve ter variação de preço (não apenas preço fixo)
    """
    print("🎲 SELECIONANDO JOGOS PARA TESTE")
    print("-" * 80)
    
    # Filtrar jogos pagos
    paid_games = df[df['freetoplay'] == 0].copy()
    
    # Contar registros por jogo
    game_counts = paid_games.groupby('appid').size()
    valid_games = game_counts[game_counts >= min_records].index
    
    print(f"📊 Jogos pagos: {len(game_counts):,}")
    print(f"✅ Jogos com ≥{min_records} registros: {len(valid_games):,}")
    
    # Filtrar jogos com variação de preço
    games_with_variation = []
    for appid in valid_games:
        game_data = paid_games[paid_games['appid'] == appid]
        price_std = game_data['final_price'].std()
        if price_std > 0.01:  # Tem variação de preço
            games_with_variation.append(appid)
    
    print(f"🔄 Jogos com variação de preço: {len(games_with_variation):,}")
    
    # Selecionar aleatoriamente
    np.random.seed(42)  # Reprodutibilidade
    selected_games = np.random.choice(
        games_with_variation, 
        size=min(n_games, len(games_with_variation)), 
        replace=False
    )
    
    print(f"✅ {len(selected_games)} jogos selecionados para teste")
    print()
    
    return selected_games


def extract_features(row, feature_names):
    """Extrai features de uma linha do dataset"""
    # Criar features temporais se não existirem
    if 'month' not in row or pd.isna(row.get('month')):
        date = row['date']
        row_dict = row.to_dict()
        row_dict['month'] = date.month
        row_dict['quarter'] = (date.month - 1) // 3 + 1
        row_dict['day_of_week'] = date.dayofweek
        row_dict['is_weekend'] = int(date.dayofweek >= 5)
        
        # Steam sales (aproximado)
        row_dict['is_summer_sale'] = int(date.month == 6 or date.month == 7)
        row_dict['is_winter_sale'] = int(date.month == 12 or date.month == 1)
        
        # Converter de volta para Series
        row = pd.Series(row_dict)
    
    features = []
    for feat in feature_names:
        if feat in row:
            features.append(row[feat])
        else:
            features.append(0)  # Default para features faltantes
    
    return np.array(features).reshape(1, -1)


def make_prediction(model, features):
    """Faz predição e retorna probabilidade"""
    pred = model.predict(features)[0]
    prob = model.predict_proba(features)[0]
    
    return {
        'prediction': int(pred),
        'probability': float(prob[1]),  # Probabilidade de desconto
        'confidence': float(abs(prob[1] - 0.5) * 2)
    }


def analyze_game(df, appid, model, feature_names):
    """
    Analisa um jogo específico
    
    Método:
    1. Pegar penúltimo registro (momento da predição)
    2. Fazer predição com modelo
    3. Pegar último registro (resultado real)
    4. Comparar predição vs realidade
    """
    game_data = df[df['appid'] == appid].sort_values('date').copy()
    
    if len(game_data) < 2:
        return None
    
    # Penúltimo registro (momento da predição)
    penultimate = game_data.iloc[-2]
    
    # Último registro (resultado real)
    last = game_data.iloc[-1]
    
    # Extrair features do penúltimo registro
    features = extract_features(penultimate, feature_names)
    
    # Fazer predição
    prediction = make_prediction(model, features)
    
    # Calcular resultado real
    days_diff = (last['date'] - penultimate['date']).days
    
    # Determinar se houve desconto significativo (>20%)
    penultimate_discount = penultimate['discount']
    last_discount = last['discount']
    
    # Calcular mudança de preço
    price_change_pct = ((last['final_price'] - penultimate['final_price']) 
                        / penultimate['final_price'] * 100)
    
    # Determinar resultado real
    if last_discount >= 20 and penultimate_discount < 20:
        real_result = 1  # Teve desconto novo
        result_label = "DESCONTO NOVO"
    elif last_discount >= 20 and penultimate_discount >= 20:
        real_result = 1  # Desconto continuou
        result_label = "DESCONTO CONTINUOU"
    elif price_change_pct > 5:
        real_result = 0  # Preço aumentou
        result_label = "PREÇO AUMENTOU"
    elif penultimate_discount > 0 and last_discount == 0:
        real_result = 0  # Desconto terminou
        result_label = "DESCONTO TERMINOU"
    else:
        real_result = 0  # Sem desconto
        result_label = "SEM DESCONTO"
    
    # Verificar se predição estava correta
    predicted_label = "AGUARDAR" if prediction['prediction'] == 1 else "COMPRAR AGORA"
    correct = (prediction['prediction'] == real_result)
    
    return {
        'appid': appid,
        'game_name': game_data['name'].iloc[0] if 'name' in game_data.columns else f"Game {appid}",
        'penultimate_date': penultimate['date'],
        'penultimate_price': penultimate['final_price'],
        'penultimate_discount': penultimate_discount,
        'last_date': last['date'],
        'last_price': last['final_price'],
        'last_discount': last_discount,
        'days_between': days_diff,
        'price_change_pct': price_change_pct,
        'prediction': prediction['prediction'],
        'predicted_label': predicted_label,
        'probability': prediction['probability'],
        'confidence': prediction['confidence'],
        'real_result': real_result,
        'result_label': result_label,
        'correct': correct
    }


def run_validation(df, selected_games, model_pkg):
    """Executa validação em todos os jogos selecionados"""
    print("🧪 EXECUTANDO VALIDAÇÃO")
    print("=" * 80)
    print()
    
    model = model_pkg['model']
    feature_names = model_pkg['feature_names']
    
    results = []
    
    for i, appid in enumerate(selected_games, 1):
        print(f"[{i:2d}/{len(selected_games)}] Analisando jogo {appid}...", end=' ')
        
        result = analyze_game(df, appid, model, feature_names)
        
        if result:
            results.append(result)
            status = "✅" if result['correct'] else "❌"
            print(f"{status} {result['predicted_label']} → {result['result_label']}")
        else:
            print("⚠️  Dados insuficientes")
    
    print()
    return pd.DataFrame(results)


def analyze_results(results_df):
    """Analisa resultados da validação"""
    print("\n" + "=" * 80)
    print("📊 ANÁLISE DOS RESULTADOS")
    print("=" * 80)
    print()
    
    # Métricas gerais
    total = len(results_df)
    correct = results_df['correct'].sum()
    incorrect = total - correct
    accuracy = (correct / total * 100) if total > 0 else 0
    
    print("📈 MÉTRICAS GERAIS")
    print("-" * 80)
    print(f"   Total de testes: {total}")
    print(f"   ✅ Acertos: {correct} ({accuracy:.1f}%)")
    print(f"   ❌ Erros: {incorrect} ({100-accuracy:.1f}%)")
    print()
    
    # Análise por tipo de resultado real
    print("📊 DISTRIBUIÇÃO POR RESULTADO REAL")
    print("-" * 80)
    result_counts = results_df['result_label'].value_counts()
    for label, count in result_counts.items():
        pct = (count / total * 100)
        correct_in_category = results_df[
            (results_df['result_label'] == label) & (results_df['correct'])
        ].shape[0]
        acc_in_category = (correct_in_category / count * 100) if count > 0 else 0
        print(f"   {label:20s}: {count:3d} ({pct:5.1f}%) - Acerto: {acc_in_category:5.1f}%")
    print()
    
    # Análise de erros
    errors_df = results_df[~results_df['correct']].copy()
    
    if len(errors_df) > 0:
        print("❌ ANÁLISE DE ERROS")
        print("-" * 80)
        
        # Tipo de erro mais comum
        error_types = errors_df.groupby(['predicted_label', 'result_label']).size()
        print("\n   Tipos de erro mais comuns:")
        for (pred, real), count in error_types.sort_values(ascending=False).head(5).items():
            print(f"      {pred:15s} → {real:20s}: {count:2d} casos")
        
        print()
        
        # Análise de mudança de preço nos erros
        print("   Mudança de preço nos erros:")
        price_increases = errors_df[errors_df['price_change_pct'] > 5]
        price_decreases = errors_df[errors_df['price_change_pct'] < -5]
        price_stable = errors_df[errors_df['price_change_pct'].abs() <= 5]
        
        print(f"      Preço aumentou (>5%): {len(price_increases)} casos")
        print(f"      Preço caiu (<-5%): {len(price_decreases)} casos")
        print(f"      Preço estável (±5%): {len(price_stable)} casos")
        print()
        
        # Casos similares ao Stardew Valley
        stardew_like = errors_df[
            (errors_df['predicted_label'] == 'AGUARDAR') & 
            ((errors_df['result_label'] == 'PREÇO AUMENTOU') | 
             (errors_df['result_label'] == 'DESCONTO TERMINOU'))
        ]
        
        if len(stardew_like) > 0:
            print(f"   ⚠️  CASOS SIMILARES AO STARDEW VALLEY: {len(stardew_like)}")
            print(f"      Previu 'AGUARDAR' mas desconto terminou ou preço subiu")
            print(f"      Representa {len(stardew_like)/len(errors_df)*100:.1f}% dos erros")
            print()
    
    # Top 10 piores casos (maior confiança + erro)
    print("🔴 TOP 10 PIORES ERROS (maior confiança, mas errou)")
    print("-" * 80)
    worst_errors = errors_df.nlargest(10, 'confidence')
    for idx, row in worst_errors.iterrows():
        print(f"   {row['game_name'][:30]:30s}")
        print(f"      Previu: {row['predicted_label']:15s} (conf: {row['confidence']*100:.1f}%)")
        print(f"      Real:   {row['result_label']:15s}")
        print(f"      Preço:  ${row['penultimate_price']:.2f} → ${row['last_price']:.2f} " +
              f"({row['price_change_pct']:+.1f}%)")
        print()
    
    return {
        'accuracy': accuracy,
        'total': total,
        'correct': correct,
        'incorrect': incorrect,
        'stardew_like_cases': len(stardew_like) if len(errors_df) > 0 else 0
    }


def generate_action_plan(results_df, metrics):
    """Gera plano de ação baseado nos resultados"""
    print("\n" + "=" * 80)
    print("🎯 PLANO DE AÇÃO")
    print("=" * 80)
    print()
    
    accuracy = metrics['accuracy']
    stardew_cases = metrics['stardew_like_cases']
    total_errors = metrics['incorrect']
    
    # Classificar gravidade
    if accuracy >= 75:
        severity = "BOA"
        emoji = "✅"
    elif accuracy >= 60:
        severity = "MODERADA"
        emoji = "⚠️"
    else:
        severity = "CRÍTICA"
        emoji = "❌"
    
    print(f"{emoji} AVALIAÇÃO GERAL: {severity}")
    print(f"   Acurácia: {accuracy:.1f}%")
    print()
    
    # Análise do caso Stardew
    if stardew_cases > 0:
        stardew_pct = (stardew_cases / total_errors * 100) if total_errors > 0 else 0
        
        if stardew_pct > 30:
            print(f"⚠️  PROBLEMA RECORRENTE: Casos tipo Stardew")
            print(f"   {stardew_cases} de {total_errors} erros ({stardew_pct:.1f}%)")
            print(f"   Modelo tem dificuldade em detectar FIM de promoções")
            print()
            print("📌 AÇÃO RECOMENDADA:")
            print("   1. Adicionar features de DURAÇÃO de promoção")
            print("   2. Implementar regras de negócio para promoções longas")
            print("   3. Retreinar modelo com essas features")
            print()
        else:
            print(f"ℹ️  Caso Stardew é ISOLADO ou RARO")
            print(f"   Apenas {stardew_cases} de {total_errors} erros ({stardew_pct:.1f}%)")
            print()
            print("📌 AÇÃO RECOMENDADA:")
            print("   1. Manter modelo v2.0 atual")
            print("   2. Adicionar regra de negócio específica:")
            print("      'Se promoção ativa há >5 dias, reduzir confiança em 30%'")
            print("   3. Monitorar casos similares em produção")
            print()
    else:
        print("✅ Nenhum caso similar ao Stardew detectado")
        print()
    
    # Recomendações baseadas em acurácia
    if accuracy >= 75:
        print("✅ MODELO v2.0 ESTÁ BOM")
        print("   Recomendações:")
        print("   1. Deploy do modelo atual em produção")
        print("   2. Adicionar regras de negócio simples (se necessário)")
        print("   3. Monitorar performance em produção")
        print("   4. Coletar feedback de usuários")
        print()
    elif accuracy >= 60:
        print("⚠️  MODELO PRECISA DE AJUSTES")
        print("   Recomendações:")
        print("   1. Analisar padrões de erro (feito acima)")
        print("   2. Adicionar 2-3 features específicas para casos problemáticos")
        print("   3. Retreinar modelo v2.1 com ajustes incrementais")
        print("   4. Re-validar com os mesmos 50 jogos")
        print()
    else:
        print("❌ MODELO PRECISA DE REVISÃO PROFUNDA")
        print("   Recomendações:")
        print("   1. Revisar features (adicionar histórico de longo prazo)")
        print("   2. Considerar reformular target (multi-classe)")
        print("   3. Implementar ensemble de modelos")
        print("   4. Aumentar dataset de treinamento")
        print()


def save_results(results_df, output_path: Path):
    """Salva resultados em CSV"""
    results_df.to_csv(output_path, index=False)
    print(f"\n💾 Resultados salvos em: {output_path}")


def main():
    """Função principal"""
    print("=" * 80)
    print("VALIDAÇÃO DO MODELO v2.0 EM CASOS REAIS")
    print("=" * 80)
    print()
    
    # Caminhos
    backend_root = Path(__file__).parent.parent
    price_dir = backend_root / "data" / "PriceHistory"
    app_info_file = backend_root / "data" / "applicationInformation.csv"
    model_file = backend_root / "ml_model" / "discount_predictor.pkl"
    output_file = backend_root / "tests" / "validation_results_v2.csv"
    
    # Verificar arquivos
    if not price_dir.exists():
        print(f"❌ Diretório de preços não encontrado: {price_dir}")
        return
    
    if not app_info_file.exists():
        print(f"❌ Arquivo de informações não encontrado: {app_info_file}")
        return
    
    if not model_file.exists():
        print(f"❌ Modelo não encontrado: {model_file}")
        return
    
    # 1. Carregar modelo
    model_pkg = load_model(model_file)
    
    # 2. Carregar dataset
    df = load_dataset(price_dir, app_info_file)
    
    # 3. Selecionar jogos para teste
    selected_games = select_test_games(df, n_games=1000)
    
    # 4. Executar validação
    results_df = run_validation(df, selected_games, model_pkg)
    
    # 5. Analisar resultados
    metrics = analyze_results(results_df)
    
    # 6. Gerar plano de ação
    generate_action_plan(results_df, metrics)
    
    # 7. Salvar resultados
    save_results(results_df, output_file)
    
    print("\n" + "=" * 80)
    print("✅ VALIDAÇÃO CONCLUÍDA!")
    print("=" * 80)


if __name__ == "__main__":
    main()
