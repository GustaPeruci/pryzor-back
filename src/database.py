"""
Configuração do banco de dados e modelos para o projeto Pryzor
"""

from sqlalchemy import create_engine, text, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging
from .mysql_config import get_database_url, get_mysql_connection_info

# Configuração do logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base para os modelos
Base = declarative_base()

# Engine e Session
engine = None
SessionLocal = None

def init_database():
    """Inicializa a conexão com o banco de dados"""
    global engine, SessionLocal
    
    try:
        database_url = get_database_url()
        logger.info(f"🔗 Conectando ao banco: {get_mysql_connection_info()['environment']}")
        
        engine = create_engine(
            database_url,
            echo=False,  # Mudar para True para debug SQL
            pool_recycle=3600,
            pool_pre_ping=True
        )
        
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Testa a conexão
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            logger.info("✅ Conexão com banco estabelecida com sucesso!")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao conectar com banco: {e}")
        return False

def get_db():
    """Retorna uma sessão do banco de dados"""
    if SessionLocal is None:
        init_database()
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_connection():
    """Testa a conexão com o banco"""
    try:
        if engine is None:
            init_database()
            
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 'Connection OK' as status"))
            row = result.fetchone()
            return {"success": True, "message": row[0]}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

# Modelos do banco de dados
class Game(Base):
    __tablename__ = 'games'
    
    id = Column(Integer, primary_key=True)
    steam_id = Column(Integer, unique=True, nullable=False)
    nome = Column(String(255), nullable=False)
    preco_atual = Column(Float, default=0.0)
    desconto_atual = Column(Integer, default=0)
    categoria = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PricePrediction(Base):
    __tablename__ = 'price_predictions'
    
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, nullable=False)
    predicted_price = Column(Float, nullable=False)
    confidence = Column(Float, default=0.0)
    trend_percent = Column(Float, default=0.0)
    recommendation = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

def create_tables():
    """Cria as tabelas no banco de dados"""
    try:
        if engine is None:
            init_database()
            
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tabelas criadas/atualizadas com sucesso!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabelas: {e}")
        return False

def insert_sample_data():
    """Insere dados de exemplo se não existirem"""
    try:
        if SessionLocal is None:
            init_database()
            
        db = SessionLocal()
        
        # Verifica se já existem jogos
        existing_games = db.query(Game).count()
        if existing_games > 0:
            logger.info(f"📊 Banco já possui {existing_games} jogos")
            db.close()
            return True
        
        # Insere jogos de exemplo
        sample_games = [
            Game(
                steam_id=730,
                nome="Counter-Strike 2",
                preco_atual=0.0,
                desconto_atual=0,
                categoria="FPS"
            ),
            Game(
                steam_id=271590,
                nome="Grand Theft Auto V",
                preco_atual=89.90,
                desconto_atual=50,
                categoria="Action"
            ),
            Game(
                steam_id=292030,
                nome="The Witcher 3: Wild Hunt",
                preco_atual=149.99,
                desconto_atual=75,
                categoria="RPG"
            ),
            Game(
                steam_id=813780,
                nome="Age of Empires IV",
                preco_atual=199.90,
                desconto_atual=30,
                categoria="Strategy"
            ),
            Game(
                steam_id=1172470,
                nome="Apex Legends",
                preco_atual=0.0,
                desconto_atual=0,
                categoria="Battle Royale"
            )
        ]
        
        for game in sample_games:
            db.add(game)
        
        db.commit()
        logger.info(f"✅ Inseridos {len(sample_games)} jogos de exemplo")
        
        # Insere predições de exemplo
        predictions = [
            PricePrediction(
                game_id=2,  # GTA V
                predicted_price=67.43,
                confidence=85.0,
                trend_percent=-25.0,
                recommendation="COMPRAR"
            ),
            PricePrediction(
                game_id=3,  # Witcher 3
                predicted_price=99.99,
                confidence=78.0,
                trend_percent=-33.0,
                recommendation="AGUARDAR"
            )
        ]
        
        for pred in predictions:
            db.add(pred)
        
        db.commit()
        logger.info(f"✅ Inseridas {len(predictions)} predições de exemplo")
        
        db.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao inserir dados de exemplo: {e}")
        if 'db' in locals():
            db.close()
        return False

if __name__ == "__main__":
    print("🔧 Testando configuração do banco...")
    
    # Teste de conexão
    result = test_connection()
    print(f"Conexão: {result}")
    
    # Criação de tabelas
    if create_tables():
        print("✅ Tabelas OK")
        
        # Inserção de dados de exemplo
        if insert_sample_data():
            print("✅ Dados de exemplo OK")
