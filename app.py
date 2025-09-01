"""
PRYZOR - API Flask Simplificada para Railway
============================================
Versão simplificada para debugging no Railway
"""

from flask import Flask, jsonify
from flask_cors import CORS
import os

# Inicialização da aplicação Flask
app = Flask(__name__)
CORS(app)

print("🚀 Iniciando aplicação PRYZOR...")

@app.route('/')
def home():
    """Rota raiz da API - informações básicas do sistema."""
    return jsonify({
        "message": "API PRYZOR - Sistema de Análise de Preços Steam",
        "version": "1.0-simple",
        "status": "online",
        "environment": "railway"
    })

@app.route('/health')
def health_check():
    """Verifica se a API está funcionando."""
    return jsonify({
        "status": "ok", 
        "message": "API PRYZOR funcionando",
        "projeto": "Sistema de Análise de Preços Steam"
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
        }
    ]
    
    return jsonify({
        "success": True,
        "data": sample_predictions,
        "total": len(sample_predictions),
        "source": "demo"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Iniciando servidor na porta {port}")
    print(f"🔧 Variáveis de ambiente disponíveis:")
    for key in sorted(os.environ.keys()):
        if any(keyword in key.upper() for keyword in ['PORT', 'MYSQL', 'RAILWAY']):
            print(f"   {key}={os.environ[key]}")
    app.run(host='0.0.0.0', port=port, debug=False)
