"""
PRYZOR - Gerenciador de Banco de Dados
======================================
Módulo responsável pela conexão e operações com banco de dados MySQL.

Este módulo centraliza todas as operações de banco de dados do sistema:
- Conexão com MySQL
- Operações CRUD para jogos e histórico de preços
- Consultas otimizadas para análises
- Gerenciamento de transações

Autor: Gustavo Peruci
Projeto Universitário - Análise de Dados
"""

import pandas as pd
import numpy as np
import logging
import os
from urllib.parse import urlparse

# Configuração de conectores MySQL
try:
    import pymysql
    pymysql.install_as_MySQLdb()
    MYSQL_CONNECTOR = 'pymysql'
    Error = pymysql.Error
    print("✅ Usando PyMySQL")
except ImportError:
    try:
        import mysql.connector
        from mysql.connector import Error
        MYSQL_CONNECTOR = 'mysql.connector'
        print("✅ Usando MySQL Connector")
    except ImportError:
        raise ImportError("Instale mysql-connector-python ou pymysql: pip install pymysql")

# Importação da configuração do banco
def get_mysql_config(env='local'):
    """Obtém configuração do MySQL a partir de variáveis de ambiente ou configuração padrão"""
    # Tenta usar DATABASE_URL primeiro (para Railway, Heroku, etc.)
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        try:
            parsed = urlparse(database_url)
            return {
                'host': parsed.hostname,
                'port': parsed.port or 3306,
                'user': parsed.username,
                'password': parsed.password,
                'database': parsed.path.lstrip('/')
            }
        except Exception as e:
            print(f"Erro ao parsear DATABASE_URL: {e}")
    
    # Usa variáveis de ambiente individuais
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 3306)),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', 'root'),
        'database': os.getenv('DB_NAME', 'pryzor_db')
    }

class DatabaseManager:
    def __init__(self, environment='local'):
        """Inicializa o gerenciador do banco MySQL"""
        self.config = get_mysql_config(environment)
        self.environment = environment
        self.setup_logging()
        
        # Testa conexão e cria tabelas
        if self._test_connection():
            self.create_tables()
        else:
            raise ConnectionError("Não foi possível conectar ao MySQL. Execute setup_mysql.py primeiro.")
    
    def setup_logging(self):
        """Configura logging para operações do banco"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def _test_connection(self):
        """Testa conexão com MySQL"""
        try:
            connection = self.get_connection()
            # PyMySQL não tem is_connected(), só testa se conseguiu conectar
            if MYSQL_CONNECTOR == 'mysql.connector':
                if connection.is_connected():
                    connection.close()
                    return True
            else:  # pymysql
                if connection:
                    connection.close()
                    return True
        except Exception as e:
            self.logger.error(f"Erro de conexão MySQL: {e}")
            return False
    
    def get_connection(self):
        """Retorna uma conexão com o banco MySQL"""
        try:
            if MYSQL_CONNECTOR == 'mysql.connector':
                connection = mysql.connector.connect(
                    host=self.config['host'],
                    port=self.config['port'],
                    user=self.config['user'],
                    password=self.config['password'],
                    database=self.config['database'],
                    charset='utf8mb4',
                    autocommit=True
                )
            else:  # pymysql
                import pymysql
                connection = pymysql.connect(
                    host=self.config['host'],
                    port=self.config['port'],
                    user=self.config['user'],
                    password=self.config['password'],
                    database=self.config['database'],
                    charset='utf8mb4',
                    autocommit=True
                )
            return connection
        except Exception as e:
            self.logger.error(f"Erro ao conectar MySQL: {e}")
            raise
    
    def create_tables(self):
        """Cria as tabelas básicas do banco de dados MySQL"""
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            
            # Tabela de jogos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS games (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    steam_id BIGINT UNIQUE NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_steam_id (steam_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Tabela de preços históricos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    game_id INT NOT NULL,
                    price DECIMAL(10, 2) NOT NULL,
                    date DATE NOT NULL,
                    week_year VARCHAR(7) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (game_id) REFERENCES games (id) ON DELETE CASCADE,
                    UNIQUE KEY unique_game_date (game_id, date),
                    INDEX idx_game_date (game_id, date),
                    INDEX idx_week_year (week_year)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            connection.commit()
            cursor.close()
            connection.close()
            self.logger.info("Tabelas MySQL criadas com sucesso")
            
        except Error as e:
            self.logger.error(f"Erro ao criar tabelas MySQL: {e}")
            raise
    
    def add_game(self, steam_id, name):
        """Adiciona um novo jogo ao banco"""
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            
            try:
                cursor.execute(
                    "INSERT INTO games (steam_id, name) VALUES (%s, %s)",
                    (steam_id, name)
                )
                game_id = cursor.lastrowid
                self.logger.info(f"Jogo adicionado: {name} (Steam ID: {steam_id})")
                cursor.close()
                connection.close()
                return game_id
                
            except Exception as duplicate_error:
                # Jogo já existe, retorna o ID existente (funciona para ambos conectores)
                cursor.execute(
                    "SELECT id FROM games WHERE steam_id = %s",
                    (steam_id,)
                )
                result = cursor.fetchone()
                game_id = result[0] if result else None
                self.logger.info(f"Jogo já existe: {name} (ID: {game_id})")
                cursor.close()
                connection.close()
                return game_id
                
        except Error as e:
            self.logger.error(f"Erro ao adicionar jogo: {e}")
            raise
    
    def add_price_record(self, game_id, price, timestamp=None, discount_percent=0):
        """Adiciona um registro de preço"""
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            
            # Se não informar timestamp, usa o atual
            if timestamp is None:
                if MYSQL_CONNECTOR == 'mysql.connector':
                    import mysql.connector
                    timestamp_sql = "NOW()"
                    cursor.execute(
                        "INSERT INTO price_history (game_id, price, discount_percent) VALUES (%s, %s, %s)",
                        (game_id, price, discount_percent)
                    )
                else:  # pymysql
                    from datetime import datetime
                    timestamp = datetime.now()
                    cursor.execute(
                        "INSERT INTO price_history (game_id, price, discount_percent, timestamp) VALUES (%s, %s, %s, %s)",
                        (game_id, price, discount_percent, timestamp)
                    )
            else:
                cursor.execute(
                    "INSERT INTO price_history (game_id, price, discount_percent, timestamp) VALUES (%s, %s, %s, %s)",
                    (game_id, price, discount_percent, timestamp)
                )
                
            self.logger.debug(f"Preço adicionado: Game {game_id}, R$ {price}")
            
            cursor.close()
            connection.close()
            
        except Exception as e:
            self.logger.error(f"Erro ao adicionar preço: {e}")
            raise
    
    def get_games(self):
        """Retorna todos os jogos com preços atuais"""
        try:
            connection = self.get_connection()
            
            # Query que busca jogos com o preço mais recente
            query = """
            SELECT 
                g.id,
                g.steam_id,
                g.name,
                g.created_at,
                g.created_at as last_updated,
                COALESCE(latest_price.price, 0) as current_price,
                COALESCE(latest_price.discount_percent, 0) as discount_percent,
                NULL as base_price
            FROM games g
            LEFT JOIN (
                SELECT 
                    ph1.game_id,
                    ph1.price,
                    ph1.discount_percent,
                    ph1.timestamp
                FROM price_history ph1
                INNER JOIN (
                    SELECT game_id, MAX(timestamp) as max_timestamp
                    FROM price_history 
                    GROUP BY game_id
                ) ph2 ON ph1.game_id = ph2.game_id AND ph1.timestamp = ph2.max_timestamp
            ) latest_price ON g.id = latest_price.game_id
            ORDER BY g.name
            """
            
            df = pd.read_sql_query(query, connection)
            connection.close()
            return df
        except Error as e:
            self.logger.error(f"Erro ao buscar jogos: {e}")
            return pd.DataFrame()
    
    def get_price_history(self, game_id=None, start_date=None, end_date=None):
        """Retorna histórico de preços com filtros opcionais"""
        query = """
            SELECT g.name, g.steam_id, ph.price, ph.timestamp as date, 
                   WEEK(ph.timestamp, 1) as week_year
            FROM price_history ph
            JOIN games g ON ph.game_id = g.id
        """
        
        conditions = []
        params = []
        
        if game_id:
            conditions.append("ph.game_id = %s")
            params.append(game_id)
        
        if start_date:
            conditions.append("ph.timestamp >= %s")
            params.append(start_date)
        
        if end_date:
            conditions.append("ph.timestamp <= %s")
            params.append(end_date)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY g.name, ph.timestamp"
        
        try:
            connection = self.get_connection()
            df = pd.read_sql_query(query, connection, params=params)
            connection.close()
            return df
        except Error as e:
            self.logger.error(f"Erro ao buscar histórico: {e}")
            return pd.DataFrame()
    
    def get_latest_prices(self):
        """Retorna os preços mais recentes de cada jogo"""
        query = """
            SELECT g.name, g.steam_id, ph.price, ph.timestamp as date, 
                   WEEK(ph.timestamp, 1) as week_year
            FROM games g
            JOIN price_history ph ON g.id = ph.game_id
            WHERE ph.timestamp = (
                SELECT MAX(timestamp)
                FROM price_history ph2
                WHERE ph2.game_id = g.id
            )
            ORDER BY g.name
        """
        
        try:
            connection = self.get_connection()
            df = pd.read_sql_query(query, connection)
            connection.close()
            return df
        except Error as e:
            self.logger.error(f"Erro ao buscar preços atuais: {e}")
            return pd.DataFrame()
    
    def get_database_stats(self):
        """Retorna estatísticas do banco de dados"""
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            stats = {}
            
            # Número total de jogos
            cursor.execute("SELECT COUNT(*) FROM games")
            stats['total_games'] = cursor.fetchone()[0]
            
            # Número total de registros de preço
            cursor.execute("SELECT COUNT(*) FROM price_history")
            stats['total_price_records'] = cursor.fetchone()[0]
            
            # Data mais antiga e mais recente
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM price_history")
            result = cursor.fetchone()
            min_date, max_date = result if result[0] else (None, None)
            stats['date_range'] = f"{min_date} até {max_date}" if min_date else "Sem dados"
            
            # Jogo com mais registros de preço
            cursor.execute("""
                SELECT g.name, COUNT(ph.id) as count
                FROM games g
                JOIN price_history ph ON g.id = ph.game_id
                GROUP BY g.id, g.name
                ORDER BY count DESC
                LIMIT 1
            """)
            result = cursor.fetchone()
            if result:
                stats['game_most_records'] = f"{result[0]} ({result[1]} registros)"
            else:
                stats['game_most_records'] = "Nenhum"
            
            cursor.close()
            connection.close()
            return stats
            
        except Error as e:
            self.logger.error(f"Erro ao buscar estatísticas: {e}")
            return {
                'total_games': 0,
                'total_price_records': 0,
                'date_range': 'Erro',
                'game_most_records': 'Erro'
            }

if __name__ == "__main__":
    # Teste básico
    try:
        db = DatabaseManager()
        print("✅ Banco MySQL inicializado com sucesso!")
        
        stats = db.get_database_stats()
        print("\n📊 Estatísticas do banco:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        print("🔧 Execute: python setup_mysql.py")
