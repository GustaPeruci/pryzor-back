"""
Script para importar dataset completo para o banco MySQL
Importa jogos do applicationInformation.csv e histórico de preços da pasta PriceHistory/
"""

import pymysql
import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatasetImporter:
    def __init__(self, host='localhost', user='root', password='root', database='steam_pryzor'):
        """Inicializa conexão com MySQL"""
        self.connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        self.cursor = self.connection.cursor()
        logger.info(f"✅ Conectado ao banco {database}")

    def parse_date(self, date_str: str) -> str:
        """Converte data do formato DD-MMM-YY para YYYY-MM-DD"""
        if not date_str or date_str.strip() == '':
            return None
        
        try:
            # Formato: 21-Dec-17
            dt = datetime.strptime(date_str, '%d-%b-%y')
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            try:
                # Formato alternativo: 9-Jul-13
                dt = datetime.strptime(date_str, '%-d-%b-%y')
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                logger.warning(f"Data inválida: {date_str}")
                return None

    def import_games(self, csv_path: str) -> Dict[int, int]:
        """
        Importa jogos do applicationInformation.csv
        Retorna dict com {appid: price_records_count} para atualizar depois
        """
        logger.info("📥 Importando jogos do applicationInformation.csv...")
        
        games_imported = 0
        games_skipped = 0
        appid_map = {}

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                appid = row['appid'].strip()
                game_type = row['type'].strip()
                name = row['name'].strip()
                releasedate = row['releasedate'].strip()
                freetoplay = row['freetoplay'].strip()

                # Pular entradas sem appid ou sem tipo (incompletas)
                if not appid or not game_type:
                    games_skipped += 1
                    continue

                # Converter data
                release_date_formatted = self.parse_date(releasedate)

                # Converter freetoplay para booleano
                is_free = 1 if freetoplay == '1' else 0

                try:
                    # INSERT com ON DUPLICATE KEY UPDATE para evitar erros
                    sql = """
                    INSERT INTO games (appid, name, type, releasedate, freetoplay, price_records)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        name = VALUES(name),
                        type = VALUES(type),
                        releasedate = VALUES(releasedate),
                        freetoplay = VALUES(freetoplay)
                    """
                    self.cursor.execute(sql, (
                        int(appid),
                        name,
                        game_type,
                        release_date_formatted,
                        is_free,
                        0  # price_records será atualizado depois
                    ))
                    
                    appid_map[int(appid)] = 0  # Inicializa contador
                    games_imported += 1

                    if games_imported % 100 == 0:
                        logger.info(f"  {games_imported} jogos importados...")

                except Exception as e:
                    logger.error(f"Erro ao importar jogo {appid} ({name}): {e}")
                    continue

        self.connection.commit()
        logger.info(f"✅ {games_imported} jogos importados, {games_skipped} pulados")
        return appid_map

    def import_price_history(self, price_history_dir: str, appid_map: Dict[int, int]) -> None:
        """
        Importa histórico de preços da pasta PriceHistory/
        Cada arquivo CSV tem o nome do appid (ex: 10.csv)
        """
        logger.info("📥 Importando histórico de preços...")
        
        price_records_imported = 0
        files_processed = 0
        files_skipped = 0

        # Listar todos os arquivos .csv na pasta PriceHistory
        price_history_path = Path(price_history_dir)
        csv_files = list(price_history_path.glob('*.csv'))
        total_files = len(csv_files)

        logger.info(f"  Encontrados {total_files} arquivos de histórico de preços")

        for csv_file in csv_files:
            # Extrair appid do nome do arquivo (ex: 10.csv -> 10)
            try:
                appid = int(csv_file.stem)
            except ValueError:
                logger.warning(f"Nome de arquivo inválido: {csv_file.name}")
                files_skipped += 1
                continue

            # Verificar se o jogo existe no banco
            if appid not in appid_map:
                logger.warning(f"Jogo {appid} não encontrado na tabela games, pulando...")
                files_skipped += 1
                continue

            # Ler e importar registros de preço
            records_count = 0
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                batch = []
                for row in reader:
                    date_str = row['Date'].strip()
                    final_price = row['Finalprice'].strip()
                    discount = row['Discount'].strip()

                    # Converter data para formato MySQL
                    try:
                        dt = datetime.strptime(date_str, '%Y-%m-%d')
                        date_formatted = dt.strftime('%Y-%m-%d')
                    except ValueError:
                        continue

                    # Preparar dados para batch insert
                    batch.append((
                        appid,
                        date_formatted,
                        float(final_price) if final_price else 0.0,
                        int(discount) if discount else 0
                    ))
                    records_count += 1

                    # Executar batch a cada 500 registros
                    if len(batch) >= 500:
                        self._insert_price_batch(batch)
                        price_records_imported += len(batch)
                        batch = []

                # Inserir registros restantes
                if batch:
                    self._insert_price_batch(batch)
                    price_records_imported += len(batch)

            # Atualizar contador no mapa
            appid_map[appid] = records_count
            files_processed += 1

            if files_processed % 50 == 0:
                logger.info(f"  {files_processed}/{total_files} arquivos processados ({price_records_imported} registros)...")

        self.connection.commit()
        logger.info(f"✅ {price_records_imported} registros de preço importados de {files_processed} arquivos")
        logger.info(f"⚠️  {files_skipped} arquivos pulados")

    def _insert_price_batch(self, batch: List[Tuple]) -> None:
        """Insere batch de registros de preço"""
        if not batch:
            return

        sql = """
        INSERT INTO price_history (appid, date, final_price, discount)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            final_price = VALUES(final_price),
            discount = VALUES(discount)
        """
        try:
            self.cursor.executemany(sql, batch)
        except Exception as e:
            logger.error(f"Erro ao inserir batch de preços: {e}")

    def update_price_records_count(self, appid_map: Dict[int, int]) -> None:
        """Atualiza o campo price_records na tabela games"""
        logger.info("📝 Atualizando contador de registros de preço...")
        
        updated = 0
        for appid, count in appid_map.items():
            if count > 0:
                sql = "UPDATE games SET price_records = %s WHERE appid = %s"
                self.cursor.execute(sql, (count, appid))
                updated += 1

        self.connection.commit()
        logger.info(f"✅ {updated} jogos atualizados com contador de price_records")

    def get_statistics(self) -> None:
        """Exibe estatísticas do banco após importação"""
        logger.info("\n📊 Estatísticas do banco de dados:")
        
        # Total de jogos
        self.cursor.execute("SELECT COUNT(*) as total FROM games")
        total_games = self.cursor.fetchone()['total']
        logger.info(f"  Total de jogos: {total_games}")

        # Total de registros de preço
        self.cursor.execute("SELECT COUNT(*) as total FROM price_history")
        total_prices = self.cursor.fetchone()['total']
        logger.info(f"  Total de registros de preço: {total_prices}")

        # Jogos com histórico de preços
        self.cursor.execute("SELECT COUNT(*) as total FROM games WHERE price_records > 0")
        games_with_prices = self.cursor.fetchone()['total']
        logger.info(f"  Jogos com histórico: {games_with_prices}")

        # Jogos gratuitos
        self.cursor.execute("SELECT COUNT(*) as total FROM games WHERE freetoplay = 1")
        free_games = self.cursor.fetchone()['total']
        logger.info(f"  Jogos gratuitos: {free_games}")

        # Top 5 jogos com mais registros
        self.cursor.execute("""
            SELECT name, price_records 
            FROM games 
            WHERE price_records > 0
            ORDER BY price_records DESC 
            LIMIT 5
        """)
        top_games = self.cursor.fetchall()
        logger.info("\n  Top 5 jogos com mais registros de preço:")
        for game in top_games:
            logger.info(f"    - {game['name']}: {game['price_records']} registros")

    def close(self):
        """Fecha conexão com banco"""
        self.cursor.close()
        self.connection.close()
        logger.info("🔒 Conexão fechada")


def main():
    """Função principal"""
    logger.info("🚀 Iniciando importação do dataset...")
    logger.info("=" * 60)
    
    # Caminhos dos dados
    base_dir = Path(__file__).parent
    data_dir = base_dir / 'data'
    games_csv = data_dir / 'applicationInformation.csv'
    price_history_dir = data_dir / 'PriceHistory'

    # Verificar se arquivos existem
    if not games_csv.exists():
        logger.error(f"❌ Arquivo não encontrado: {games_csv}")
        return
    
    if not price_history_dir.exists():
        logger.error(f"❌ Diretório não encontrado: {price_history_dir}")
        return

    try:
        # Inicializar importador
        importer = DatasetImporter()

        # 1. Importar jogos
        appid_map = importer.import_games(str(games_csv))

        # 2. Importar histórico de preços
        importer.import_price_history(str(price_history_dir), appid_map)

        # 3. Atualizar contadores
        importer.update_price_records_count(appid_map)

        # 4. Exibir estatísticas
        importer.get_statistics()

        # Fechar conexão
        importer.close()

        logger.info("\n" + "=" * 60)
        logger.info("✅ Importação concluída com sucesso!")
        logger.info("🎮 Banco de dados pronto para uso!")

    except pymysql.Error as e:
        logger.error(f"❌ Erro de conexão com MySQL: {e}")
        logger.error("💡 Verifique se o banco 'steam_pryzor' foi criado (rode setup_database.py)")
    except Exception as e:
        logger.error(f"❌ Erro durante importação: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
