-- Setup inicial do banco de dados Pryzor
-- Execute este script no MySQL antes de rodar a aplicação

-- Criar banco de dados (caso não exista)
CREATE DATABASE IF NOT EXISTS steam_pryzor 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- Usar o banco criado
USE steam_pryzor;

-- Tabela de jogos
CREATE TABLE IF NOT EXISTS games (
    appid INT PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    type VARCHAR(50),
    releasedate DATE,
    freetoplay TINYINT(1) DEFAULT 0,
    price_records INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_name (name(100)),
    INDEX idx_type (type),
    INDEX idx_freetoplay (freetoplay)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabela de preços históricos
CREATE TABLE IF NOT EXISTS price_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    appid INT NOT NULL,
    date DATE NOT NULL,
    final_price DECIMAL(10,2),
    initial_price DECIMAL(10,2),
    discount INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (appid) REFERENCES games(appid) ON DELETE CASCADE,
    UNIQUE KEY unique_price (appid, date),
    INDEX idx_appid (appid),
    INDEX idx_date (date),
    INDEX idx_discount (discount)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Verificar se o banco foi criado com sucesso
SELECT 'Banco de dados steam_pryzor criado com sucesso!' AS status;
SELECT COUNT(*) as total_games FROM games;
SELECT COUNT(*) as total_price_records FROM price_history;
