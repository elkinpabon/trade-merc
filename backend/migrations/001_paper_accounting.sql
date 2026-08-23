-- Apply once to existing MySQL/TiDB databases before running the updated paper engine.
ALTER TABLE paper_positions
    ADD COLUMN entry_order_id VARCHAR(64) NULL,
    ADD COLUMN entry_fee_amount DECIMAL(18,8) NOT NULL DEFAULT 0;
