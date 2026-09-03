-- Align the legacy TiDB table with the RiskEvent ORM model.
ALTER TABLE risk_events ADD COLUMN IF NOT EXISTS details_json TEXT NULL;

INSERT IGNORE INTO schema_migrations (version, applied_at)
VALUES ('005_fix_risk_events', UTC_TIMESTAMP());
