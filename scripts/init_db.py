"""
Script para inicializar o banco de dados MySQL no CI/CD
Cria as tabelas e insere dados mínimos se necessário
"""

from database.connection import SessionLocal, engine
from database.models import Base, Game
from sqlalchemy.orm import Session

# Cria todas as tabelas
print("Criando tabelas no banco de dados...")
Base.metadata.create_all(bind=engine)
print("Tabelas criadas com sucesso!")

# Insere dados mínimos se não existirem
with SessionLocal() as session:
    if session.query(Game).count() == 0:
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
