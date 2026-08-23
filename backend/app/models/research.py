from datetime import datetime
import json

from app.extensions import db


class ModelVersion(db.Model):
    __tablename__ = 'model_versions'

    id = db.Column(db.String(64), primary_key=True)
    model_name = db.Column(db.String(100), nullable=False)
    version = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='candidate')
    algorithm = db.Column(db.String(100), nullable=False)
    feature_schema_json = db.Column(db.Text, nullable=False)
    parameters_json = db.Column(db.Text, nullable=False)
    metrics_json = db.Column(db.Text, nullable=True)
    training_window_start = db.Column(db.DateTime, nullable=True)
    training_window_end = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('model_name', 'version', name='uq_model_name_version'),
        db.Index('idx_model_status_created', 'status', 'created_at'),
    )

    def parameters(self):
        return json.loads(self.parameters_json or '{}')


class StrategyEvaluation(db.Model):
    __tablename__ = 'strategy_evaluations'

    id = db.Column(db.String(64), primary_key=True)
    model_version_id = db.Column(db.String(64), db.ForeignKey('model_versions.id'), nullable=False)
    bot_run_id = db.Column(db.String(64), db.ForeignKey('bot_runs.id'), nullable=True)
    signal_id = db.Column(db.String(64), db.ForeignKey('signals.id'), nullable=True)
    symbol = db.Column(db.String(32), nullable=False)
    timeframe = db.Column(db.String(10), nullable=False)
    decision_candle_ts = db.Column(db.BigInteger, nullable=False)
    decision_at = db.Column(db.DateTime, nullable=False)
    side = db.Column(db.String(10), nullable=False, default='LONG')
    action = db.Column(db.String(20), nullable=False)
    entry_price = db.Column(db.Float, nullable=False)
    score = db.Column(db.Float, nullable=True)
    probability = db.Column(db.Float, nullable=True)
    expected_value_pct = db.Column(db.Float, nullable=True)
    features_json = db.Column(db.Text, nullable=False)
    prediction_json = db.Column(db.Text, nullable=True)
    tp_price = db.Column(db.Float, nullable=False)
    sl_price = db.Column(db.Float, nullable=False)
    horizon_candles = db.Column(db.Integer, nullable=False)
    label_status = db.Column(db.String(20), nullable=False, default='PENDING')
    label = db.Column(db.String(20), nullable=True)
    label_candle_ts = db.Column(db.BigInteger, nullable=True)
    label_at = db.Column(db.DateTime, nullable=True)
    time_to_label_candles = db.Column(db.Integer, nullable=True)
    max_favorable_excursion_pct = db.Column(db.Float, nullable=True)
    max_adverse_excursion_pct = db.Column(db.Float, nullable=True)
    realized_return_pct = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('symbol', 'timeframe', 'decision_candle_ts', 'model_version_id', name='uq_evaluation_candle_model'),
        db.Index('idx_evaluation_pending', 'label_status', 'decision_candle_ts'),
        db.Index('idx_evaluation_model_label', 'model_version_id', 'label', 'decision_at'),
    )

    def features(self):
        return json.loads(self.features_json or '{}')


class StrategyRun(db.Model):
    __tablename__ = 'strategy_runs'

    id = db.Column(db.String(64), primary_key=True)
    run_type = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    model_version_id = db.Column(db.String(64), db.ForeignKey('model_versions.id'), nullable=False)
    config_id = db.Column(db.Integer, db.ForeignKey('bot_configs.id'), nullable=True)
    source_bot_run_id = db.Column(db.String(64), db.ForeignKey('bot_runs.id'), nullable=True)
    symbols_json = db.Column(db.Text, nullable=False)
    timeframe = db.Column(db.String(10), nullable=False)
    parameters_json = db.Column(db.Text, nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    finished_at = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.Text, nullable=True)

    __table_args__ = (db.Index('idx_strategy_run_type_status', 'run_type', 'status', 'started_at'),)


class BacktestRun(db.Model):
    __tablename__ = 'backtest_runs'

    run_id = db.Column(db.String(64), db.ForeignKey('strategy_runs.id'), primary_key=True)
    data_start_at = db.Column(db.DateTime, nullable=False)
    data_end_at = db.Column(db.DateTime, nullable=False)
    initial_equity = db.Column(db.Float, nullable=False)
    final_equity = db.Column(db.Float, nullable=True)
    total_return_pct = db.Column(db.Float, nullable=True)
    max_drawdown_pct = db.Column(db.Float, nullable=True)
    profit_factor = db.Column(db.Float, nullable=True)
    total_trades = db.Column(db.Integer, default=0)
    winning_trades = db.Column(db.Integer, default=0)
    losing_trades = db.Column(db.Integer, default=0)
    data_fingerprint = db.Column(db.String(64), nullable=False)
    result_json = db.Column(db.Text, nullable=True)


class BacktestTrade(db.Model):
    __tablename__ = 'backtest_trades'

    id = db.Column(db.String(64), primary_key=True)
    run_id = db.Column(db.String(64), db.ForeignKey('backtest_runs.run_id'), nullable=False)
    symbol = db.Column(db.String(32), nullable=False)
    entry_at = db.Column(db.DateTime, nullable=False)
    exit_at = db.Column(db.DateTime, nullable=False)
    entry_price = db.Column(db.Float, nullable=False)
    exit_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    realized_pnl = db.Column(db.Float, nullable=False)
    total_fee = db.Column(db.Float, nullable=False)
    exit_reason = db.Column(db.String(20), nullable=False)


class RunDailyMetric(db.Model):
    __tablename__ = 'run_daily_metrics'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    run_id = db.Column(db.String(64), db.ForeignKey('strategy_runs.id'), nullable=False)
    metric_date = db.Column(db.Date, nullable=False)
    starting_equity = db.Column(db.Float, nullable=False)
    ending_equity = db.Column(db.Float, nullable=False)
    daily_pnl = db.Column(db.Float, nullable=False)
    daily_return_pct = db.Column(db.Float, nullable=False)
    total_trades = db.Column(db.Integer, default=0)
    winning_trades = db.Column(db.Integer, default=0)
    losing_trades = db.Column(db.Integer, default=0)
    gross_profit = db.Column(db.Float, default=0.0)
    gross_loss = db.Column(db.Float, default=0.0)
    max_drawdown_pct = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (db.UniqueConstraint('run_id', 'metric_date', name='uq_run_daily_metric'),)
