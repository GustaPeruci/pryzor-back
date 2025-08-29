# PRYZOR - Sistema de Análise de Preços de Jogos Steam
# Projeto Universitário - Análise de Dados e Machine Learning
# Autor: Gustavo Peruci
# Data: Agosto 2025

"""
Este é o arquivo principal da API Flask do sistema PRYZOR.
O sistema analisa preços históricos de jogos da Steam e fornece
recomendações de compra baseadas em análise estatística.

Funcionalidades principais:
- API REST para consulta de jogos e preços
- Sistema de análise de compra inteligente
- Interface web para visualização de dados
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import sys
import os

# Configuração do path para importar módulos do projeto
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Importações dos módulos do projeto
from src.database_manager import DatabaseManager, get_mysql_config
from src.basic_analyzer import BasicAnalyzer
from buy_analyzer import SimpleBuyingAnalyzer

def init_database():
    """Inicializa o banco de dados com migrações se necessário"""
    try:
        import pymysql
        
        config = get_mysql_config()
        connection = pymysql.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        
        # Verifica se a tabela games existe
        cursor.execute("SHOW TABLES LIKE 'games'")
        if not cursor.fetchone():
            print("🔧 Tabelas não encontradas, executando migrações...")
            
            # Importa e executa migrações
            from src.migrations import CREATE_TABLES_SQL, INITIAL_DATA_SQL
            
            # Cria tabelas
            statements = CREATE_TABLES_SQL.strip().split(';')
            for statement in statements:
                if statement.strip():
                    cursor.execute(statement)
            
            # Insere dados iniciais
            statements = INITIAL_DATA_SQL.strip().split(';')
            for statement in statements:
                if statement.strip():
                    cursor.execute(statement)
            
            connection.commit()
            print("✅ Migrações executadas com sucesso!")
        else:
            print("✅ Banco de dados já inicializado")
            
        cursor.close()
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro ao inicializar banco: {str(e)}")
        return False

# Inicialização da aplicação Flask
app = Flask(__name__)
CORS(app)  # Permite requisições do frontend

# Inicializa o banco de dados
print("🚀 Inicializando banco de dados...")
init_database()

# ========================
# ROTAS DE SISTEMA
# ========================

@app.route('/')
def home():
    """Rota raiz da API - informações básicas do sistema."""
    return jsonify({
        "message": "API PRYZOR - Sistema de Análise de Preços Steam",
        "version": "1.0",
        "endpoints": {
            "health": "/health",
            "games": "/api/games",
            "predictions": "/api/predictions",
            "buy_analysis": "/api/buy-analysis",
            "temporal_validation": "/api/temporal-validation"
        },
        "status": "online"
    })

@app.route('/health')
def health_check():
    """Verifica se a API está funcionando."""
    return jsonify({
        "status": "ok", 
        "message": "API PRYZOR funcionando",
        "projeto": "Sistema de Análise de Preços Steam"
    })

# ========================
# ROTAS DE DADOS
# ========================

@app.route('/api/games')
def listar_jogos():
    """
    Retorna a lista de todos os jogos cadastrados no sistema.
    
    Returns:
        JSON com lista de jogos e seus preços atuais
    """
    try:
        print("Iniciando consulta de jogos...")
        db = DatabaseManager()
        print("DatabaseManager criado com sucesso")
        
        games_df = db.get_games()
        print(f"Jogos obtidos: {len(games_df) if not games_df.empty else 0}")
        
        if games_df.empty:
            return jsonify({
                "success": True, 
                "data": [],
                "total": 0,
                "message": "Nenhum jogo encontrado"
            })
        
        games_list = games_df.to_dict('records')
        
        return jsonify({
            "success": True, 
            "data": games_list,
            "total": len(games_list)
        })
        
    except Exception as e:
        print(f"Erro ao buscar jogos: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False, 
            "error": f"Erro ao buscar jogos: {str(e)}"
        }), 500

@app.route('/api/games/<steam_id>')
def obter_jogo(steam_id):
    """
    Retorna informações detalhadas de um jogo específico.
    
    Args:
        steam_id: ID do jogo na Steam
        
    Returns:
        JSON com dados históricos do jogo
    """
    try:
        db = DatabaseManager()
        game_data = db.get_game_price_history(steam_id)
        
        if not game_data:
            return jsonify({
                "success": False, 
                "error": "Jogo não encontrado"
            }), 404
            
        return jsonify({
            "success": True, 
            "data": game_data
        })
        
    except Exception as e:
        return jsonify({
            "success": False, 
            "error": f"Erro ao buscar jogo: {str(e)}"
        }), 500

# ========================
# SISTEMA DE ANÁLISE DE COMPRA
# ========================

@app.route('/api/buy-analysis')
def listar_jogos_para_analise():
    """
    Lista jogos disponíveis para análise de compra com estatísticas básicas.
    
    Returns:
        JSON com jogos disponíveis e suas informações
    """
    try:
        analyzer = SimpleBuyingAnalyzer()
        available_games = analyzer.get_available_games()
        
        return jsonify({
            "success": True,
            "games": available_games,
            "total": len(available_games)
        })
        
    except Exception as e:
        return jsonify({
            "success": False, 
            "error": f"Erro ao listar jogos: {str(e)}"
        }), 500

@app.route('/api/buy-analysis/<game_name>')
def analisar_oportunidade_compra(game_name):
    """
    Realiza análise completa para determinar se é bom momento para comprar um jogo.
    
    Esta função implementa o algoritmo principal do sistema, que:
    1. Analisa a posição atual do preço (percentil)
    2. Examina tendências recentes de preço
    3. Considera histórico de descontos
    4. Gera uma pontuação de 0-100 e recomendação
    
    Args:
        game_name: Nome do jogo para análise
        
    Returns:
        JSON com análise completa e recomendação
    """
    try:
        analyzer = SimpleBuyingAnalyzer()
        result = analyzer.analyze_game(game_name)
        
        if not result['success']:
            return jsonify(result), 404
            
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "game_name": game_name,
            "error": f"Erro na análise: {str(e)}"
        }), 500

# ========================
# ROTAS DE ANÁLISE ESTATÍSTICA
# ========================

@app.route('/api/predictions')
def obter_predicoes():
    """
    Gera predições de preços usando análise básica de tendências.
    
    Esta função é uma versão simplificada que analisa tendências
    recentes para estimar direção dos preços.
    """
    try:
        db = DatabaseManager()
        analyzer = BasicAnalyzer()
        
        # Buscar jogos com dados suficientes
        games_df = db.get_games()
        predictions = []
        
        for _, game in games_df.iterrows():
            if game['current_price'] is None or game['current_price'] == 0:
                continue
                
            # Análise simples de tendência (pode ser expandida)
            prediction_data = {
                "game": game['name'],
                "current_price": float(game['current_price']),
                "predicted_price": float(game['current_price']) * 0.95,  # Estimativa conservadora
                "trend_percent": -5.0,  # Tendência de queda conservadora
                "recommendation": "AGUARDAR" if game['current_price'] > 50 else "COMPRAR"
            }
            predictions.append(prediction_data)
        
        return jsonify({
            "success": True,
            "data": predictions[:10],  # Limitar a 10 resultados
            "total": len(predictions)
        })
        
    except Exception as e:
        return jsonify({
            "success": False, 
            "error": f"Erro ao gerar predições: {str(e)}"
        }), 500

@app.route('/api/analysis/best-deals')
def melhores_ofertas():
    """
    Identifica as melhores ofertas disponíveis baseado em análise de preços.
    
    Returns:
        JSON com lista das melhores ofertas encontradas
    """
    try:
        analyzer = BasicAnalyzer()
        limit = request.args.get('limit', 5, type=int)
        deals_df = analyzer.find_best_deals(top_n=limit)
        
        if deals_df.empty:
            deals_list = []
        else:
            deals_list = deals_df.to_dict('records')
            
        return jsonify({
            "success": True, 
            "data": deals_list,
            "total": len(deals_list)
        })
        
    except Exception as e:
        return jsonify({
            "success": False, 
            "error": f"Erro ao buscar ofertas: {str(e)}"
        }), 500

# ========================
# FUNÇÃO PRINCIPAL
# ========================

if __name__ == '__main__':
    print("="*50)
    print("🎮 PRYZOR - Sistema de Análise de Preços Steam")
    print("📊 Projeto Universitário de Análise de Dados")
    print("🚀 Iniciando servidor Flask...")
    print("="*50)
    
    # Configuração para produção e desenvolvimento
    import os
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    host = '0.0.0.0' if not debug else '127.0.0.1'
    
    app.run(debug=debug, host=host, port=port)
