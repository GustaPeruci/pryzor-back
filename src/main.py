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

from dotenv import load_dotenv

load_dotenv()  

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
    "https://pryzor-front.onrender.com",
    os.getenv('MAIN_URL', 'localhost')
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
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', '3306')),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', os.getenv('MYSQL_PASS', 'root')),
    'database': os.getenv('MYSQL_DATABASE', 'steam_pryzor')
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

class AdminResponse(BaseModel):
    status: str
    message: str
    details: Optional[Dict[str, Any]] = None

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
    except Exception as e:
        print(f"\n⚠️  Não foi possível conectar ao banco de dados: {e}\n")
        print(f"   A API será inicializada sem conexão ao banco. Use os endpoints de setup para criar/importar a base após o deploy.")
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
        db_status = {
            "status": "connected",
            "games": games,
            "price_records": prices
        }
    except Exception as e:
        db_status = {
            "status": "unavailable",
            "error": str(e)
        }
    predictor = get_ml_predictor()
    return {
        "status": "healthy" if db_status["status"] == "connected" else "degraded",
        "timestamp": datetime.now().isoformat(),
        "database": db_status,
        "ml_model": {
            "loaded": predictor.is_loaded(),
            "version": predictor.version if predictor.is_loaded() else None
        }
    }

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
                g.releasedate as release_date, 
                g.freetoplay as free_to_play,
                (
                    SELECT ph.final_price 
                    FROM price_history ph 
                    WHERE ph.appid = g.appid AND ph.final_price IS NOT NULL 
                    ORDER BY ph.date DESC 
                    LIMIT 1
                ) as current_price,
                (
                    SELECT ph.discount 
                    FROM price_history ph 
                    WHERE ph.appid = g.appid AND ph.discount IS NOT NULL 
                    ORDER BY ph.date DESC 
                    LIMIT 1
                ) as current_discount
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
            SELECT appid, name, type, releasedate as release_date, freetoplay as free_to_play
            FROM games
            WHERE appid = %s
        """, (appid,))
        
        game = cursor.fetchone()
        
        if not game:
            raise HTTPException(status_code=404, detail="Jogo não encontrado")
        
        # Buscar histórico de preços (últimos 30 registros)
        cursor.execute("""
            SELECT date, final_price, discount
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
                AVG(final_price) as avg_price,
                MIN(final_price) as min_price,
                MAX(final_price) as max_price
            FROM price_history
            WHERE final_price IS NOT NULL
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
# ENDPOINTS - ADMIN (SETUP E MIGRAÇÃO)
# ============================================================================

@app.post("/api/admin/setup-database")
async def setup_database():
    """
    Cria o banco de dados e tabelas necessárias
    
    ⚠️ ATENÇÃO: Este endpoint cria a estrutura do banco.
    Só execute se o banco não existir ou precisar ser recriado.
    """
    import pymysql
    from pathlib import Path
    
    try:
        # Conectar SEM especificar database (para criar)
        connection = pymysql.connect(
            host=MYSQL_CONFIG['host'],
            port=MYSQL_CONFIG['port'],
            user=MYSQL_CONFIG['user'],
            password=MYSQL_CONFIG['password'],
            charset='utf8mb4'
        )
        cursor = connection.cursor()
        
        # Criar database
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_CONFIG['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute(f"USE {MYSQL_CONFIG['database']}")
        
        # Ler e executar SQL do arquivo setup_database.sql
        sql_file = Path(__file__).parent.parent / 'setup_database.sql'
        
        if not sql_file.exists():
            raise HTTPException(
                status_code=500, 
                detail=f"Arquivo setup_database.sql não encontrado em {sql_file}"
            )
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        # Executar cada statement SQL
        statements = [s.strip() for s in sql_script.split(';') if s.strip()]
        executed = 0
        
        for statement in statements:
            if statement and not statement.startswith('CREATE DATABASE'):
                cursor.execute(statement)
                executed += 1
        
        connection.commit()
        
        # Verificar criação
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        
        cursor.close()
        connection.close()
        
        return {
            "status": "success",
            "message": "Banco de dados criado com sucesso!",
            "details": {
                "database": MYSQL_CONFIG['database'],
                "tables_created": tables,
                "sql_statements_executed": executed,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except pymysql.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao criar banco de dados: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro inesperado: {str(e)}"
        )

@app.post("/api/admin/import-dataset")
async def import_dataset():
    """
    Importa dataset completo do CSV para o banco MySQL
    
    Importa:
    - applicationInformation.csv → tabela games
    - PriceHistory/*.csv → tabela price_history
    
    ⚠️ ATENÇÃO: Este processo pode levar vários minutos.
    Certifique-se de que o banco foi criado antes (use /api/admin/setup-database).
    """
    import pymysql
    import csv
    from pathlib import Path
    from datetime import datetime as dt
    
    try:
        # Verificar se banco e tabelas existem
        try:
            connection = pymysql.connect(
                host=MYSQL_CONFIG['host'],
                port=MYSQL_CONFIG['port'],
                user=MYSQL_CONFIG['user'],
                password=MYSQL_CONFIG['password'],
                database=MYSQL_CONFIG['database'],
                charset='utf8mb4'
            )
            cursor = connection.cursor()
            
            # Verificar se tabelas existem
            cursor.execute("SHOW TABLES LIKE 'games'")
            if not cursor.fetchone():
                cursor.close()
                connection.close()
                raise HTTPException(
                    status_code=400,
                    detail="Tabela 'games' não encontrada. Execute /api/admin/setup-database primeiro."
                )
            
            cursor.execute("SHOW TABLES LIKE 'price_history'")
            if not cursor.fetchone():
                cursor.close()
                connection.close()
                raise HTTPException(
                    status_code=400,
                    detail="Tabela 'price_history' não encontrada. Execute /api/admin/setup-database primeiro."
                )
            
            cursor.close()
            connection.close()
            
        except pymysql.Error as e:
            raise HTTPException(
                status_code=400,
                detail=f"Erro ao conectar ao banco: {str(e)}. Execute /api/admin/setup-database primeiro."
            )
        
        # Caminhos dos dados
        base_dir = Path(__file__).parent.parent
        data_dir = base_dir / 'data'
        games_csv = data_dir / 'applicationInformation.csv'
        price_history_dir = data_dir / 'PriceHistory'
        
        if not games_csv.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Arquivo não encontrado: {games_csv}"
            )
        
        if not price_history_dir.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Diretório não encontrado: {price_history_dir}"
            )
        
        # Conectar ao banco
        connection = pymysql.connect(
            host=MYSQL_CONFIG['host'],
            port=MYSQL_CONFIG['port'],
            user=MYSQL_CONFIG['user'],
            password=MYSQL_CONFIG['password'],
            database=MYSQL_CONFIG['database'],
            charset='utf8mb4'
        )
        cursor = connection.cursor()
        
        # Função para detectar encoding
        def open_csv_with_encoding(file_path):
            """Tenta abrir CSV com diferentes encodings"""
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'utf-8-sig']
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        f.read()
                    return encoding
                except (UnicodeDecodeError, UnicodeError):
                    continue
            return 'latin-1'  # Fallback
        
        # ==== IMPORTAR JOGOS ====
        games_imported = 0
        games_skipped = 0
        
        # Detectar encoding do arquivo
        csv_encoding = open_csv_with_encoding(games_csv)
        
        with open(games_csv, 'r', encoding=csv_encoding, errors='replace') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                appid = row['appid'].strip()
                game_type = row['type'].strip()
                name = row['name'].strip()
                # Normalizar nomes de colunas (CSV usa releasedate/freetoplay sem underscore)
                release_date = row.get('release_date', row.get('releasedate', '')).strip()
                free_to_play = row.get('free_to_play', row.get('freetoplay', '')).strip()
                
                if not appid:
                    games_skipped += 1
                    continue
                
                # Converter data
                release_date_formatted = None
                if release_date:
                    try:
                        date_obj = dt.strptime(release_date, '%d-%b-%y')
                        release_date_formatted = date_obj.strftime('%Y-%m-%d')
                    except:
                        pass
                
                is_free = 1 if free_to_play == '1' else 0
                
                try:
                    sql = """
                    INSERT INTO games (appid, name, type, releasedate, freetoplay, price_records)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        name = VALUES(name),
                        type = VALUES(type),
                        releasedate = VALUES(releasedate),
                        freetoplay = VALUES(freetoplay)
                    """
                    cursor.execute(sql, (
                        int(appid), name, game_type, 
                        release_date_formatted, is_free, 0
                    ))
                    games_imported += 1
                except Exception as e:
                    print(f"⚠️  Erro ao importar jogo {appid}: {e}")
                    games_skipped += 1
                    continue
        
        connection.commit()
        
        # ==== IMPORTAR HISTÓRICO DE PREÇOS ====
        price_records_imported = 0
        files_processed = 0
        files_skipped = 0
        
        csv_files = list(price_history_dir.glob('*.csv'))
        total_files = len(csv_files)
        
        appid_price_count = {}
        
        for csv_file in csv_files:
            try:
                appid = int(csv_file.stem)
            except ValueError:
                files_skipped += 1
                continue
            
            # Verificar se jogo existe
            cursor.execute("SELECT 1 FROM games WHERE appid = %s", (appid,))
            if not cursor.fetchone():
                files_skipped += 1
                continue
            
            records_count = 0
            batch = []
            
            # Detectar encoding de cada arquivo de histórico
            price_encoding = open_csv_with_encoding(csv_file)
            
            with open(csv_file, 'r', encoding=price_encoding, errors='replace') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    date_str = row['Date'].strip()
                    final_price = row['Finalprice'].strip()
                    discount = row['Discount'].strip()
                    
                    try:
                        date_obj = dt.strptime(date_str, '%Y-%m-%d')
                        date_formatted = date_obj.strftime('%Y-%m-%d')
                    except:
                        continue
                    
                    batch.append((
                        appid,
                        date_formatted,
                        float(final_price) if final_price else 0.0,
                        int(discount) if discount else 0
                    ))
                    records_count += 1
                    
                    # Executar batch a cada 500 registros
                    if len(batch) >= 500:
                        sql = """
                        INSERT INTO price_history (appid, date, final_price, discount)
                        VALUES (%s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE 
                            final_price = VALUES(final_price),
                            discount = VALUES(discount)
                        """
                        cursor.executemany(sql, batch)
                        price_records_imported += len(batch)
                        batch = []
                
                # Inserir registros restantes
                if batch:
                    sql = """
                    INSERT INTO price_history (appid, date, final_price, discount)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        final_price = VALUES(final_price),
                        discount = VALUES(discount)
                    """
                    cursor.executemany(sql, batch)
                    price_records_imported += len(batch)
            
            appid_price_count[appid] = records_count
            files_processed += 1
        
        connection.commit()
        
        # ==== ATUALIZAR CONTADORES ====
        updated = 0
        for appid, count in appid_price_count.items():
            if count > 0:
                cursor.execute(
                    "UPDATE games SET price_records = %s WHERE appid = %s",
                    (count, appid)
                )
                updated += 1
        
        connection.commit()
        
        # ==== ESTATÍSTICAS FINAIS ====
        cursor.execute("SELECT COUNT(*) as total FROM games")
        total_games = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) as total FROM price_history")
        total_prices = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) as total FROM games WHERE price_records > 0")
        games_with_prices = cursor.fetchone()[0]
        
        cursor.close()
        connection.close()
        
        return {
            "status": "success",
            "message": "Dataset importado com sucesso!",
            "details": {
                "games": {
                    "imported": games_imported,
                    "skipped": games_skipped,
                    "total_in_db": total_games
                },
                "price_history": {
                    "files_processed": files_processed,
                    "files_skipped": files_skipped,
                    "total_files": total_files,
                    "records_imported": price_records_imported,
                    "total_in_db": total_prices
                },
                "games_with_price_data": games_with_prices,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except pymysql.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro no banco de dados: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro durante importação: {str(e)}"
        )

# ============================================================================
# MAIN - EXECUÇÃO LOCAL
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    print("🚀 Iniciando Pryzor API...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
