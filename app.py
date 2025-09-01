"""
PRYZOR - API Flask Mínima para Railway
=====================================
Versão mínima para resolver problemas de deploy
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import sys

# Logging básico
print("🔧 Python version:", sys.version)
print("🔧 Working directory:", os.getcwd())

# Inicialização da aplicação Flask
app = Flask(__name__)

# Configuração CORS mais permissiva para produção
CORS(app, origins=[
    "https://pryzor-front.vercel.app",
    "https://*.vercel.app", 
    "http://localhost:5173",
    "http://localhost:3000"
])

print("✅ Flask app criado com sucesso")

@app.route('/')
def home():
    """Rota raiz da API"""
    return jsonify({
        "message": "PRYZOR API - Online",
        "version": "1.0-minimal",
        "status": "ok"
    })

@app.route('/health')
def health_check():
    """Health check para Railway"""
    return jsonify({
        "status": "healthy",
        "service": "pryzor-backend"
    })

@app.route('/api/test')
def test_endpoint():
    """Endpoint de teste"""
    return jsonify({
        "success": True,
        "message": "API funcionando corretamente",
        "environment_vars": {
            "PORT": os.environ.get('PORT', 'not_set'),
            "RAILWAY_ENVIRONMENT": os.environ.get('RAILWAY_ENVIRONMENT', 'not_set')
        }
    })

@app.route('/api/games')
def listar_jogos():
    """Lista de jogos de demonstração"""
    sample_games = [
        {
            "steam_id": 730,
            "nome": "Counter-Strike 2",
            "preco_atual": 0.00,
            "desconto_atual": 0,
            "categoria": "FPS"
        },
        {
            "steam_id": 271590,
            "nome": "Grand Theft Auto V", 
            "preco_atual": 89.90,
            "desconto_atual": 50,
            "categoria": "Action"
        },
        {
            "steam_id": 292030,
            "nome": "The Witcher 3: Wild Hunt",
            "preco_atual": 149.99,
            "desconto_atual": 75,
            "categoria": "RPG"
        }
    ]
    
    return jsonify({
        "success": True,
        "data": sample_games,
        "total": len(sample_games),
        "source": "demo"
    })

@app.route('/api/predictions')
def obter_predicoes():
    """Predições de demonstração"""
    sample_predictions = [
        {
            "game": "Grand Theft Auto V",
            "current_price": 89.90,
            "predicted_price": 67.43,
            "trend_percent": -25.0,
            "recommendation": "COMPRAR"
        },
        {
            "game": "The Witcher 3: Wild Hunt",
            "current_price": 149.99,
            "predicted_price": 99.99,
            "trend_percent": -33.0,
            "recommendation": "AGUARDAR"
        }
    ]
    
    return jsonify({
        "success": True,
        "data": sample_predictions,
        "total": len(sample_predictions),
        "source": "demo"
    })

@app.route('/api/buy-analysis', methods=['GET', 'POST'])
def buy_analysis():
    """Análise de compra de jogos"""
    if request.method == 'GET':
        # Lista jogos disponíveis para análise
        games = [
            {
                "steam_id": 271590,
                "nome": "Grand Theft Auto V",
                "preco_atual": 89.90,
                "desconto_atual": 50
            },
            {
                "steam_id": 292030,
                "nome": "The Witcher 3: Wild Hunt", 
                "preco_atual": 149.99,
                "desconto_atual": 75
            }
        ]
        
        return jsonify({
            "success": True,
            "games": games
        })
    
    else:  # POST
        # Análise de compra específica
        data = request.get_json()
        
        # Simulação de análise
        score = 75  # Score base
        if data.get('preco_atual', 0) < 50:
            score += 10
        if data.get('desconto_atual', 0) > 50:
            score += 15
            
        return jsonify({
            "success": True,
            "analysis": {
                "score": min(score, 100),
                "recommendation": "COMPRAR" if score >= 70 else "AGUARDAR",
                "factors": ["Preço atrativo", "Desconto significativo"],
                "confidence": 85
            }
        })

@app.route('/api/temporal-validation')
def temporal_validation():
    """Validação temporal de predições"""
    validation_data = {
        "summary": {
            "total_predictions": 150,
            "unique_games": 10,
            "period_start": "2024-01-01",
            "period_end": "2024-08-31",
            "mean_error": 8.5,
            "median_error": 6.2,
            "max_error": 25.3,
            "mean_error_pct": 12.8,
            "r2_approx": 0.78
        }
    }
    
    return jsonify({
        "success": True,
        "data": validation_data
    })

if __name__ == '__main__':
    try:
        # Força uso da porta padrão para Railway se PORT não estiver definida corretamente
        port = int(os.environ.get('PORT', 5000))
        
        # Se a porta for 3306 (MySQL), use a porta padrão do Railway
        if port == 3306:
            port = 5000
            print("⚠️  PORT era 3306 (MySQL), mudando para 5000")
        
        print(f"🚀 Tentando iniciar na porta: {port}")
        print(f"🔧 PORT env var: {os.environ.get('PORT', 'não definida')}")
        
        # Debug das variáveis relacionadas a porta
        for key in sorted(os.environ.keys()):
            if 'PORT' in key.upper():
                print(f"   {key}={os.environ[key]}")
        
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        print(f"❌ Erro ao iniciar aplicação: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
