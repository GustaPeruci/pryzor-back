"""
Pryzor API - MySQL Production Ready
API final otimizada exclusivamente para MySQL
"""

import mysql.connector
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

app = FastAPI(
    title="Pryzor - Steam Price Prediction API",
    description="Production-ready Steam price prediction API powered by MySQL",
    version="5.0.0 - MySQL Production"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuração MySQL
MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'steam_pryzor'
}

def get_mysql_connection():
    """Obtém conexão MySQL"""
    try:
        return mysql.connector.connect(**MYSQL_CONFIG)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"MySQL connection failed: {str(e)}")

@app.on_event("startup")
async def startup_event():
    """Inicialização da API"""
    print("🚀 Pryzor API - MySQL Production")
    print("=" * 50)
    
    try:
        # Testar conexão
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        # Verificar dados
        cursor.execute("SELECT COUNT(*) FROM games")
        games_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM price_history")
        prices_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        print(f"🏠 MySQL: {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}")
        print(f"💾 Database: {MYSQL_CONFIG['database']}")
        print(f"🎮 Games: {games_count:,}")
        print(f"💰 Price Records: {prices_count:,}")
        print("✅ API inicializada com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro na inicialização: {e}")

@app.get("/")
async def root():
    """API Info"""
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM games")
        games = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM price_history")
        prices = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return {
            "name": "Pryzor - Steam Price Prediction API",
            "version": "5.0.0",
            "database": {
                "type": "MySQL",
                "status": "connected",
                "games": games,
                "price_records": prices
            },
            "features": [
                "MySQL High Performance",
                "Steam Games Database", 
                "Price History Analytics",
                "ML Price Predictions",
                "Production Ready"
            ],
            "endpoints": {
                "games": "/api/games",
                "game_details": "/api/games/{appid}",
                "predictions": "/api/predictions/{appid}",
                "analytics": "/api/analytics",
                "documentation": "/docs"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/health")
async def health_check():
    """Health Check MySQL"""
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor()
        
        # Testar query
        cursor.execute("SELECT 1")
        test = cursor.fetchone()[0]
        
        # Estatísticas
        cursor.execute("SELECT COUNT(*) FROM games")
        games = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM price_history")  
        prices = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "mysql": {
                "host": MYSQL_CONFIG['host'],
                "database": MYSQL_CONFIG['database'],
                "connection": "active",
                "test_query": test == 1
            },
            "data": {
                "games": games,
                "price_records": prices
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/api/games")
async def list_games(
    limit: int = 100,
    offset: int = 0,
    search: Optional[str] = None,
    free_only: bool = False
):
    """Lista jogos com filtros"""
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Base query
        where_conditions = []
        params = []
        
        if search:
            where_conditions.append("name LIKE %s")
            params.append(f"%{search}%")
        
        if free_only:
            where_conditions.append("freetoplay = 1")
        
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # Count total
        count_query = f"SELECT COUNT(*) as total FROM games {where_clause}"
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']
        
        # Limitar máximo para performance (mas permitir buscar todos)
        max_limit = min(limit, 2000)  # Máximo 2000 jogos por vez
        
        # Get games
        games_query = f"""
            SELECT appid, name, type, releasedate, freetoplay,
                   (SELECT COUNT(*) FROM price_history WHERE appid = games.appid) as price_records
            FROM games {where_clause}
            ORDER BY appid
            LIMIT %s OFFSET %s
        """
        
        cursor.execute(games_query, params + [max_limit, offset])
        games = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {
            "games": games,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": total,
                "returned": len(games),
                "has_more": (offset + limit) < total
            },
            "filters": {
                "search": search,
                "free_only": free_only
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/games/{appid}")
async def get_game_details(appid: int):
    """Detalhes de um jogo"""
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Game info
        cursor.execute("SELECT * FROM games WHERE appid = %s", (appid,))
        game = cursor.fetchone()
        
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        
        # Price statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_records,
                AVG(finalprice) as avg_price,
                MIN(finalprice) as min_price,
                MAX(finalprice) as max_price,
                AVG(discount) as avg_discount,
                MAX(discount) as max_discount
            FROM price_history 
            WHERE appid = %s AND finalprice IS NOT NULL
        """, (appid,))
        
        stats = cursor.fetchone()
        
        # Recent prices
        cursor.execute("""
            SELECT date, finalprice, discount 
            FROM price_history 
            WHERE appid = %s 
            ORDER BY date DESC 
            LIMIT 10
        """, (appid,))
        
        recent_prices = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {
            "game": game,
            "statistics": {
                "total_price_records": stats['total_records'] or 0,
                "average_price": round(float(stats['avg_price'] or 0), 2),
                "min_price": float(stats['min_price'] or 0),
                "max_price": float(stats['max_price'] or 0),
                "average_discount": round(float(stats['avg_discount'] or 0), 2),
                "max_discount": float(stats['max_discount'] or 0)
            },
            "recent_prices": recent_prices
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/predictions/{appid}")
async def create_prediction(appid: int):
    """Gerar predição de preço"""
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar se jogo existe
        cursor.execute("SELECT * FROM games WHERE appid = %s", (appid,))
        game = cursor.fetchone()
        
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        
        # Calcular features
        cursor.execute("""
            SELECT 
                AVG(finalprice) as avg_price,
                COUNT(*) as record_count,
                STDDEV(finalprice) as price_stddev
            FROM price_history 
            WHERE appid = %s AND finalprice IS NOT NULL
        """, (appid,))
        
        stats = cursor.fetchone()
        
        if not stats['record_count']:
            raise HTTPException(status_code=404, detail="Insufficient data for prediction")
        
        avg_price = float(stats['avg_price'] or 0)
        
        # Predição baseada em regras
        if avg_price < 5:
            category = "budget"
            confidence = 0.85
        elif avg_price < 15:
            category = "economy"  
            confidence = 0.78
        elif avg_price < 30:
            category = "standard"
            confidence = 0.82
        elif avg_price < 50:
            category = "premium"
            confidence = 0.76
        else:
            category = "luxury"
            confidence = 0.88
        
        prediction_data = {
            "appid": appid,
            "game_name": game['name'],
            "predicted_category": category,
            "confidence": confidence,
            "model": "rule_based_mysql_v1",
            "features": {
                "average_price": avg_price,
                "data_points": stats['record_count'],
                "price_volatility": float(stats['price_stddev'] or 0)
            },
            "prediction_date": datetime.now().isoformat()
        }
        
        cursor.close()
        conn.close()
        
        return prediction_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics")
async def analytics_summary():
    """Analytics do sistema"""
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Estatísticas gerais
        cursor.execute("SELECT COUNT(*) as total FROM games")
        total_games = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM price_history")
        total_prices = cursor.fetchone()['total']
        
        # Top games por dados
        cursor.execute("""
            SELECT g.appid, g.name, COUNT(p.id) as price_records
            FROM games g
            LEFT JOIN price_history p ON g.appid = p.appid
            GROUP BY g.appid, g.name
            ORDER BY price_records DESC
            LIMIT 10
        """)
        
        top_games = cursor.fetchall()
        
        # Estatísticas de preços
        cursor.execute("""
            SELECT 
                AVG(finalprice) as avg_price,
                MIN(finalprice) as min_price,
                MAX(finalprice) as max_price
            FROM price_history
            WHERE finalprice IS NOT NULL
        """)
        
        price_stats = cursor.fetchone()
        
        # Games grátis
        cursor.execute("SELECT COUNT(*) as total FROM games WHERE freetoplay = 1")
        free_games = cursor.fetchone()['total']
        
        cursor.close()
        conn.close()
        
        return {
            "summary": {
                "total_games": total_games,
                "total_price_records": total_prices,
                "free_games": free_games,
                "paid_games": total_games - free_games
            },
            "price_statistics": {
                "average_price": round(float(price_stats['avg_price'] or 0), 2),
                "min_price": float(price_stats['min_price'] or 0),
                "max_price": float(price_stats['max_price'] or 0)
            },
            "top_games_by_data": top_games,
            "database": {
                "type": "MySQL",
                "performance": "optimized"
            },
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("🚀 Iniciando Pryzor API MySQL Production...")
    uvicorn.run(app, host="127.0.0.1", port=8000)