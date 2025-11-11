"""
Script de setup do banco de dados MySQL para o Pryzor
Cria o banco e as tabelas necessárias
"""

import pymysql
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  
# Ler configurações do .env
env_file = Path(__file__).parent / '.env'
config = {}
if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                config[key] = value

# Configurações do MySQL
# MYSQL_HOST = config.get('MYSQL_HOST', 'localhost')
# MYSQL_PORT = int(config.get('MYSQL_PORT', 3306))
# MYSQL_USER = config.get('MYSQL_USER', 'root')
# MYSQL_PASSWORD = config.get('MYSQL_PASSWORD', 'root')
# MYSQL_DATABASE = config.get('MYSQL_DATABASE', 'steam_pryzor')

MYSQL_HOST = config.get('MYSQL_HOST', 'db4free.net')
MYSQL_PORT = int(config.get('MYSQL_PORT', 3306))
MYSQL_USER = config.get('MYSQL_USER', 'root_gcpa')
MYSQL_PASSWORD = config.get('MYSQL_PASSWORD', 'Q%aQCwa5acjY75z')
MYSQL_DATABASE = config.get('MYSQL_DATABASE', 'Q%aQCwa5acjY75z')

# DATABASE_URL=mysql+pymysql://root_gcpa:Q%aQCwa5acjY75z @db4free.net:3306/steam_pryzor
# MYSQL_HOST=db4free.net
# MYSQL_PORT=3306
# MYSQL_USER=root_gcpa
# MYSQL_PASSWORD=Q%aQCwa5acjY75z
# MYSQL_DATABASE=Q%aQCwa5acjY75z

def create_database():
    """Cria o banco de dados e as tabelas"""
    print(f"🔌 Conectando ao MySQL em {MYSQL_HOST}:{MYSQL_PORT}...")
    
    try:
        # Conectar ao MySQL (sem especificar database)
        connection = pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        
        # Criar banco de dados
        print(f"📦 Criando banco de dados '{MYSQL_DATABASE}'...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DATABASE} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"✅ Banco '{MYSQL_DATABASE}' criado/verificado com sucesso!")
        
        # Usar o banco criado
        cursor.execute(f"USE {MYSQL_DATABASE}")
        
        # Criar tabela de jogos
        print("📋 Criando tabela 'games'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS games (
                appid INT PRIMARY KEY,
                name VARCHAR(500) NOT NULL,
                type VARCHAR(50),
                release_date DATE,
                free_to_play TINYINT(1) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_name (name(100)),
                INDEX idx_type (type),
                INDEX idx_free_to_play (free_to_play)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("✅ Tabela 'games' criada com sucesso!")
        
        # Criar tabela de histórico de preços
        print("📋 Criando tabela 'price_history'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                appid INT NOT NULL,
                date DATE NOT NULL,
                final_price DECIMAL(10,2),
                initial_price DECIMAL(10,2),
                discount INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (appid) REFERENCES games(appid) ON DELETE CASCADE,
                UNIQUE KEY unique_price (appid, date),
                INDEX idx_appid (appid),
                INDEX idx_date (date),
                INDEX idx_discount (discount)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("✅ Tabela 'price_history' criada com sucesso!")
        
        # Verificar quantos registros existem
        cursor.execute("SELECT COUNT(*) FROM games")
        game_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM price_history")
        price_count = cursor.fetchone()[0]
        
        print(f"\n📊 Status do banco de dados:")
        print(f"   - Jogos cadastrados: {game_count:,}")
        print(f"   - Registros de preço: {price_count:,}")
        
        if game_count == 0:
            print(f"\n⚠️  O banco está vazio!")
            print(f"   Execute o script de importação de dados para popular o banco.")
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print(f"\n🎉 Setup concluído com sucesso!")
        print(f"   Você já pode rodar o backend: python -m src.main")
        
    except pymysql.Error as e:
        print(f"❌ Erro ao conectar/criar banco: {e}")
        print(f"\n💡 Verifique se:")
        print(f"   1. O MySQL está rodando")
        print(f"   2. As credenciais no .env estão corretas")
        print(f"   3. O usuário {MYSQL_USER} tem permissões para criar databases")
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 PRYZOR - Setup do Banco de Dados MySQL")
    print("=" * 60)
    print()
    
    if create_database():
        print("\n✅ Tudo pronto para usar o Pryzor!")
    else:
        print("\n❌ Falha no setup. Corrija os erros e tente novamente.")
