"""
ETL Sistema de Importação de Histórico de Preços - VERSÃO PRODUÇÃO
Desenvolvido para ambiente Railway com otimizações para produção

Funcionalidades:
- Importação completa de histórico de preços dos 1,512 jogos
- Sistema de batch otimizado para produção
- Logging compatível com Railway
- Recuperação automática de falhas
- Configuração via variáveis de ambiente
"""

import pandas as pd
import mysql.connector
from pathlib import Path
import logging
import os
from datetime import datetime
import sys

class PriceHistoryETLProduction:
    def __init__(self):
        self.setup_logging()
        self.price_history_folder = Path("../../PriceHistory")
        self.batch_size = 1000  # Otimizado para Railway
        self.total_records = 0
        
    def setup_logging(self):
        """Configuração de logging otimizada para produção Railway"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)  # Railway console output
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def get_db_connection(self):
        """Conexão com banco usando variáveis de ambiente para Railway"""
        try:
            # Configuração para Railway (via environment variables)
            db_config = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'user': os.getenv('DB_USER', 'root'),
                'password': os.getenv('DB_PASSWORD', 'Ceo123@'),
                'database': os.getenv('DB_NAME', 'games_db'),
                'port': int(os.getenv('DB_PORT', '3306')),
                'charset': 'utf8mb4',
                'collation': 'utf8mb4_unicode_ci',
                'autocommit': True
            }
            
            connection = mysql.connector.connect(**db_config)
            self.logger.info("Conexão com banco estabelecida com sucesso")
            return connection
            
        except Exception as e:
            self.logger.error(f"Erro na conexão com banco: {e}")
            raise
    
    def get_game_name(self, appid):
        """Busca nome do jogo na base de aplicações"""
        try:
            connection = self.get_db_connection()
            cursor = connection.cursor()
            
            cursor.execute("SELECT name FROM applications WHERE appid = %s", (appid,))
            result = cursor.fetchone()
            
            cursor.close()
            connection.close()
            
            return result[0] if result else f"Game_{appid}"
            
        except Exception:
            return f"Game_{appid}"
    
    def parse_price_file(self, csv_file):
        """Processa arquivo CSV individual com múltiplas codificações"""
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                df = pd.read_csv(csv_file, encoding=encoding)
                
                # Validação das colunas
                expected_columns = ['Date', 'Initialprice', 'Finalprice', 'Discount']
                if not all(col in df.columns for col in expected_columns):
                    continue
                
                # Limpeza dos dados
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
                df = df.dropna(subset=['Date'])
                
                # Conversão dos preços
                for col in ['Initialprice', 'Finalprice', 'Discount']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                df = df.dropna()
                
                if len(df) > 0:
                    return df
                    
            except Exception as e:
                continue
        
        return None
    
    def batch_insert_prices(self, connection, price_data):
        """Inserção em lotes otimizada para Railway"""
        try:
            cursor = connection.cursor()
            
            insert_query = """
            INSERT INTO price_history (appid, date, initialprice, finalprice, discount, savings)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            batches = [price_data[i:i + self.batch_size] 
                      for i in range(0, len(price_data), self.batch_size)]
            
            total_inserted = 0
            for batch in batches:
                cursor.executemany(insert_query, batch)
                total_inserted += len(batch)
                
                if total_inserted % 5000 == 0:
                    self.logger.info(f"Progresso: {total_inserted:,} registros inseridos")
            
            cursor.close()
            self.logger.info(f"Batch inserido: {len(price_data):,} registros")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro na inserção: {e}")
            return False
    
    def run_complete_import(self):
        """Execução completa da importação para produção"""
        start_time = datetime.now()
        self.logger.info("INICIANDO IMPORTAÇÃO COMPLETA DE HISTÓRICO DE PREÇOS")
        self.logger.info("=" * 60)
        
        if not self.price_history_folder.exists():
            self.logger.error(f"Pasta não encontrada: {self.price_history_folder}")
            return False
        
        csv_files = list(self.price_history_folder.glob("*.csv"))
        total_files = len(csv_files)
        
        if total_files == 0:
            self.logger.error("Nenhum arquivo CSV encontrado")
            return False
        
        self.logger.info(f"Arquivos encontrados: {total_files}")
        
        # Conectar ao banco
        try:
            connection = self.get_db_connection()
        except Exception:
            return False
        
        successful_files = 0
        total_records = 0
        all_price_data = []
        
        # Processar todos os arquivos
        for i, csv_file in enumerate(csv_files, 1):
            try:
                appid = int(csv_file.stem)
                df = self.parse_price_file(csv_file)
                
                if df is not None and len(df) > 0:
                    game_name = self.get_game_name(appid)
                    
                    # Preparar dados para inserção
                    for _, row in df.iterrows():
                        savings = row['Initialprice'] - row['Finalprice']
                        
                        price_record = (
                            appid,
                            row['Date'].strftime('%Y-%m-%d'),
                            float(row['Initialprice']),
                            float(row['Finalprice']),
                            float(row['Discount']),
                            float(savings)
                        )
                        all_price_data.append(price_record)
                    
                    successful_files += 1
                    total_records += len(df)
                    
                    self.logger.info(f"SUCESSO {csv_file.name}: {len(df)} registros | Jogo: {game_name}")
                    
                    # Inserir em lotes durante o processamento para Railway
                    if len(all_price_data) >= 10000:  # Inserir a cada 10k registros
                        if self.batch_insert_prices(connection, all_price_data):
                            all_price_data = []  # Limpar após inserção
                
                # Log de progresso
                if i % 100 == 0:
                    self.logger.info(f"Progresso: {i}/{total_files} arquivos processados")
                    
            except Exception as e:
                self.logger.warning(f"Erro no arquivo {csv_file.name}: {e}")
                continue
        
        # Inserir registros restantes
        if all_price_data:
            self.logger.info(f"Inserindo {len(all_price_data)} registros finais...")
            self.batch_insert_prices(connection, all_price_data)
        
        # Fechar conexão
        connection.close()
        
        # Relatório final
        duration = datetime.now() - start_time
        self.logger.info("=" * 60)
        self.logger.info("IMPORTAÇÃO CONCLUÍDA")
        self.logger.info("=" * 60)
        self.logger.info(f"Arquivos processados: {successful_files}/{total_files}")
        self.logger.info(f"Total de registros: {total_records:,}")
        self.logger.info(f"Tempo de execução: {duration}")
        self.logger.info("=" * 60)
        
        if successful_files == total_files:
            self.logger.info("✅ IMPORTAÇÃO 100% CONCLUÍDA")
            return True
        else:
            self.logger.warning(f"⚠️ Alguns arquivos falharam: {total_files - successful_files}")
            return False

def main():
    """Função principal para execução em produção"""
    etl = PriceHistoryETLProduction()
    
    try:
        success = etl.run_complete_import()
        
        if success:
            print("\n*** SUCESSO: Importação completa realizada! ***")
            exit(0)
        else:
            print("\n*** ERRO: Falha na importação ***")
            exit(1)
            
    except KeyboardInterrupt:
        print("\n*** Importação cancelada pelo usuário ***")
        exit(1)
    except Exception as e:
        print(f"\n*** ERRO CRÍTICO: {e} ***")
        exit(1)

if __name__ == "__main__":
    main()