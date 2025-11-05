"""
Script para inicializar o banco de dados MySQL no CI/CD
Cria as tabelas e insere dados mínimos se necessário
"""

from database.connection import SessionLocal, engine
# Importar TODOS os modelos para que o Base.metadata os conheça
from database.models import Base, Game, PriceHistory, PricePrediction, ModelMetadata, DataProcessingLog

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
except Exception as e:
    print(f"Erro ao inserir dados: {e}")
    raise
