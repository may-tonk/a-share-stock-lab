-- 连接配置中的独立数据库由 init-db 命令创建，以下四张表均使用 InnoDB。
CREATE TABLE IF NOT EXISTS stocks (
    symbol VARCHAR(9) PRIMARY KEY,
    code CHAR(6) NOT NULL,
    market VARCHAR(2) NOT NULL,
    name VARCHAR(64) NOT NULL,
    tracked BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS daily_quotes (
    symbol VARCHAR(9) NOT NULL,
    trade_date DATE NOT NULL,
    open DECIMAL(16,4) NOT NULL,
    close DECIMAL(16,4) NOT NULL,
    high DECIMAL(16,4) NOT NULL,
    low DECIMAL(16,4) NOT NULL,
    volume BIGINT UNSIGNED NOT NULL COMMENT '手',
    amount DECIMAL(24,2) NOT NULL COMMENT '元',
    amplitude DECIMAL(16,4) NULL COMMENT '百分数，例如1.03表示1.03%',
    change_pct DECIMAL(16,4) NULL,
    change_amount DECIMAL(16,4) NULL,
    turnover DECIMAL(16,4) NULL,
    source VARCHAR(32) NOT NULL DEFAULT 'eastmoney',
    adjustment VARCHAR(8) NOT NULL DEFAULT 'none',
    fetched_at DATETIME(6) NOT NULL COMMENT '北京时间',
    PRIMARY KEY (symbol, trade_date),
    CONSTRAINT fk_quotes_stock FOREIGN KEY (symbol) REFERENCES stocks(symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS sync_state (
    symbol VARCHAR(9) PRIMARY KEY,
    first_trade_date DATE NOT NULL,
    latest_trade_date DATE NOT NULL,
    total_rows INT UNSIGNED NOT NULL,
    last_success_at DATETIME(6) NOT NULL,
    CONSTRAINT fk_state_stock FOREIGN KEY (symbol) REFERENCES stocks(symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS sync_logs (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(9) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(16) NOT NULL,
    fetched_rows INT UNSIGNED NOT NULL DEFAULT 0,
    inserted_rows INT UNSIGNED NOT NULL DEFAULT 0,
    updated_rows INT UNSIGNED NOT NULL DEFAULT 0,
    unchanged_rows INT UNSIGNED NOT NULL DEFAULT 0,
    message VARCHAR(500) NOT NULL DEFAULT '',
    started_at DATETIME(6) NOT NULL,
    finished_at DATETIME(6) NOT NULL,
    INDEX idx_sync_symbol (symbol, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

