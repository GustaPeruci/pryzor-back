"""
Script de teste para validação da integração do modelo ML v2.0
Testa os endpoints da API e o serviço de predição
"""

import sys
import os
import requests
import time
from typing import Dict, Any

# Adicionar path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from api.ml_discount_predictor import MLDiscountPredictor

# Configuração
API_BASE_URL = "http://127.0.0.1:8000"
MYSQL_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', os.getenv('DB_PASS', 'root')),
    'database': os.getenv('DB_NAME', 'steam_pryzor')
}

def print_section(title: str):
    """Imprime seção formatada"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_result(name: str, passed: bool, details: str = ""):
    """Imprime resultado de teste"""
    status = "✅ PASSOU" if passed else "❌ FALHOU"
    print(f"{status} - {name}")
    if details:
        print(f"         {details}")

def test_direct_service():
    """Testa o serviço diretamente (sem API)"""
    print_section("TESTE 1: Serviço ML Direto (sem API)")
    
    try:
        predictor = MLDiscountPredictor(MYSQL_CONFIG)
        
        # Teste 1.1: Modelo carregado
        loaded = predictor.is_loaded()
        print_result("Modelo carregado", loaded)
        
        if not loaded:
            print("\n⚠️ ATENÇÃO: Modelo não foi carregado!")
            print("   Verifique se o arquivo existe em: pryzor-back/ml_model/discount_predictor.pkl")
            return False
        
        # Teste 1.2: Informações do modelo
        info = predictor.get_model_info()
        print_result("Info do modelo", True, 
                    f"v{info['version']}, {info['features_count']} features, F1={info['metrics']['f1_score']:.4f}")
        
        # Teste 1.3: Predição para um jogo conhecido (Counter-Strike: Global Offensive - appid 730)
        print("\n📊 Testando predição para CS:GO (appid 730)...")
        result = predictor.predict(730)
        
        if 'error' in result:
            print_result("Predição CS:GO", False, f"Erro: {result['error']}")
            return False
        
        print_result("Predição CS:GO", True)
        print(f"   Jogo: {result.get('game_name', 'N/A')}")
        print(f"   Terá desconto >20%? {result['will_have_discount']}")
        print(f"   Probabilidade: {result['probability']:.2%}")
        print(f"   Confiança: {result['confidence']:.2%}")
        print(f"   Desconto atual: {result['current_discount']:.0f}%")
        print(f"   Recomendação: {result['recommendation']}")
        
        # Teste 1.4: Predição em lote
        print("\n📊 Testando predição em lote (3 jogos)...")
        batch_result = predictor.batch_predict([730, 440, 570])  # CS:GO, TF2, Dota 2
        
        print_result("Predição em lote", True, 
                    f"{batch_result['successful']} sucessos, {batch_result['failed']} falhas")
        
        for pred in batch_result['predictions'][:3]:
            print(f"   • {pred['game_name']}: prob={pred['probability']:.2%}")
        
        return True
        
    except Exception as e:
        print_result("Serviço ML Direto", False, f"Exceção: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_endpoints():
    """Testa os endpoints da API"""
    print_section("TESTE 2: Endpoints da API")
    # CI/CD: Não usar input(), apenas tentar conectar
    try:
        # Teste 2.1: Health check
        print("\n🔍 Testando /api/ml/v2/health...")
        response = requests.get(f"{API_BASE_URL}/api/ml/v2/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_result("Health check", data['model_loaded'], f"Status: {data['status']}, v{data['version']}")
        else:
            print_result("Health check", False, f"Status code: {response.status_code}")
            return False

        # Teste 2.2: Model info
        print("\n🔍 Testando /api/ml/v2/info...")
        response = requests.get(f"{API_BASE_URL}/api/ml/v2/info", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_result("Model info", True, f"F1={data['metrics']['f1_score']:.4f}, Precision={data['metrics']['precision']:.4f}")
        else:
            print_result("Model info", False, f"Status code: {response.status_code}")

        # Teste 2.3: Predição única
        print("\n🔍 Testando /api/ml/v2/predict/730 (CS:GO)...")
        response = requests.get(f"{API_BASE_URL}/api/ml/v2/predict/730", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print_result("Predição única", True)
            print(f"   Jogo: {data.get('game_name', 'N/A')}")
            print(f"   Probabilidade: {data['probability']:.2%}")
            print(f"   Recomendação: {data['recommendation']}")
        else:
            print_result("Predição única", False, f"Status code: {response.status_code}")

        # Teste 2.4: Predição em lote
        print("\n🔍 Testando /api/ml/v2/predict/batch...")
        payload = {"appids": [730, 440, 570]}
        response = requests.post(f"{API_BASE_URL}/api/ml/v2/predict/batch", json=payload, timeout=15)
        if response.status_code == 200:
            data = response.json()
            print_result("Predição em lote", True, f"{data['successful']}/{data['total_requested']} sucessos")
            for pred in data['predictions'][:3]:
                print(f"   • {pred['game_name']}: {pred['probability']:.2%}")
        else:
            print_result("Predição em lote", False, f"Status code: {response.status_code}")

        return True

    except requests.exceptions.ConnectionError:
        print_result("API Endpoints", False, "Não foi possível conectar à API. Ela está rodando?")
        assert False, "A API não está rodando em http://127.0.0.1:8000 durante o teste automatizado. Suba a API antes de rodar os testes."

    except Exception as e:
        print_result("API Endpoints", False, f"Exceção: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_edge_cases():
    """Testa casos especiais"""
    print_section("TESTE 3: Casos Especiais")
    
    try:
        predictor = MLDiscountPredictor(MYSQL_CONFIG)
        
        # Teste 3.1: Jogo inexistente
        print("\n🔍 Testando jogo inexistente (appid 999999999)...")
        result = predictor.predict(999999999)
        has_error = 'error' in result
        print_result("Jogo inexistente retorna erro", has_error, 
                    f"Erro: {result.get('error', 'N/A')}")
        
        # Teste 3.2: Jogo free-to-play (Team Fortress 2 - appid 440)
        print("\n🔍 Testando jogo free-to-play (TF2 - appid 440)...")
        result = predictor.predict(440)
        is_free = result.get('recommendation', '').lower().find('gratuito') >= 0 or result.get('probability', 1) == 0
        print_result("Free-to-play detectado", is_free, 
                    f"Rec: {result.get('recommendation', 'N/A')}")
        
        return True
        
    except Exception as e:
        print_result("Casos Especiais", False, f"Exceção: {e}")
        return False

def main():
    """Executa todos os testes"""
    print("\n" + "🎯" * 40)
    print("  TESTE DE INTEGRAÇÃO - MODELO ML v2.0 no PRYZOR-BACK")
    print("🎯" * 40)
    
    results = []
    
    # Teste 1: Serviço direto
    results.append(("Serviço ML Direto", test_direct_service()))
    
    # Teste 2: API endpoints
    results.append(("Endpoints da API", test_api_endpoints()))
    
    # Teste 3: Casos especiais
    results.append(("Casos Especiais", test_edge_cases()))
    
    # Resumo
    print_section("RESUMO DOS TESTES")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        print_result(name, result)
    
    print(f"\n{'=' * 80}")
    print(f"  Total: {passed}/{total} testes passaram")
    
    if passed == total:
        print("  ✅ TODOS OS TESTES PASSARAM - Sistema pronto para uso!")
    else:
        print("  ⚠️ ALGUNS TESTES FALHARAM - Verifique os erros acima")
    
    print("=" * 80)
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
