-- Apply once to existing TiDB/MySQL databases created before PaperOrder.updated_at existed.
ALTER TABLE paper_orders
    ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;
