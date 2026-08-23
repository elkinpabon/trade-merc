-- Schema declaration for TradeMerc - Algorithmic Crypto Paper/Live Trading System
CREATE DATABASE IF NOT EXISTS trademerc_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE trademerc_db;

-- 1. Exchanges
CREATE TABLE IF NOT EXISTS exchanges (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    supports_paper BOOLEAN DEFAULT TRUE,
    supports_live BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 2. Exchange Settings
CREATE TABLE IF NOT EXISTS exchange_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    exchange_id VARCHAR(64) NOT NULL,
    mode VARCHAR(20) DEFAULT 'paper', -- 'paper' or 'live'
    testnet BOOLEAN DEFAULT FALSE,
    rate_limit_ms INT DEFAULT 200,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (exchange_id) REFERENCES exchanges(id) ON DELETE CASCADE
);

-- 3. Exchange Credentials (Encrypted for future Live Mode)
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

-- 4. Bot Configs
CREATE TABLE IF NOT EXISTS bot_configs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL DEFAULT 'Default EMA Strategy Bot',
    exchange_id VARCHAR(64) DEFAULT 'binance',
    mode VARCHAR(20) DEFAULT 'paper', -- 'paper' or 'live'
    symbols TEXT NULL,
    timeframe VARCHAR(10) DEFAULT '5m',
    virtual_balance DECIMAL(18, 8) DEFAULT 1000.00,
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
    polling_interval_seconds INT DEFAULT 5,
    is_active BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 5. Bot Runs
CREATE TABLE IF NOT EXISTS bot_runs (
    id VARCHAR(64) PRIMARY KEY,
    config_id INT NOT NULL,
    status VARCHAR(20) DEFAULT 'stopped', -- 'running', 'stopped', 'error', 'paused'
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    stopped_at DATETIME NULL,
    last_heartbeat DATETIME NULL,
    error_message TEXT NULL,
    FOREIGN KEY (config_id) REFERENCES bot_configs(id) ON DELETE CASCADE
);

-- 6. Symbols
CREATE TABLE IF NOT EXISTS symbols (
    id VARCHAR(32) PRIMARY KEY, -- e.g. BTC/USDT
    base VARCHAR(16) NOT NULL,
    quote VARCHAR(16) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 7. Symbol Rules
CREATE TABLE IF NOT EXISTS symbol_rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(32) NOT NULL,
    min_notional DECIMAL(18, 8) DEFAULT 10.0,
    min_qty DECIMAL(18, 8) DEFAULT 0.0001,
    qty_precision INT DEFAULT 6,
    price_precision INT DEFAULT 2,
    tick_size DECIMAL(18, 8) DEFAULT 0.01,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_symbol_rule (symbol)
);

-- 8. Candles
CREATE TABLE IF NOT EXISTS candles (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(32) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp BIGINT NOT NULL, -- Epoch milliseconds
    datetime DATETIME NOT NULL,
    open DECIMAL(18, 8) NOT NULL,
    high DECIMAL(18, 8) NOT NULL,
    low DECIMAL(18, 8) NOT NULL,
    close DECIMAL(18, 8) NOT NULL,
    volume DECIMAL(24, 8) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_candle (symbol, timeframe, timestamp),
    INDEX idx_symbol_tf_time (symbol, timeframe, timestamp)
);

-- 9. Signals
CREATE TABLE IF NOT EXISTS signals (
    id VARCHAR(64) PRIMARY KEY,
    bot_run_id VARCHAR(64) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    type VARCHAR(10) NOT NULL, -- 'BUY' or 'SELL'
    action VARCHAR(20) NOT NULL, -- 'ENTER_LONG', 'EXIT_LONG', etc.
    price DECIMAL(18, 8) NOT NULL,
    reason TEXT NULL,
    indicators_json JSON NULL,
    status VARCHAR(20) DEFAULT 'PENDING', -- 'PENDING', 'EXECUTED', 'REJECTED'
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_signal_symbol (symbol),
    INDEX idx_signal_status (status)
);

-- 10. Paper Orders
CREATE TABLE IF NOT EXISTS paper_orders (
    id VARCHAR(64) PRIMARY KEY,
    signal_id VARCHAR(64) NULL,
    symbol VARCHAR(32) NOT NULL,
    side VARCHAR(10) NOT NULL, -- 'BUY' or 'SELL'
    type VARCHAR(10) NOT NULL, -- 'MARKET', 'LIMIT'
    quantity DECIMAL(18, 8) NOT NULL,
    requested_price DECIMAL(18, 8) NOT NULL,
    status VARCHAR(20) DEFAULT 'FILLED', -- 'NEW', 'FILLED', 'CANCELLED', 'REJECTED'
    simulated_fee DECIMAL(18, 8) DEFAULT 0.0,
    simulated_slippage DECIMAL(18, 8) DEFAULT 0.0,
    rejection_reason TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_order_symbol (symbol)
);

-- 11. Paper Fills
CREATE TABLE IF NOT EXISTS paper_fills (
    id VARCHAR(64) PRIMARY KEY,
    order_id VARCHAR(64) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    side VARCHAR(10) NOT NULL,
    fill_price DECIMAL(18, 8) NOT NULL,
    fill_quantity DECIMAL(18, 8) NOT NULL,
    fee_amount DECIMAL(18, 8) NOT NULL,
    fee_currency VARCHAR(16) NOT NULL DEFAULT 'USDT',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES paper_orders(id) ON DELETE CASCADE
);

-- 12. Paper Positions
CREATE TABLE IF NOT EXISTS paper_positions (
    id VARCHAR(64) PRIMARY KEY,
    symbol VARCHAR(32) NOT NULL UNIQUE,
    side VARCHAR(10) NOT NULL DEFAULT 'LONG',
    quantity DECIMAL(18, 8) NOT NULL DEFAULT 0.0,
    entry_price DECIMAL(18, 8) NOT NULL DEFAULT 0.0,
    current_price DECIMAL(18, 8) NOT NULL DEFAULT 0.0,
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

-- 13. Trades
CREATE TABLE IF NOT EXISTS trades (
    id VARCHAR(64) PRIMARY KEY,
    symbol VARCHAR(32) NOT NULL,
    side VARCHAR(10) NOT NULL DEFAULT 'LONG',
    entry_order_id VARCHAR(64) NULL,
    exit_order_id VARCHAR(64) NULL,
    entry_price DECIMAL(18, 8) NOT NULL,
    exit_price DECIMAL(18, 8) NOT NULL,
    quantity DECIMAL(18, 8) NOT NULL,
    realized_pnl DECIMAL(18, 8) NOT NULL,
    realized_pnl_pct DECIMAL(10, 4) NOT NULL,
    total_fee DECIMAL(18, 8) DEFAULT 0.0,
    exit_reason VARCHAR(50) DEFAULT 'SIGNAL', -- 'SIGNAL', 'STOP_LOSS', 'TAKE_PROFIT', 'MANUAL'
    opened_at DATETIME NOT NULL,
    closed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_trade_symbol (symbol)
);

-- 14. Portfolio Snapshots
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cash_balance DECIMAL(18, 8) NOT NULL,
    positions_value DECIMAL(18, 8) NOT NULL,
    total_equity DECIMAL(18, 8) NOT NULL,
    realized_pnl DECIMAL(18, 8) NOT NULL,
    unrealized_pnl DECIMAL(18, 8) NOT NULL,
    peak_equity DECIMAL(18, 8) NOT NULL,
    drawdown_pct DECIMAL(10, 4) NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_portfolio_time (timestamp)
);

-- 15. Daily Metrics
CREATE TABLE IF NOT EXISTS daily_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE UNIQUE NOT NULL,
    starting_balance DECIMAL(18, 8) NOT NULL,
    ending_equity DECIMAL(18, 8) NOT NULL,
    daily_pnl DECIMAL(18, 8) NOT NULL,
    daily_return_pct DECIMAL(10, 4) NOT NULL,
    total_trades INT DEFAULT 0,
    winning_trades INT DEFAULT 0,
    losing_trades INT DEFAULT 0,
    max_drawdown_pct DECIMAL(10, 4) DEFAULT 0.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 16. Strategy Metrics
CREATE TABLE IF NOT EXISTS strategy_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    total_trades INT DEFAULT 0,
    win_rate DECIMAL(10, 4) DEFAULT 0.0,
    profit_factor DECIMAL(10, 4) DEFAULT 0.0,
    total_pnl DECIMAL(18, 8) DEFAULT 0.0,
    max_drawdown_pct DECIMAL(10, 4) DEFAULT 0.0,
    sharpe_ratio DECIMAL(10, 4) DEFAULT 0.0,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 17. Risk Events
CREATE TABLE IF NOT EXISTS risk_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL, -- 'STOP_LOSS_TRIGGERED', 'CIRCUIT_BREAKER', 'MAX_DRAWDOWN_EXCEEDED', 'REJECTED_SIGNAL'
    symbol VARCHAR(32) NULL,
    message TEXT NOT NULL,
    details_json JSON NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 18. Bot Logs
CREATE TABLE IF NOT EXISTS bot_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    level VARCHAR(10) NOT NULL DEFAULT 'INFO', -- 'DEBUG', 'INFO', 'WARNING', 'ERROR'
    module VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_log_level (level),
    INDEX idx_log_time (timestamp)
);

-- 19. System Health
CREATE TABLE IF NOT EXISTS system_health (
    id INT AUTO_INCREMENT PRIMARY KEY,
    component VARCHAR(50) NOT NULL UNIQUE, -- 'database', 'ccxt_feed', 'bot_worker', 'socket_server'
    status VARCHAR(20) NOT NULL, -- 'HEALTHY', 'DEGRADED', 'DOWN'
    details TEXT NULL,
    last_check DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Seed initial default config if empty
INSERT INTO exchanges (id, name, is_active, supports_paper, supports_live) 
VALUES ('binance', 'Binance Exchange', TRUE, TRUE, TRUE)
ON DUPLICATE KEY UPDATE name=name;

INSERT INTO bot_configs (id, name, exchange_id, mode, symbols, timeframe, virtual_balance, is_active)
VALUES (1, 'EMA Crossover & Risk Control Bot', 'binance', 'paper', 'BTC/USDT,ETH/USDT', '5m', 1000.00, FALSE)
ON DUPLICATE KEY UPDATE name=name;

INSERT INTO exchange_credentials (exchange_name, is_active, testnet_flag)
VALUES ('binance', FALSE, TRUE)
ON DUPLICATE KEY UPDATE exchange_name=exchange_name;
