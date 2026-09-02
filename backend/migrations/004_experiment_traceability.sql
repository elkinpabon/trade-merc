-- Idempotent TiDB migration for isolated 30-day experiment traceability.
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(64) PRIMARY KEY,
    applied_at DATETIME NOT NULL
);

ALTER TABLE strategy_runs ADD COLUMN IF NOT EXISTS config_snapshot_json TEXT NULL;
ALTER TABLE strategy_runs ADD COLUMN IF NOT EXISTS git_commit VARCHAR(64) NULL;
ALTER TABLE strategy_runs ADD COLUMN IF NOT EXISTS planned_end_at DATETIME NULL;
UPDATE strategy_runs SET config_snapshot_json = '{}' WHERE config_snapshot_json IS NULL;
UPDATE strategy_runs SET git_commit = 'unknown' WHERE git_commit IS NULL;
ALTER TABLE strategy_runs MODIFY COLUMN config_snapshot_json TEXT NOT NULL;
ALTER TABLE strategy_runs MODIFY COLUMN git_commit VARCHAR(64) NOT NULL;

ALTER TABLE paper_orders ADD COLUMN IF NOT EXISTS strategy_run_id VARCHAR(64) NULL;
ALTER TABLE paper_orders ADD COLUMN IF NOT EXISTS model_version_id VARCHAR(64) NULL;
ALTER TABLE paper_orders ADD COLUMN IF NOT EXISTS config_id INT NULL;
CREATE INDEX IF NOT EXISTS idx_paper_order_strategy_run ON paper_orders (strategy_run_id);

ALTER TABLE paper_fills ADD COLUMN IF NOT EXISTS strategy_run_id VARCHAR(64) NULL;
ALTER TABLE paper_fills ADD COLUMN IF NOT EXISTS model_version_id VARCHAR(64) NULL;
ALTER TABLE paper_fills ADD COLUMN IF NOT EXISTS config_id INT NULL;
CREATE INDEX IF NOT EXISTS idx_paper_fill_strategy_run ON paper_fills (strategy_run_id);

ALTER TABLE paper_positions ADD COLUMN IF NOT EXISTS strategy_run_id VARCHAR(64) NULL;
ALTER TABLE paper_positions ADD COLUMN IF NOT EXISTS model_version_id VARCHAR(64) NULL;
ALTER TABLE paper_positions ADD COLUMN IF NOT EXISTS config_id INT NULL;
CREATE INDEX IF NOT EXISTS idx_paper_position_strategy_run ON paper_positions (strategy_run_id);

ALTER TABLE trades ADD COLUMN IF NOT EXISTS strategy_run_id VARCHAR(64) NULL;
ALTER TABLE trades ADD COLUMN IF NOT EXISTS model_version_id VARCHAR(64) NULL;
ALTER TABLE trades ADD COLUMN IF NOT EXISTS config_id INT NULL;
CREATE INDEX IF NOT EXISTS idx_trade_strategy_run ON trades (strategy_run_id);

ALTER TABLE portfolio_snapshots ADD COLUMN IF NOT EXISTS strategy_run_id VARCHAR(64) NULL;
ALTER TABLE portfolio_snapshots ADD COLUMN IF NOT EXISTS model_version_id VARCHAR(64) NULL;
ALTER TABLE portfolio_snapshots ADD COLUMN IF NOT EXISTS config_id INT NULL;
CREATE INDEX IF NOT EXISTS idx_portfolio_snapshot_strategy_run ON portfolio_snapshots (strategy_run_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_paper_order_signal ON paper_orders (signal_id);

CREATE TABLE IF NOT EXISTS worker_cycles (
    id VARCHAR(64) PRIMARY KEY,
    bot_run_id VARCHAR(64) NOT NULL,
    strategy_run_id VARCHAR(64) NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'RUNNING',
    expected_symbols INT NOT NULL DEFAULT 0,
    received_symbols INT NOT NULL DEFAULT 0,
    processed_symbols INT NOT NULL DEFAULT 0,
    started_at DATETIME NOT NULL,
    finished_at DATETIME NULL,
    error_message TEXT NULL,
    KEY idx_worker_cycle_bot_run (bot_run_id, started_at),
    KEY idx_worker_cycle_strategy_run (strategy_run_id, started_at)
);

INSERT IGNORE INTO schema_migrations (version, applied_at)
VALUES ('004_experiment_traceability', UTC_TIMESTAMP());
