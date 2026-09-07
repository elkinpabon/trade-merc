CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(64) PRIMARY KEY,
    applied_at DATETIME NOT NULL
);

ALTER TABLE worker_cycles ADD COLUMN IF NOT EXISTS scheduled_at DATETIME NULL;
CREATE INDEX IF NOT EXISTS idx_worker_cycle_scheduled ON worker_cycles (scheduled_at);
CREATE UNIQUE INDEX IF NOT EXISTS uq_worker_cycle_run_slot
    ON worker_cycles (bot_run_id, scheduled_at);

ALTER TABLE candles ADD COLUMN IF NOT EXISTS created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS indicators_json TEXT NULL;

CREATE INDEX IF NOT EXISTS idx_signals_bot_time ON signals (bot_run_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_evaluations_bot_time ON strategy_evaluations (bot_run_id, decision_at);
CREATE INDEX IF NOT EXISTS idx_snapshots_run_time ON portfolio_snapshots (strategy_run_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_trades_run_closed ON trades (strategy_run_id, closed_at);
CREATE INDEX IF NOT EXISTS idx_orders_run_created ON paper_orders (strategy_run_id, created_at);
CREATE INDEX IF NOT EXISTS idx_fills_run_timestamp ON paper_fills (strategy_run_id, timestamp);

UPDATE strategy_runs
SET planned_end_at = DATE_ADD(started_at, INTERVAL 30 DAY)
WHERE run_type = 'EXPERIMENT' AND planned_end_at IS NULL;

UPDATE bot_configs
SET mode = 'paper', timeframe = '15m', virtual_balance = 100.00,
    risk_per_trade_pct = 0.25, stop_loss_pct = 2.0,
    take_profit_pct = 4.0, fee_pct = 0.10, slippage_pct = 0.05,
    cooldown_seconds = 900, polling_interval_seconds = 60
WHERE is_active = TRUE;

INSERT IGNORE INTO schema_migrations (version, applied_at)
VALUES ('006_worker_reliability', UTC_TIMESTAMP());
