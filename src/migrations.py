"""
PRYZOR - Migração Inicial do Banco de Dados
==========================================
Este arquivo contém todas as queries SQL necessárias para criar
as tabelas e dados iniciais do sistema PRYZOR.

Autor: Gustavo Peruci
Data: Agosto 2025
"""

# SQL para criar todas as tabelas necessárias
CREATE_TABLES_SQL = """
-- Tabela de jogos
CREATE TABLE IF NOT EXISTS games (
    steam_id INT PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    preco_atual DECIMAL(10,2) DEFAULT 0.00,
    desconto_atual INT DEFAULT 0,
    categoria VARCHAR(100),
    data_lancamento DATE,
    avaliacoes_positivas INT DEFAULT 0,
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_nome (nome),
    INDEX idx_categoria (categoria),
    INDEX idx_preco (preco_atual)
);

-- Tabela de histórico de preços
CREATE TABLE IF NOT EXISTS price_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    steam_id INT NOT NULL,
    preco DECIMAL(10,2) NOT NULL,
    desconto INT DEFAULT 0,
    data_coleta DATE NOT NULL,
    timestamp_coleta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (steam_id) REFERENCES games(steam_id) ON DELETE CASCADE,
    INDEX idx_steam_id (steam_id),
    INDEX idx_data (data_coleta),
    UNIQUE KEY unique_game_date (steam_id, data_coleta)
);

-- Tabela de previsões
CREATE TABLE IF NOT EXISTS predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    steam_id INT NOT NULL,
    preco_atual DECIMAL(10,2) NOT NULL,
    preco_previsto DECIMAL(10,2) NOT NULL,
    desconto_esperado INT DEFAULT 0,
    score_compra INT DEFAULT 0,
    recomendacao VARCHAR(100),
    confianca INT DEFAULT 0,
    data_previsao DATE NOT NULL,
    modelo_usado VARCHAR(50) DEFAULT 'linear_regression',
    timestamp_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (steam_id) REFERENCES games(steam_id) ON DELETE CASCADE,
    INDEX idx_steam_id (steam_id),
    INDEX idx_data_previsao (data_previsao),
    INDEX idx_score (score_compra)
);

-- Tabela de validações temporais
CREATE TABLE IF NOT EXISTS temporal_validations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    steam_id INT NOT NULL,
    data_previsao DATE NOT NULL,
    preco_previsto DECIMAL(10,2) NOT NULL,
    preco_real DECIMAL(10,2) NOT NULL,
    erro_absoluto DECIMAL(10,2) NOT NULL,
    erro_percentual DECIMAL(5,2) NOT NULL,
    timestamp_validacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (steam_id) REFERENCES games(steam_id) ON DELETE CASCADE,
    INDEX idx_steam_id (steam_id),
    INDEX idx_data_previsao (data_previsao),
    INDEX idx_erro (erro_percentual)
);
"""

# Dados iniciais para demonstração
INITIAL_DATA_SQL = """
-- Inserir jogos de exemplo
INSERT IGNORE INTO games (steam_id, nome, preco_atual, desconto_atual, categoria, data_lancamento, avaliacoes_positivas) VALUES
(730, 'Counter-Strike 2', 0.00, 0, 'FPS', '2012-08-21', 85),
(570, 'Dota 2', 0.00, 0, 'MOBA', '2013-07-09', 82),
(440, 'Team Fortress 2', 0.00, 0, 'FPS', '2007-10-10', 92),
(271590, 'Grand Theft Auto V', 89.90, 50, 'Action', '2015-04-14', 88),
(1172470, 'Apex Legends', 0.00, 0, 'Battle Royale', '2020-11-04', 79),
(292030, 'The Witcher 3: Wild Hunt', 149.99, 75, 'RPG', '2015-05-18', 97),
(578080, 'PUBG: BATTLEGROUNDS', 129.99, 60, 'Battle Royale', '2017-12-20', 73),
(367520, 'Hollow Knight', 46.99, 34, 'Metroidvania', '2017-02-24', 97),
(431960, 'Wallpaper Engine', 13.99, 0, 'Software', '2018-02-06', 95),
(105600, 'Terraria', 37.99, 50, 'Sandbox', '2011-05-16', 97);

-- Inserir histórico de preços de exemplo
INSERT IGNORE INTO price_history (steam_id, preco, desconto, data_coleta) VALUES
(271590, 179.80, 0, '2024-01-01'),
(271590, 89.90, 50, '2024-06-15'),
(271590, 134.85, 25, '2024-07-01'),
(271590, 89.90, 50, '2024-08-01'),
(292030, 199.99, 0, '2024-01-01'),
(292030, 149.99, 25, '2024-03-15'),
(292030, 99.99, 50, '2024-06-20'),
(292030, 149.99, 25, '2024-08-15'),
(578080, 129.99, 0, '2024-01-01'),
(578080, 64.99, 50, '2024-04-01'),
(578080, 129.99, 0, '2024-07-01'),
(367520, 46.99, 0, '2024-01-01'),
(367520, 31.04, 34, '2024-05-15'),
(367520, 23.49, 50, '2024-07-20');

-- Inserir previsões de exemplo
INSERT IGNORE INTO predictions (steam_id, preco_atual, preco_previsto, desconto_esperado, score_compra, recomendacao, confianca, data_previsao) VALUES
(271590, 89.90, 67.43, 25, 75, 'Comprar agora', 85, CURDATE()),
(292030, 149.99, 99.99, 33, 80, 'Aguardar promoção', 78, CURDATE()),
(578080, 129.99, 64.99, 50, 65, 'Aguardar promoção', 72, CURDATE()),
(367520, 46.99, 23.49, 50, 85, 'Ótima oportunidade', 92, CURDATE()),
(730, 0.00, 0.00, 0, 95, 'Jogo gratuito', 100, CURDATE());

-- Inserir validações temporais de exemplo
INSERT IGNORE INTO temporal_validations (steam_id, data_previsao, preco_previsto, preco_real, erro_absoluto, erro_percentual) VALUES
(271590, '2024-06-15', 95.00, 89.90, 5.10, 5.37),
(292030, '2024-06-20', 105.00, 99.99, 5.01, 4.77),
(578080, '2024-04-01', 70.00, 64.99, 5.01, 7.16),
(367520, '2024-05-15', 28.00, 31.04, 3.04, 10.86);
"""
