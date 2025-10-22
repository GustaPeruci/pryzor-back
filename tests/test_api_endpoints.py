"""
Script de Testes dos Endpoints da API Pryzor
Testa todos os principais endpoints do sistema
"""

import requests
import json
from datetime import datetime

API_BASE = "http://localhost:8000"

def print_section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def test_endpoint(name, url, method="GET", data=None):
    """Testa um endpoint e imprime o resultado"""
    print(f"\n📡 {name}")
    print(f"   {method} {url}")
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=5)
        
        print(f"   Status: {response.status_code} {'✅' if response.status_code < 400 else '❌'}")
        
        if response.status_code == 200:
            result = response.json()
            # Limitar tamanho da saída
            result_str = json.dumps(result, indent=2, ensure_ascii=False)
            if len(result_str) > 500:
                result_str = result_str[:500] + "\n   ... (truncado)"
            print(f"   Resposta:\n{result_str}")
        else:
            print(f"   Erro: {response.text[:200]}")
        
        return response.status_code == 200
        
    except requests.exceptions.ConnectionError:
        print("   ❌ ERRO: API não está rodando!")
        print("   Execute: python src/main.py")
        return False
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        return False

def main():
    print("\n" + "🎯" * 40)
    print("  TESTES DOS ENDPOINTS - PRYZOR API")
    print("🎯" * 40)
    
    results = []
    
    # ========================================================================
    # TESTES - SISTEMA
    # ========================================================================
    
    print_section("1. ENDPOINTS DO SISTEMA")
    
    results.append(("GET /", test_endpoint(
        "Raiz da API",
        f"{API_BASE}/"
    )))
    
    results.append(("GET /health", test_endpoint(
        "Health Check",
        f"{API_BASE}/health"
    )))
    
    results.append(("GET /api/stats", test_endpoint(
        "Estatísticas do Sistema",
        f"{API_BASE}/api/stats"
    )))
    
    # ========================================================================
    # TESTES - DADOS
    # ========================================================================
    
    print_section("2. ENDPOINTS DE DADOS")
    
    results.append(("GET /api/games", test_endpoint(
        "Listar Jogos (limit=5)",
        f"{API_BASE}/api/games?limit=5"
    )))
    
    results.append(("GET /api/games (busca)", test_endpoint(
        "Buscar Jogos (search='Counter')",
        f"{API_BASE}/api/games?search=Counter&limit=3"
    )))
    
    results.append(("GET /api/games/730", test_endpoint(
        "Detalhes do CS:GO (appid=730)",
        f"{API_BASE}/api/games/730"
    )))
    
    # ========================================================================
    # TESTES - MACHINE LEARNING
    # ========================================================================
    
    print_section("3. ENDPOINTS DE MACHINE LEARNING")
    
    results.append(("GET /api/ml/health", test_endpoint(
        "Health Check ML",
        f"{API_BASE}/api/ml/health"
    )))
    
    results.append(("GET /api/ml/info", test_endpoint(
        "Informações do Modelo",
        f"{API_BASE}/api/ml/info"
    )))
    
    results.append(("GET /api/ml/predict/730", test_endpoint(
        "Predição CS:GO (appid=730)",
        f"{API_BASE}/api/ml/predict/730"
    )))
    
    results.append(("GET /api/ml/predict/271590", test_endpoint(
        "Predição GTA V (appid=271590)",
        f"{API_BASE}/api/ml/predict/271590"
    )))
    
    results.append(("POST /api/ml/predict/batch", test_endpoint(
        "Predição em Lote (3 jogos)",
        f"{API_BASE}/api/ml/predict/batch",
        method="POST",
        data={"appids": [730, 440, 570]}  # CS:GO, TF2, Dota 2
    )))
    
    # ========================================================================
    # RESUMO
    # ========================================================================
    
    print_section("RESUMO DOS TESTES")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    print(f"\n{'=' * 80}")
    print(f"  Total: {passed}/{total} testes passaram ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("  ✅ TODOS OS TESTES PASSARAM!")
    elif passed > total * 0.7:
        print("  ⚠️ MAIORIA DOS TESTES PASSOU")
    else:
        print("  ❌ MUITOS TESTES FALHARAM")
    
    print("=" * 80)
    print()
    
    return passed == total

if __name__ == "__main__":
    print("\n⚠️ CERTIFIQUE-SE DE QUE A API ESTÁ RODANDO!")
    print("   Execute em outro terminal: python src/main.py\n")
    
    input("Pressione ENTER quando a API estiver rodando...")
    
    success = main()
    
    if not success:
        print("\n💡 DICA: Verifique se a API está rodando e acessível em http://localhost:8000")
