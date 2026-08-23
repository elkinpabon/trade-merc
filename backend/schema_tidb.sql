-- ==============================================================================
-- TRADEMERC - TiDB Cloud Serverless (MySQL 8.0 Compatible) Full Schema
-- Database: trademerc_db
-- Initial Balance: $100.00 USD | Admin User: elkinpabon | PIN: 2002123
-- ==============================================================================

CREATE DATABASE IF NOT EXISTS trademerc_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE trademerc_db;

-- 1. Users Table (Auth Module)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    pin_hash VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_username (username)
);

-- Pre-populate Admin User: elkinpabon with hashed PIN: 2002123
INSERT INTO users (id, username, pin_hash, created_at)
VALUES (
    1,
    'elkinpabon',
    'pbkdf2:sha256:600000$h6C2X4mZ9kL8$8d45ef537d1cf6a1b2496a848c8b671a5330e7ef02e48227b689a71a06780bb2',
    NOW()
) ON DUPLICATE KEY UPDATE username = 'elkinpabon';

-- 2. Exchanges Table
CREATE TABLE IF NOT EXISTS exchanges (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    supports_paper BOOLEAN DEFAULT TRUE,
    supports_live BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

INSERT INTO exchanges (id, name, is_active, supports_paper, supports_live)
VALUES ('binance', 'Binance', TRUE, TRUE, TRUE)
ON DUPLICATE KEY UPDATE name = 'Binance';

-- 3. Exchange Settings Table
CREATE TABLE IF NOT EXISTS exchange_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    exchange_id VARCHAR(64) NOT NULL,
    mode VARCHAR(20) DEFAULT 'paper',
    testnet BOOLEAN DEFAULT FALSE,
    rate_limit_ms INT DEFAULT 200,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (exchange_id) REFERENCES exchanges(id) ON DELETE CASCADE
);

INSERT INTO exchange_settings (id, exchange_id, mode, testnet, rate_limit_ms)
VALUES (1, 'binance', 'paper', FALSE, 200)
ON DUPLICATE KEY UPDATE mode = 'paper';

-- 4. Exchange Credentials Table (Encrypted)
CREATE TABLE IF NOT EXISTS exchange_credentials (
    id INT AUTO_INCREMENT PRIMARY KEY,
    exchange_name VARCHAR(64) NOT NULL,
    api_key_encrypted TEXT NULL,
    api_secret_encrypted TEXT NULL,
    passphrase_encrypted TEXT NULL,
    testnet_flag BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 5. Bot Configs Table
CREATE TABLE IF NOT EXISTS bot_configs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL DEFAULT 'TRADEMERC Multi-Market Bot',
    exchange_id VARCHAR(64) DEFAULT 'binance',
    mode VARCHAR(20) DEFAULT 'paper',
    symbols TEXT NULL,
    timeframe VARCHAR(10) DEFAULT '5m',
    virtual_balance DECIMAL(18, 8) DEFAULT 100.00,
    ema_fast_period INT DEFAULT 9,
    ema_slow_period INT DEFAULT 21,
    rsi_period INT DEFAULT 14,
    rsi_entry_threshold DECIMAL(10, 4) DEFAULT 50.0,
    stop_loss_pct DECIMAL(10, 4) DEFAULT 2.0,
    take_profit_pct DECIMAL(10, 4) DEFAULT 4.0,
    risk_per_trade_pct DECIMAL(10, 4) DEFAULT 2.0,
    slippage_pct DECIMAL(10, 4) DEFAULT 0.05,
    fee_pct DECIMAL(10, 4) DEFAULT 0.10,
    cooldown_seconds INT DEFAULT 60,
    candle_limit INT DEFAULT 100,
    polling_interval_seconds INT DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

INSERT INTO bot_configs (
    id, name, exchange_id, mode, symbols, timeframe, virtual_balance,
    ema_fast_period, ema_slow_period, rsi_period, stop_loss_pct, take_profit_pct,
    polling_interval_seconds, is_active
) VALUES (
    1, 'TRADEMERC Multi-Market Bot', 'binance', 'paper',
    'BTC/USDT,ETH/USDT,SOL/USDT,BNB/USDT,XRP/USDT,ADA/USDT,DOGE/USDT,AVAX/USDT,LINK/USDT,DOT/USDT,MATIC/USDT,NEAR/USDT,SHIB/USDT,LTC/USDT,UNI/USDT,ATOM/USDT,ETC/USDT,BCH/USDT,APT/USDT,SUI/USDT,FET/USDT,RNDR/USDT,INJ/USDT,TIA/USDT,OP/USDT,ARB/USDT,STX/USDT,FTM/USDT,FIL/USDT,ICP/USDT,PEPE/USDT,WIF/USDT,FLOKI/USDT,BONK/USDT,AAVE/USDT,GRT/USDT,THETA/USDT,RUNE/USDT,LDO/USDT,ALGO/USDT,EGLD/USDT,FLOW/USDT,CHZ/USDT,EOS/USDT,QNT/USDT,GALA/USDT,SAND/USDT,MANA/USDT,AXS/USDT,KSM/USDT',
    '5m', 100.00, 9, 21, 14, 2.0, 4.0, 1, TRUE
) ON DUPLICATE KEY UPDATE virtual_balance = 100.00;

-- 6. Bot Runs Table
CREATE TABLE IF NOT EXISTS bot_runs (
    id VARCHAR(64) PRIMARY KEY,
    config_id INT NOT NULL,
    status VARCHAR(20) DEFAULT 'running',
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    stopped_at DATETIME NULL,
    last_heartbeat DATETIME NULL,
    error_message TEXT NULL,
    FOREIGN KEY (config_id) REFERENCES bot_configs(id) ON DELETE CASCADE
);

-- 7. Symbols & Symbol Rules Tables
CREATE TABLE IF NOT EXISTS symbols (
    id VARCHAR(32) PRIMARY KEY,
    base VARCHAR(16) NOT NULL,
    quote VARCHAR(16) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS symbol_rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(32) NOT NULL UNIQUE,
    min_notional DECIMAL(18, 8) DEFAULT 10.0,
    min_qty DECIMAL(18, 8) DEFAULT 0.0001,
    qty_precision INT DEFAULT 6,
    price_precision INT DEFAULT 2,
    tick_size DECIMAL(18, 8) DEFAULT 0.01,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 8. Candles Table
CREATE TABLE IF NOT EXISTS candles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(32) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp BIGINT NOT NULL,
    datetime DATETIME NOT NULL,
    open DECIMAL(18, 8) NOT NULL,
    high DECIMAL(18, 8) NOT NULL,
    low DECIMAL(18, 8) NOT NULL,
    close DECIMAL(18, 8) NOT NULL,
    volume DECIMAL(18, 8) NOT NULL,
    UNIQUE KEY uq_candle (symbol, timeframe, timestamp),
    INDEX idx_symbol_tf (symbol, timeframe)
);

-- 9. Signals Table
CREATE TABLE IF NOT EXISTS signals (
    id VARCHAR(64) PRIMARY KEY,
    bot_run_id VARCHAR(64) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    type VARCHAR(10) NOT NULL,
    action VARCHAR(20) NOT NULL,
    price DECIMAL(18, 8) NOT NULL,
    reason TEXT NULL,
    status VARCHAR(20) DEFAULT 'PENDING',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bot_run_id) REFERENCES bot_runs(id) ON DELETE CASCADE
);

-- 10. Paper Orders Table
CREATE TABLE IF NOT EXISTS paper_orders (
    id VARCHAR(64) PRIMARY KEY,
    signal_id VARCHAR(64) NULL,
    symbol VARCHAR(32) NOT NULL,
    side VARCHAR(10) NOT NULL,
    type VARCHAR(20) DEFAULT 'MARKET',
    quantity DECIMAL(18, 8) NOT NULL,
    requested_price DECIMAL(18, 8) NOT NULL,
    status VARCHAR(20) DEFAULT 'FILLED',
    simulated_fee DECIMAL(18, 8) DEFAULT 0.0,
    simulated_slippage DECIMAL(18, 8) DEFAULT 0.0,
    rejection_reason TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (signal_id) REFERENCES signals(id) ON DELETE SET NULL
);

-- 11. Paper Fills Table
CREATE TABLE IF NOT EXISTS paper_fills (
    id VARCHAR(64) PRIMARY KEY,
    order_id VARCHAR(64) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    side VARCHAR(10) NOT NULL,
    fill_price DECIMAL(18, 8) NOT NULL,
    fill_quantity DECIMAL(18, 8) NOT NULL,
    fee_amount DECIMAL(18, 8) DEFAULT 0.0,
    fee_currency VARCHAR(16) DEFAULT 'USDT',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES paper_orders(id) ON DELETE CASCADE
);

-- 12. Paper Positions Table
CREATE TABLE IF NOT EXISTS paper_positions (
    id VARCHAR(64) PRIMARY KEY,
    symbol VARCHAR(32) NOT NULL,
    side VARCHAR(10) DEFAULT 'LONG',
    quantity DECIMAL(18, 8) NOT NULL,
    entry_price DECIMAL(18, 8) NOT NULL,
    current_price DECIMAL(18, 8) NOT NULL,
    unrealized_pnl DECIMAL(18, 8) DEFAULT 0.0,
    unrealized_pnl_pct DECIMAL(10, 4) DEFAULT 0.0,
    stop_loss_price DECIMAL(18, 8) NULL,
    take_profit_price DECIMAL(18, 8) NULL,
    entry_order_id VARCHAR(64) NULL,
    entry_fee_amount DECIMAL(18, 8) NOT NULL DEFAULT 0,
    is_open BOOLEAN DEFAULT TRUE,
    opened_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 13. Closed Trades Table
CREATE TABLE IF NOT EXISTS trades (
    id VARCHAR(64) PRIMARY KEY,
    symbol VARCHAR(32) NOT NULL,
    side VARCHAR(10) DEFAULT 'LONG',
    entry_order_id VARCHAR(64) NULL,
    exit_order_id VARCHAR(64) NULL,
    entry_price DECIMAL(18, 8) NOT NULL,
    exit_price DECIMAL(18, 8) NOT NULL,
    quantity DECIMAL(18, 8) NOT NULL,
    realized_pnl DECIMAL(18, 8) NOT NULL,
    realized_pnl_pct DECIMAL(10, 4) NOT NULL,
    total_fee DECIMAL(18, 8) DEFAULT 0.0,
    exit_reason VARCHAR(50) DEFAULT 'SIGNAL',
    opened_at DATETIME NOT NULL,
    closed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 14. Portfolio Snapshots Table ($100.00 USD Initial Balance)
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cash_balance DECIMAL(18, 8) NOT NULL,
    positions_value DECIMAL(18, 8) NOT NULL,
    total_equity DECIMAL(18, 8) NOT NULL,
    realized_pnl DECIMAL(18, 8) DEFAULT 0.0,
    unrealized_pnl DECIMAL(18, 8) DEFAULT 0.0,
    peak_equity DECIMAL(18, 8) NOT NULL,
    drawdown_pct DECIMAL(10, 4) DEFAULT 0.0,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Initial Snapshot of $100.00 USD
INSERT INTO portfolio_snapshots (
    id, cash_balance, positions_value, total_equity, realized_pnl, unrealized_pnl, peak_equity, drawdown_pct, timestamp
) VALUES (
    1, 100.00, 0.00, 100.00, 0.00, 0.00, 100.00, 0.00, NOW()
) ON DUPLICATE KEY UPDATE cash_balance = 100.00, total_equity = 100.00;

-- 15. Daily Metrics & Strategy Metrics
CREATE TABLE IF NOT EXISTS daily_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    starting_equity DECIMAL(18, 8) NOT NULL,
    ending_equity DECIMAL(18, 8) NOT NULL,
    daily_pnl DECIMAL(18, 8) NOT NULL,
    daily_pnl_pct DECIMAL(10, 4) NOT NULL,
    total_trades INT DEFAULT 0,
    winning_trades INT DEFAULT 0,
    losing_trades INT DEFAULT 0,
    max_drawdown_pct DECIMAL(10, 4) DEFAULT 0.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS strategy_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    strategy_name VARCHAR(100) NOT NULL,
    total_signals INT DEFAULT 0,
    executed_signals INT DEFAULT 0,
    win_rate DECIMAL(10, 4) DEFAULT 0.0,
    profit_factor DECIMAL(10, 4) DEFAULT 0.0,
    sharpe_ratio DECIMAL(10, 4) DEFAULT 0.0,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 16. Logs & Health Tables
CREATE TABLE IF NOT EXISTS risk_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    symbol VARCHAR(32) NULL,
    message TEXT NOT NULL,
    details JSON NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bot_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    level VARCHAR(10) NOT NULL,
    module VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    details JSON NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS system_health (
    id INT AUTO_INCREMENT PRIMARY KEY,
    component VARCHAR(50) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL,
    details TEXT NULL,
    last_check DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ==============================================================================
-- END OF TIDB CLOUD SCHEMA
-- ==============================================================================
