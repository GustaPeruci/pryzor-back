"""
Configuração do banco de dados MySQL para o projeto Pryzor
Arquivo de configuração separado para facilitar mudanças
"""

import os
from pathlib import Path

# Configurações do MySQL
MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',  # Ajuste conforme necessário
    'password': 'root',  # Deixe vazio se não houver senha ou configure
    'database': 'pryzor_db',
    'charset': 'utf8mb4',
    'autocommit': True,
    'auth_plugin': 'mysql_native_password'  # Para compatibilidade
}

# Configurações de conexão alternativas para diferentes ambientes
MYSQL_CONFIGS = {
    'local': {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': 'root',
        'database': 'pryzor_db',
        'auth_plugin': 'mysql_native_password'
    },
    'docker': {
        'host': 'localhost',
        'port': 3306,
        'user': 'pryzor_user',
        'password': 'pryzor_pass',
        'database': 'pryzor_db'
    },
        'xampp': {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': 'root',  # XAMPP/Local (senha root)
        'database': 'pryzor_db'
    }
}

def get_mysql_config(environment='local'):
    """Retorna configuração do MySQL baseada no ambiente"""
    return MYSQL_CONFIGS.get(environment, MYSQL_CONFIGS['local'])

def get_connection_string(environment='local'):
    """Retorna string de conexão SQLAlchemy para MySQL"""
    config = get_mysql_config(environment)
    if config['password']:
        return f"mysql+pymysql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}?charset=utf8mb4"
    else:
        return f"mysql+pymysql://{config['user']}@{config['host']}:{config['port']}/{config['database']}?charset=utf8mb4"

# Instruções de configuração
SETUP_INSTRUCTIONS = """
🔧 CONFIGURAÇÃO DO MYSQL:

1. Instale o MySQL Server:
   - Windows: https://dev.mysql.com/downloads/installer/
   - XAMPP: https://www.apachefriends.org/
   - Docker: docker run -d -p 3306:3306 --name mysql-pryzor -e MYSQL_ROOT_PASSWORD=pryzor_pass mysql:8.0

2. Configure a conexão em mysql_config.py:
   - Ajuste host, user, password conforme sua instalação
   - Escolha o ambiente adequado (local, docker, xampp)

3. Execute setup_mysql.py para criar o banco:
   python setup_mysql.py

4. O projeto criará automaticamente as tabelas necessárias
"""

if __name__ == "__main__":
    print(SETUP_INSTRUCTIONS)
    print("\n📋 Configuração atual:")
    config = get_mysql_config()
    for key, value in config.items():
        if key == 'password':
            print(f"  {key}: {'***' if value else '(sem senha)'}")
        else:
            print(f"  {key}: {value}")
