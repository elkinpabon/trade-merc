-- Apply once to TiDB/MySQL before enabling research jobs.
ALTER TABLE bot_configs ADD COLUMN model_version_id VARCHAR(64) NULL;
ALTER TABLE candles ADD UNIQUE KEY uq_candle (symbol, timeframe, timestamp);

CREATE TABLE model_versions (
    id VARCHAR(64) PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    version VARCHAR(64) NOT NULL,
    status VARCHAR(20) NOT NULL,
    algorithm VARCHAR(100) NOT NULL,
    feature_schema_json TEXT NOT NULL,
    parameters_json TEXT NOT NULL,
    metrics_json TEXT NULL,
    training_window_start DATETIME NULL,
    training_window_end DATETIME NULL,
    created_at DATETIME NOT NULL,
    UNIQUE KEY uq_model_name_version (model_name, version),
    KEY idx_model_status_created (status, created_at)
);

CREATE TABLE strategy_evaluations (
    id VARCHAR(64) PRIMARY KEY,
    model_version_id VARCHAR(64) NOT NULL,
    bot_run_id VARCHAR(64) NULL,
    signal_id VARCHAR(64) NULL,
    symbol VARCHAR(32) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    decision_candle_ts BIGINT NOT NULL,
    decision_at DATETIME NOT NULL,
    side VARCHAR(10) NOT NULL,
    action VARCHAR(20) NOT NULL,
    entry_price DECIMAL(18,8) NOT NULL,
    score DECIMAL(10,4) NULL,
    probability DECIMAL(10,6) NULL,
    expected_value_pct DECIMAL(12,6) NULL,
    features_json TEXT NOT NULL,
    prediction_json TEXT NULL,
    tp_price DECIMAL(18,8) NOT NULL,
    sl_price DECIMAL(18,8) NOT NULL,
    horizon_candles INT NOT NULL,
    label_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    label VARCHAR(20) NULL,
    label_candle_ts BIGINT NULL,
    label_at DATETIME NULL,
    time_to_label_candles INT NULL,
    max_favorable_excursion_pct DECIMAL(12,6) NULL,
    max_adverse_excursion_pct DECIMAL(12,6) NULL,
    realized_return_pct DECIMAL(12,6) NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    UNIQUE KEY uq_evaluation_candle_model (symbol, timeframe, decision_candle_ts, model_version_id),
    KEY idx_evaluation_pending (label_status, decision_candle_ts),
    KEY idx_evaluation_model_label (model_version_id, label, decision_at)
);

CREATE TABLE strategy_runs (
    id VARCHAR(64) PRIMARY KEY,
    run_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    model_version_id VARCHAR(64) NOT NULL,
    config_id INT NULL,
    source_bot_run_id VARCHAR(64) NULL,
    symbols_json TEXT NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    parameters_json TEXT NOT NULL,
    started_at DATETIME NOT NULL,
    finished_at DATETIME NULL,
    error_message TEXT NULL,
    KEY idx_strategy_run_type_status (run_type, status, started_at)
);

CREATE TABLE backtest_runs (
    run_id VARCHAR(64) PRIMARY KEY,
    data_start_at DATETIME NOT NULL,
    data_end_at DATETIME NOT NULL,
    initial_equity DECIMAL(18,8) NOT NULL,
    final_equity DECIMAL(18,8) NULL,
    total_return_pct DECIMAL(12,6) NULL,
    max_drawdown_pct DECIMAL(12,6) NULL,
    profit_factor DECIMAL(12,6) NULL,
    total_trades INT DEFAULT 0,
    winning_trades INT DEFAULT 0,
    losing_trades INT DEFAULT 0,
    data_fingerprint VARCHAR(64) NOT NULL,
    result_json TEXT NULL
);

CREATE TABLE backtest_trades (
    id VARCHAR(64) PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    entry_at DATETIME NOT NULL,
    exit_at DATETIME NOT NULL,
    entry_price DECIMAL(18,8) NOT NULL,
    exit_price DECIMAL(18,8) NOT NULL,
    quantity DECIMAL(18,8) NOT NULL,
    realized_pnl DECIMAL(18,8) NOT NULL,
    total_fee DECIMAL(18,8) NOT NULL,
    exit_reason VARCHAR(20) NOT NULL,
    KEY idx_backtest_trade_run (run_id, entry_at)
);

CREATE TABLE run_daily_metrics (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL,
    metric_date DATE NOT NULL,
    starting_equity DECIMAL(18,8) NOT NULL,
    ending_equity DECIMAL(18,8) NOT NULL,
    daily_pnl DECIMAL(18,8) NOT NULL,
    daily_return_pct DECIMAL(12,6) NOT NULL,
    total_trades INT NOT NULL DEFAULT 0,
    winning_trades INT NOT NULL DEFAULT 0,
    losing_trades INT NOT NULL DEFAULT 0,
    gross_profit DECIMAL(18,8) NOT NULL DEFAULT 0,
    gross_loss DECIMAL(18,8) NOT NULL DEFAULT 0,
    max_drawdown_pct DECIMAL(12,6) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    UNIQUE KEY uq_run_daily_metric (run_id, metric_date)
);
