"""
Script para inicializar o banco de dados MySQL no CI/CD
Cria as tabelas e insere dados mínimos se necessário
"""

from database.connection import SessionLocal, engine
# Importar TODOS os modelos para que o Base.metadata os conheça
from database.models import Base, Game, PriceHistory, PricePrediction, ModelMetadata, DataProcessingLog
import pandas as pd
from pathlib import Path

# Cria todas as tabelas
print("Criando tabelas no banco de dados...")
try:
    Base.metadata.create_all(bind=engine)
    print("Tabelas criadas com sucesso!")
except Exception as e:
    print(f"Erro ao criar tabelas: {e}")
    raise

# Insere dados mínimos se não existirem
print("Verificando dados iniciais...")
try:
    with SessionLocal() as session:
        count = session.query(Game).count()
        print(f"Jogos no banco: {count}")
        
        if count == 0:
            # Exemplo de dados mínimos
            jogos = [
                Game(appid=730, name="Counter-Strike: Global Offensive", type="game", free_to_play=True),
                Game(appid=271590, name="Grand Theft Auto V", type="game", free_to_play=False),
                Game(appid=440, name="Team Fortress 2", type="game", free_to_play=True)
            ]
            session.add_all(jogos)
            session.commit()
            print("Jogos mínimos inseridos.")
        else:
            print("Jogos já existem no banco.")

        # Importar histórico de preços do dataset gerado
        price_csv = Path(__file__).parent.parent / "data" / "data_with_binary_target.csv"
        app_info_csv = Path(__file__).parent.parent / "data" / "applicationInformation.csv"
        if price_csv.exists():
            print("Importando registros de preço do dataset...")
            df = pd.read_csv(price_csv)
            # Carregar informações dos jogos
            # Tenta múltiplos encodings para ler o CSV
            try:
                app_info = pd.read_csv(app_info_csv, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    app_info = pd.read_csv(app_info_csv, encoding='latin-1')
                except:
                    app_info = pd.read_csv(app_info_csv, encoding='cp1252')
            app_info = app_info.set_index('appid')
            # Garantir que todos appids do dataset estejam na tabela games
            appids_precos = set(df['appid'].unique())
            appids_existentes = set([g.appid for g in session.query(Game.appid).all()])
            novos_appids = appids_precos - appids_existentes
            novos_jogos = []
            for appid in novos_appids:
                if appid in app_info.index:
                    row = app_info.loc[appid]
                    nome = row['name'] if 'name' in row else f"Jogo {appid}"
                    tipo = row['type'] if 'type' in row else "game"
                    free = bool(row['freetoplay']) if 'freetoplay' in row and not pd.isnull(row['freetoplay']) else False
                    # release_date: tenta converter para YYYY-MM-DD
                    release_date = None
                    if 'releasedate' in row and not pd.isnull(row['releasedate']):
                        raw_date = str(row['releasedate'])
                        try:
                            # Tenta formatos comuns
                            from datetime import datetime
                            for fmt in ("%d-%b-%y", "%d-%b-%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d-%m-%y"): 
                                try:
                                    release_date = datetime.strptime(raw_date, fmt).strftime("%Y-%m-%d")
                                    break
                                except ValueError:
                                    continue
                        except Exception:
                            release_date = None
                else:
                    nome = f"Jogo {appid}"
                    tipo = "game"
                    free = False
                    release_date = None
                novos_jogos.append(Game(appid=appid, name=nome, type=tipo, free_to_play=free, release_date=release_date))
            if novos_jogos:
                print(f"Inserindo {len(novos_jogos)} novos jogos do dataset...")
                session.add_all(novos_jogos)
                session.commit()
            # Agora insere PriceHistory
            for _, row in df.iterrows():
                ph = PriceHistory(
                    appid=int(row['appid']),
                    date=pd.to_datetime(row['date']),
                    initial_price=float(row['initial_price']),
                    final_price=float(row['final_price']),
                    discount=int(row['discount'])
                )
                session.add(ph)
            session.commit()
            print(f"Registros de preço importados: {len(df)}")
        else:
            print("Arquivo data_with_binary_target.csv não encontrado. Nenhum registro de preço importado.")
except Exception as e:
    print(f"Erro ao inserir dados: {e}")
    raise
