"""
Configuração do banco de dados MySQL para o projeto Pryzor
Arquivo de configuração separado para facilitar mudanças
"""

import os
from pathlib import Path

def get_database_url():
    """
    Retorna a URL de conexão do banco de dados.
    Prioriza variáveis de ambiente do Railway, depois configurações locais.
    """
    # Verifica se está no Railway (produção)
    if os.environ.get('RAILWAY_ENVIRONMENT'):
        # Configuração do Railway
        host = os.environ.get('MYSQL_HOST', 'mysql.railway.internal')
        port = os.environ.get('MYSQL_PORT', '3306')
        user = os.environ.get('MYSQL_USER', 'root')
        password = os.environ.get('MYSQL_PASSWORD', '')
        database = os.environ.get('MYSQL_DATABASE', 'railway')
        
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"
    
    else:
        # Configuração local para desenvolvimento
        return "mysql+pymysql://root:root@localhost:3306/pryzor_db?charset=utf8mb4"

def get_mysql_connection_info():
    """Retorna informações sobre a conexão atual"""
    if os.environ.get('RAILWAY_ENVIRONMENT'):
        return {
            'environment': 'Railway (Production)',
            'host': os.environ.get('MYSQL_HOST', 'N/A'),
            'database': os.environ.get('MYSQL_DATABASE', 'N/A'),
            'user': os.environ.get('MYSQL_USER', 'N/A')
        }
    else:
        return {
            'environment': 'Local Development',
            'host': 'localhost',
            'database': 'pryzor_db',
            'user': 'root'
        }

# Instruções de configuração
SETUP_INSTRUCTIONS = """
🔧 CONFIGURAÇÃO DO MYSQL:

PRODUÇÃO (Railway):
- As variáveis de ambiente são configuradas automaticamente
- Banco: MySQL no Railway
- Conexão automática via MYSQL_HOST, MYSQL_USER, etc.

DESENVOLVIMENTO LOCAL:
1. Instale o MySQL Server:
   - Windows: https://dev.mysql.com/downloads/installer/
   - XAMPP: https://www.apachefriends.org/
   - Docker: docker run -d -p 3306:3306 --name mysql-pryzor -e MYSQL_ROOT_PASSWORD=root mysql:8.0

2. Crie o banco 'pryzor_db' localmente
3. Configure user: 'root', password: 'root'

4. Execute setup_mysql.py para criar as tabelas:
   python setup_mysql.py
"""

if __name__ == "__main__":
    print(SETUP_INSTRUCTIONS)
    print("\n📋 Configuração atual:")
    info = get_mysql_connection_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    print(f"\n🔗 Database URL: {get_database_url()[:50]}...")
