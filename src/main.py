"""
Pryzor API - MySQL Production Ready
API final otimizada exclusivamente para MySQL
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import math

import mysql.connector
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure this src folder is importable (so that `import api.*` works when running by path)
_SRC_DIR = os.path.dirname(__file__)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from api.discount_service import DiscountForecastService

app = FastAPI(
    title="Pryzor - Steam Price Prediction API",
    description="Production-ready Steam price prediction API powered by MySQL",
    version="5.0.0 - MySQL Production"
)

# Configure CORS with explicit allowed origins (wildcard + credentials can be problematic on browsers)
_default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]
_env_origins = os.getenv("CORS_ORIGINS")
if _env_origins:
    try:
        origins = [o.strip() for o in _env_origins.split(",") if o.strip()]
    except Exception:
        origins = _default_origins
else:
    origins = _default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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

# Lazy singleton for discount forecast service
_discount_service: Optional[DiscountForecastService] = None

def get_discount_service() -> DiscountForecastService:
    global _discount_service
    if _discount_service is None:
        _discount_service = DiscountForecastService(mysql_config=MYSQL_CONFIG)
    return _discount_service


class BatchRequest(BaseModel):
    appids: List[int]

class BatchResponse(BaseModel):
    results: Dict[int, Any]

 

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


@app.get("/health")
async def health_check():
    """Health Check MySQL"""
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT 1")
        test = cursor.fetchone()[0]

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
            SELECT 
                games.appid as appid, 
                games.name as name, 
                games.type as type, 
                games.releasedate as releasedate, 
                games.freetoplay as freetoplay,
                (
                    SELECT ph.finalprice 
                    FROM price_history ph 
                    WHERE ph.appid = games.appid AND ph.finalprice IS NOT NULL 
                    ORDER BY ph.date DESC 
                    LIMIT 1
                ) as current_price,
                (
                    SELECT ph.discount 
                    FROM price_history ph 
                    WHERE ph.appid = games.appid AND ph.discount IS NOT NULL 
                    ORDER BY ph.date DESC 
                    LIMIT 1
                ) as current_discount,
                (SELECT COUNT(*) FROM price_history WHERE appid = games.appid) as price_records
            FROM games {where_clause}
            ORDER BY games.appid
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


@app.get("/api/ml/discount-30d/metrics")
async def discount_model_metrics():
    """Expõe métricas e metadados do modelo atual para o frontend (sem binários)."""
    try:
        svc = get_discount_service()
        meta = svc.meta or {}
        return {
            "threshold": svc.threshold,
            "lookback_days": meta.get("lookback_days"),
            "horizon_days": meta.get("horizon_days"),
            "discount_threshold": meta.get("discount_threshold"),
            "class_prevalence": meta.get("class_prevalence"),
            "metrics": meta.get("metrics", {}),
            "calibration": meta.get("calibration", {}),
            "best_params": meta.get("best_params"),
            "created_at": meta.get("created_at"),
            "n_samples": meta.get("n_samples"),
            "n_games": meta.get("n_games"),
            "date_min": meta.get("date_min"),
            "date_max": meta.get("date_max"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ml/discount-30d/inspect")
async def discount_feature_inspect(appid: int):
    """Retorna vetor de features; nunca lança 500 (erro vem no payload)."""
    svc = get_discount_service()
    result = svc.inspect(appid)
    return JSONResponse(content=result)


@app.get("/api/ml/discount-30d/feature-descriptions")
async def discount_feature_descriptions():
    """Descrições curtas das features para exibir no frontend (tooltip/legenda)."""
    try:
        # Dicionário mínimo; pode ser movido para arquivo JSON se crescer
        desc = {
            "price_ma7": "Média de preço 7d",
            "price_ma14": "Média de preço 14d",
            "price_ma30": "Média de preço 30d",
            "price_ma60": "Média de preço 60d",
            "price_ma90": "Média de preço 90d",
            "price_std14": "Desvio padrão 14d",
            "price_std30": "Desvio padrão 30d",
            "price_std60": "Desvio padrão 60d",
            "price_std90": "Desvio padrão 90d",
            "price_ema7": "Média exponencial 7d",
            "price_ema30": "Média exponencial 30d",
            "price_z_ma30": "Z-score vs MA30",
            "price_z_ma90": "Z-score vs MA90",
            "price_slope7": "Inclinação 7d",
            "price_slope30": "Inclinação 30d",
            "price_slope90": "Inclinação 90d",
            "price_var7": "Variância 7d",
            "price_var30": "Variância 30d",
            "price_var90": "Variância 90d",
            "price_max30": "Máximo 30d",
            "price_min30": "Mínimo 30d",
            "price_max90": "Máximo 90d",
            "price_min90": "Mínimo 90d",
            "disc_freq7": "Frequência de desconto 7d",
            "disc_freq14": "Frequência de desconto 14d",
            "disc_freq30": "Frequência de desconto 30d",
            "disc_freq60": "Frequência de desconto 60d",
            "disc_freq90": "Frequência de desconto 90d",
            "disc_mean30": "Desconto médio 30d",
            "disc_mean90": "Desconto médio 90d",
            "disc_max30": "Desconto máximo 30d",
            "disc_max90": "Desconto máximo 90d",
            "disc_strong_freq30": "Freq. descontos fortes (>=40%) 30d",
            "disc_strong_freq90": "Freq. descontos fortes (>=40%) 90d",
            "avg_gap_disc90": "Gap médio entre descontos (90d)",
            "days_since_max_disc90": "Dias desde maior desconto (90d)",
            "price_ma7_over_30": "Razão MA7/MA30",
            "days_since_last_disc": "Dias desde último desconto",
            "type_encoded": "Tipo do app (game/dlc/demo)",
            "years_since_release": "Anos desde lançamento",
            "season_winter": "Estação inverno",
            "season_spring": "Estação primavera",
            "season_summer": "Estação verão",
            "season_fall": "Estação outono",
            "sale_winter": "Janela de promo de inverno",
            "sale_summer": "Janela de promo de verão",
            "sale_autumn": "Janela de promo de outono",
            "sale_lunar_new_year": "Janela de promo Ano Novo Lunar",
            "sale_halloween": "Janela de promo Halloween",
            "sale_spring": "Janela de promo Spring",
            "sale_black_friday": "Janela de promo Black Friday",
        }
        return desc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ml/discount-30d")
async def discount_30d(appid: int):
    """Predict probability of a discount >= threshold in next 30 days for given appid"""
    try:
        svc = get_discount_service()
        result = svc.predict(appid)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ml/discount-30d/batch", response_model=BatchResponse)
async def discount_30d_batch(req: BatchRequest):
    """Batch prediction for multiple appids"""
    try:
        svc = get_discount_service()
        results = svc.predict_batch(req.appids)
        if all("error" in r for r in results.values()):
            raise HTTPException(status_code=400, detail="No predictions available for provided appids")
        return {"results": results}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ml/discount-30d/model-info")
async def discount_model_info():
    try:
        svc = get_discount_service()
        meta = svc.meta or {}
        return {
            "features": svc.features,
            "threshold": svc.threshold,
            "metadata": meta,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ml/discount-30d/reload")
async def reload_discount_model():
    """Reload the discount model artifact and clear cache (hot-reload)."""
    try:
        svc = get_discount_service()
        svc.reload()
        return {
            "status": "reloaded",
            "features": svc.features,
            "threshold": svc.threshold,
            "metadata": svc.meta,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/games/{appid}/price-history")
async def price_history(appid: int, limit: int = 120):
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT date, finalprice, discount
            FROM price_history
            WHERE appid = %s AND finalprice IS NOT NULL
            ORDER BY date DESC
            LIMIT %s
            """,
            (appid, limit),
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        # return ascending order for charts
        rows = list(reversed(rows))
        return {"appid": appid, "history": rows}
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