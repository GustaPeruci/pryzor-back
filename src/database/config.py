# Configuração de Banco MySQL - Pryzor
# MySQL Production Configuration

import os
from typing import Dict, Any
from urllib.parse import quote_plus
from pathlib import Path

# Carregar .env se existir
env_file = Path(__file__).parent.parent.parent.parent / '.env'
if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

class DatabaseConfig:
    """Configuração MySQL para todos os ambientes"""
    
    def __init__(self, env: str = None):
        self.env = env or os.getenv('ENVIRONMENT', 'development')
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Carrega configuração MySQL baseada no ambiente"""
        # Configurações base do MySQL
        base_config = {
            'type': 'mysql',
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'database': os.getenv('DB_NAME', 'steam_pryzor'),
            'username': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASS', ''),  # Senha vazia por padrão
            'charset': 'utf8mb4'
        }
        
        return base_config
    
    def get_config(self) -> Dict[str, Any]:
        """Retorna configuração MySQL"""
        return self.config
    
    def get_connection_string(self) -> str:
        """Gera string de conexão MySQL"""
        config = self.get_config()
        
        password = quote_plus(config['password']) if config['password'] else ''
        password_part = f":{password}" if password else ""
        
        return (f"mysql+pymysql://{config['username']}{password_part}"
               f"@{config['host']}:{config['port']}/{config['database']}"
               f"?charset={config['charset']}")
    
    def is_mysql(self) -> bool:
        """Sempre True - apenas MySQL"""
        return True

# Instância global
db_config = DatabaseConfig()

# Para facilitar imports
def get_db_config():
    return db_config

def get_connection_string():
    return db_config.get_connection_string()

def is_mysql():
    return True

# SQLite não é suportado - MySQL apenas