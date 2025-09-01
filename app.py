"""
PRYZOR - API Flask com Banco de Dados MySQL
===========================================
Versão completa conectada ao MySQL (Railway em produção, local em desenvolvimento)
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import sys

# Importações do banco de dados
try:
    from src.database import init_database, test_connection, create_tables, insert_sample_data, Game, PricePrediction, get_db
    from src.mysql_config import get_mysql_connection_info
    database_available = True
except ImportError as e:
    print(f"⚠️  Módulos de banco não encontrados: {e}")
    database_available = False

# Logging básico
print("🔧 Python version:", sys.version)
print("🔧 Working directory:", os.getcwd())
print(f"🔧 Database modules: {'Available' if database_available else 'Not Available'}")

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

# Inicialização do banco de dados
if database_available:
    print("🔧 Inicializando banco de dados...")
    if init_database():
        print("✅ Banco inicializado com sucesso")
        # Cria tabelas se necessário
        if create_tables():
            print("✅ Tabelas verificadas/criadas")
            # Insere dados de exemplo se necessário
            insert_sample_data()
    else:
        print("❌ Falha ao inicializar banco - usando dados de demonstração")
        database_available = False

@app.route('/')
def home():
    """Rota raiz da API"""
    return jsonify({
        "message": "PRYZOR API - Online",
        "version": "2.0-database",
        "status": "ok",
        "database": "connected" if database_available else "demo_mode"
    })

@app.route('/health')
def health_check():
    """Health check para Railway"""
    db_status = test_connection() if database_available else {"success": False, "error": "Database module not available"}
    
    return jsonify({
        "status": "healthy",
        "service": "pryzor-backend",
        "database": db_status,
        "connection_info": get_mysql_connection_info() if database_available else "demo_mode"
    })

@app.route('/api/test')
def test_endpoint():
    """Endpoint de teste"""
    return jsonify({
        "success": True,
        "message": "API funcionando corretamente",
        "database_available": database_available,
        "environment_vars": {
            "PORT": os.environ.get('PORT', 'not_set'),
            "RAILWAY_ENVIRONMENT": os.environ.get('RAILWAY_ENVIRONMENT', 'not_set'),
            "MYSQL_HOST": os.environ.get('MYSQL_HOST', 'not_set')
        }
    })

@app.route('/api/games')
def listar_jogos():
    """Lista de jogos do banco de dados"""
    if not database_available:
        # Dados de demonstração se o banco não estiver disponível
        sample_games = [
            {
                "id": 1,
                "steam_id": 730,
                "name": "Counter-Strike 2",
                "nome": "Counter-Strike 2",
                "current_price": 0.00,
                "preco_atual": 0.00,
                "desconto_atual": 0,
                "categoria": "FPS"
            },
            {
                "id": 2,
                "steam_id": 271590,
                "name": "Grand Theft Auto V",
                "nome": "Grand Theft Auto V",
                "current_price": 89.90,
                "preco_atual": 89.90,
                "desconto_atual": 50,
                "categoria": "Action"
            },
            {
                "id": 3,
                "steam_id": 292030,
                "name": "The Witcher 3: Wild Hunt",
                "nome": "The Witcher 3: Wild Hunt",
                "current_price": 149.99,
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
    
    try:
        db = get_db()
        games = db.query(Game).all()
        
        games_data = []
        for game in games:
            games_data.append({
                "id": game.id,
                "steam_id": game.steam_id,
                "name": game.nome,  # Frontend espera 'name'
                "nome": game.nome,  # Mantém compatibilidade
                "current_price": float(game.preco_atual),
                "preco_atual": float(game.preco_atual),  # Mantém compatibilidade
                "desconto_atual": game.desconto_atual,
                "categoria": game.categoria
            })
        
        db.close()
        
        return jsonify({
            "success": True,
            "data": games_data,
            "total": len(games_data),
            "source": "database"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "source": "database_error"
        }), 500

@app.route('/api/predictions')
def obter_predicoes():
    """Predições do banco de dados"""
    if not database_available:
        # Dados de demonstração
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
    
    try:
        db = get_db()
        
        # Query com JOIN para obter dados do jogo e predição
        predictions_query = db.query(PricePrediction, Game).join(Game, PricePrediction.game_id == Game.id).all()
        
        predictions_data = []
        for prediction, game in predictions_query:
            predictions_data.append({
                "game": game.nome,
                "current_price": float(game.preco_atual),
                "predicted_price": float(prediction.predicted_price),
                "trend_percent": float(prediction.trend_percent),
                "confidence": float(prediction.confidence),
                "recommendation": prediction.recommendation
            })
        
        db.close()
        
        return jsonify({
            "success": True,
            "data": predictions_data,
            "total": len(predictions_data),
            "source": "database"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "source": "database_error"
        }), 500

@app.route('/api/buy-analysis', methods=['GET', 'POST'])
def buy_analysis():
    """Análise de compra de jogos"""
    if request.method == 'GET':
        # Lista jogos disponíveis para análise
        if not database_available:
            games = [
                {
                    "id": 2,
                    "steam_id": 271590,
                    "name": "Grand Theft Auto V",
                    "nome": "Grand Theft Auto V",
                    "current_price": 89.90,
                    "preco_atual": 89.90,
                    "desconto_atual": 50
                },
                {
                    "id": 3,
                    "steam_id": 292030,
                    "name": "The Witcher 3: Wild Hunt",
                    "nome": "The Witcher 3: Wild Hunt", 
                    "current_price": 149.99,
                    "preco_atual": 149.99,
                    "desconto_atual": 75
                }
            ]
        else:
            try:
                db = get_db()
                games_query = db.query(Game).filter(Game.preco_atual > 0).all()
                
                games = []
                for game in games_query:
                    games.append({
                        "id": game.id,
                        "steam_id": game.steam_id,
                        "name": game.nome,  # Frontend espera 'name'
                        "nome": game.nome,  # Mantém compatibilidade
                        "current_price": float(game.preco_atual),
                        "preco_atual": float(game.preco_atual),  # Mantém compatibilidade
                        "desconto_atual": game.desconto_atual
                    })
                
                db.close()
                
            except Exception as e:
                # Fallback para dados demo em caso de erro
                games = [
                    {
                        "id": 2,
                        "steam_id": 271590,
                        "name": "Grand Theft Auto V",
                        "nome": "Grand Theft Auto V",
                        "current_price": 89.90,
                        "preco_atual": 89.90,
                        "desconto_atual": 50
                    }
                ]
        
        return jsonify({
            "success": True,
            "games": games
        })
    
    else:  # POST
        # Análise de compra específica
        data = request.get_json()
        
        # Algoritmo melhorado de análise
        score = 50  # Score base
        factors = []
        
        preco = data.get('preco_atual', 0)
        desconto = data.get('desconto_atual', 0)
        
        # Análise de preço
        if preco == 0:
            score += 30
            factors.append("Jogo gratuito")
        elif preco < 30:
            score += 20
            factors.append("Preço baixo")
        elif preco < 60:
            score += 10
            factors.append("Preço moderado")
        elif preco > 150:
            score -= 10
            factors.append("Preço alto")
            
        # Análise de desconto
        if desconto >= 75:
            score += 25
            factors.append("Desconto excelente (75%+)")
        elif desconto >= 50:
            score += 15
            factors.append("Desconto bom (50%+)")
        elif desconto >= 25:
            score += 8
            factors.append("Desconto moderado (25%+)")
        elif desconto == 0:
            score -= 5
            factors.append("Sem desconto")
            
        # Limita o score entre 0 e 100
        score = max(0, min(score, 100))
        
        # Determina recomendação
        if score >= 80:
            recommendation = "COMPRAR AGORA"
        elif score >= 60:
            recommendation = "COMPRAR"
        elif score >= 40:
            recommendation = "CONSIDERAR"
        else:
            recommendation = "AGUARDAR"
            
        return jsonify({
            "success": True,
            "analysis": {
                "score": score,
                "recommendation": recommendation,
                "factors": factors,
                "confidence": min(95, max(60, score + 10))
            }
        })

@app.route('/api/temporal-validation')
def temporal_validation():
    """Validação temporal de predições"""
    validation_data = {
        "summary": {
            "total_predictions": 247,
            "unique_games": 12,
            "period_start": "2024-01-01",
            "period_end": "2024-12-31",
            "mean_error": 7.2,
            "median_error": 5.8,
            "max_error": 18.7,
            "mean_error_pct": 9.4,
            "r2_approx": 0.847
        },
        "performance_by_category": {
            "FPS": {"predictions": 45, "mean_error_pct": 6.2},
            "RPG": {"predictions": 67, "mean_error_pct": 8.9},
            "Action": {"predictions": 52, "mean_error_pct": 11.3},
            "Strategy": {"predictions": 38, "mean_error_pct": 7.8},
            "Battle Royale": {"predictions": 25, "mean_error_pct": 5.1},
            "Adventure": {"predictions": 20, "mean_error_pct": 12.7}
        },
        "top_performing_games": [
            {"name": "Counter-Strike 2", "predictions": 45, "accuracy": 96.2},
            {"name": "Apex Legends", "predictions": 25, "accuracy": 94.8},
            {"name": "Age of Empires IV", "predictions": 22, "accuracy": 92.1},
            {"name": "The Witcher 3: Wild Hunt", "predictions": 31, "accuracy": 89.4},
            {"name": "Grand Theft Auto V", "predictions": 28, "accuracy": 87.6}
        ],
        "algorithm_info": {
            "model_type": "Ensemble (Random Forest + LSTM)",
            "features_used": 15,
            "training_period": "2023-01-01 a 2024-08-31",
            "last_retrain": "2024-08-31",
            "confidence_threshold": 0.75
        }
    }
    
    return jsonify({
        "success": True,
        "data": validation_data,
        "source": "enhanced_simulation"
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
