"""
Pryzor API - Backend Acadêmico TCC
API REST para predição de descontos em jogos Steam
Modelo: RandomForest v2.0 com validação temporal
"""

import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional

import mysql.connector
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure this src folder is importable
_SRC_DIR = os.path.dirname(__file__)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from api.ml_discount_predictor import MLDiscountPredictor

# ============================================================================
# CONFIGURAÇÃO DA API
# ============================================================================

app = FastAPI(
    title="Pryzor - Steam Discount Prediction API",
    description="API acadêmica para predição de descontos em jogos Steam usando ML",
    version="1.0.0-TCC"
)

# CORS - Configuração para frontend
_default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuração MySQL
MYSQL_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', os.getenv('DB_PASS', 'root')),
    'database': os.getenv('DB_NAME', 'steam_pryzor')
}

# ============================================================================
# DEPENDÊNCIAS E SINGLETONS
# ============================================================================

_ml_predictor: Optional[MLDiscountPredictor] = None

def get_ml_predictor() -> MLDiscountPredictor:
    """Singleton do preditor ML"""
    global _ml_predictor
    if _ml_predictor is None:
        _ml_predictor = MLDiscountPredictor(mysql_config=MYSQL_CONFIG)
    return _ml_predictor

def get_mysql_connection():
    """Obtém conexão MySQL"""
    try:
        return mysql.connector.connect(**MYSQL_CONFIG)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"MySQL connection failed: {str(e)}")

# ============================================================================
# SCHEMAS PYDANTIC
# ============================================================================

class BatchRequest(BaseModel):
    appids: List[int]

# ============================================================================
# STARTUP/SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Inicialização da API"""
    print("\n" + "=" * 60)
    print("🚀 Pryzor API - Sistema de Predição de Descontos")
    print("=" * 60)
    
    try:
        # Testar conexão MySQL
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM games")
        games_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM price_history")
        prices_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        print(f"📊 MySQL Database")
        print(f"   Host: {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}")
        print(f"   Database: {MYSQL_CONFIG['database']}")
        print(f"   Games: {games_count:,}")
        print(f"   Price Records: {prices_count:,}")
        
        # Carregar modelo ML
        predictor = get_ml_predictor()
        if predictor.is_loaded():
            print(f"\n🤖 Modelo ML v{predictor.version}")
            print(f"   Validação: {predictor.validation_method}")
            print(f"   F1-Score: {predictor.metrics.get('f1_score', 0):.4f}")
            print(f"   Precision: {predictor.metrics.get('precision', 0):.4f}")
        else:
            print("\n⚠️  Modelo ML não carregado")
        
        print("\n✅ API inicializada com sucesso!")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Erro na inicialização: {e}\n")

# ============================================================================
# ENDPOINTS - SISTEMA
# ============================================================================

@app.get("/")
async def root():
    """Endpoint raiz da API"""
    return {
        "message": "Pryzor API - Sistema de Predição de Descontos Steam",
        "version": "1.0.0-TCC",
        "docs": "/docs",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    """Health check do sistema"""
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1")
        db_test = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM games")
        games = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM price_history")
        prices = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        predictor = get_ml_predictor()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": {
                "status": "connected",
                "games": games,
                "price_records": prices
            },
            "ml_model": {
                "loaded": predictor.is_loaded(),
                "version": predictor.version if predictor.is_loaded() else None
            }
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

# ============================================================================
# ENDPOINTS - DADOS
# ============================================================================

@app.get("/api/games")
async def list_games(
    limit: int = 100,
    offset: int = 0,
    search: Optional[str] = None,
    free_only: bool = False
):
    """
    Lista jogos do banco de dados
    
    Args:
        limit: Máximo de resultados (padrão: 100, máx: 1000)
        offset: Offset para paginação
        search: Busca por nome do jogo
        free_only: Filtrar apenas jogos gratuitos
    """
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Construir query com filtros
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
        
        # Contar total
        count_query = f"SELECT COUNT(*) as total FROM games {where_clause}"
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']
        
        # Limitar para performance
        max_limit = min(limit, 1000)
        
        # Buscar jogos
        games_query = f"""
            SELECT 
                g.appid, 
                g.name, 
                g.type, 
                g.releasedate, 
                g.freetoplay,
                (
                    SELECT ph.finalprice 
                    FROM price_history ph 
                    WHERE ph.appid = g.appid AND ph.finalprice IS NOT NULL 
                    ORDER BY ph.date DESC 
                    LIMIT 1
                ) as current_price,
                (
                    SELECT ph.discount 
                    FROM price_history ph 
                    WHERE ph.appid = g.appid AND ph.discount IS NOT NULL 
                    ORDER BY ph.date DESC 
                    LIMIT 1
                ) as current_discount,
                (SELECT COUNT(*) FROM price_history WHERE appid = g.appid) as price_records
            FROM games g {where_clause}
            ORDER BY g.appid
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
async def get_game(appid: int):
    """
    Busca informações de um jogo específico
    """
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Buscar jogo
        cursor.execute("""
            SELECT appid, name, type, releasedate, freetoplay
            FROM games
            WHERE appid = %s
        """, (appid,))
        
        game = cursor.fetchone()
        
        if not game:
            raise HTTPException(status_code=404, detail="Jogo não encontrado")
        
        # Buscar histórico de preços (últimos 30 registros)
        cursor.execute("""
            SELECT date, initialprice, finalprice, discount
            FROM price_history
            WHERE appid = %s
            ORDER BY date DESC
            LIMIT 30
        """, (appid,))
        
        price_history = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {
            "game": game,
            "price_history": price_history,
            "price_history_count": len(price_history)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_stats():
    """
    Estatísticas gerais do sistema
    """
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Total de jogos
        cursor.execute("SELECT COUNT(*) as total FROM games")
        total_games = cursor.fetchone()['total']
        
        # Total de registros de preço
        cursor.execute("SELECT COUNT(*) as total FROM price_history")
        total_prices = cursor.fetchone()['total']
        
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
        
        # Top 10 jogos com mais dados
        cursor.execute("""
            SELECT g.appid, g.name, COUNT(p.id) as price_records
            FROM games g
            LEFT JOIN price_history p ON g.appid = p.appid
            GROUP BY g.appid, g.name
            ORDER BY price_records DESC
            LIMIT 10
        """)
        top_games = cursor.fetchall()
        
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
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ENDPOINTS - ML v2.0
# ============================================================================

@app.get("/api/ml/info")
async def ml_model_info(predictor: MLDiscountPredictor = Depends(get_ml_predictor)):
    """
    Informações sobre o modelo ML
    """
    return predictor.get_model_info()

@app.get("/api/ml/health")
async def ml_health_check(predictor: MLDiscountPredictor = Depends(get_ml_predictor)):
    """
    Health check do serviço ML
    """
    return {
        "status": "healthy" if predictor.is_loaded() else "model_not_loaded",
        "model_loaded": predictor.is_loaded(),
        "version": predictor.version,
        "validation_method": predictor.validation_method,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/ml/predict/{appid}")
async def ml_predict_single(appid: int, predictor: MLDiscountPredictor = Depends(get_ml_predictor)):
    """
    Predição para um jogo específico
    
    Retorna:
        - will_have_discount: Se terá desconto >20% nos próximos 30 dias
        - probability: Probabilidade (0-1)
        - confidence: Confiança na predição (0-1)
        - recommendation: Recomendação de compra
        - reasoning: Fatores que influenciaram
    """
    result = predictor.predict(appid)
    
    if 'error' in result:
        raise HTTPException(status_code=404, detail=result)
    
    return result

@app.post("/api/ml/predict/batch")
async def ml_predict_batch(request: BatchRequest, predictor: MLDiscountPredictor = Depends(get_ml_predictor)):
    """
    Predições em lote (máximo 50 jogos)
    
    Body: {"appids": [730, 440, 570]}
    """
    result = predictor.batch_predict(request.appids, max_items=50)
    
    if 'error' in result:
        raise HTTPException(status_code=400, detail=result)
    
    return result

# ============================================================================
# MAIN - EXECUÇÃO LOCAL
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    print("🚀 Iniciando Pryzor API...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
