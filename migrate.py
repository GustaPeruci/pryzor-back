"""
PRYZOR - Executor de Migrações
=============================
Script para executar migrações e inicializar o banco de dados.

Este script pode ser executado manualmente ou chamado pela aplicação
quando necessário.

Uso:
    python migrate.py
"""

import os
import sys

# Adiciona o diretório src ao path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.migrations import CREATE_TABLES_SQL, INITIAL_DATA_SQL
from src.database_manager import get_mysql_config

def run_migrations():
    """Executa todas as migrações necessárias"""
    try:
        # Importa o conector MySQL
        import pymysql
        
        # Obtém configuração do banco
        config = get_mysql_config()
        print(f"🔧 Conectando ao MySQL em {config['host']}:{config['port']}")
        
        # Conecta ao MySQL
        connection = pymysql.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        print("✅ Conexão estabelecida com sucesso!")
        
        # Executa criação de tabelas
        print("📋 Criando tabelas...")
        statements = CREATE_TABLES_SQL.strip().split(';')
        for statement in statements:
            if statement.strip():
                cursor.execute(statement)
        
        print("✅ Tabelas criadas com sucesso!")
        
        # Executa inserção de dados iniciais
        print("📊 Inserindo dados iniciais...")
        statements = INITIAL_DATA_SQL.strip().split(';')
        for statement in statements:
            if statement.strip():
                cursor.execute(statement)
        
        # Commit das mudanças
        connection.commit()
        print("✅ Dados iniciais inseridos com sucesso!")
        
        # Verifica se os dados foram inseridos
        cursor.execute("SELECT COUNT(*) FROM games")
        game_count = cursor.fetchone()[0]
        print(f"📈 Total de jogos na base: {game_count}")
        
        cursor.execute("SELECT COUNT(*) FROM price_history")
        history_count = cursor.fetchone()[0]
        print(f"📈 Total de registros de histórico: {history_count}")
        
        cursor.close()
        connection.close()
        
        print("🎉 Migração concluída com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro durante a migração: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Iniciando migração do banco de dados PRYZOR...")
    success = run_migrations()
    sys.exit(0 if success else 1)
