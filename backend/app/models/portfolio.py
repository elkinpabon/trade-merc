from app.extensions import db
from datetime import datetime

class PortfolioSnapshot(db.Model):
    __tablename__ = 'portfolio_snapshots'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    strategy_run_id = db.Column(db.String(64), db.ForeignKey('strategy_runs.id'), nullable=True, index=True)
    model_version_id = db.Column(db.String(64), db.ForeignKey('model_versions.id'), nullable=True)
    config_id = db.Column(db.Integer, db.ForeignKey('bot_configs.id'), nullable=True)
    cash_balance = db.Column(db.Float, nullable=False)
    positions_value = db.Column(db.Float, nullable=False)
    total_equity = db.Column(db.Float, nullable=False)
    realized_pnl = db.Column(db.Float, nullable=False)
    unrealized_pnl = db.Column(db.Float, nullable=False)
    peak_equity = db.Column(db.Float, nullable=False)
    drawdown_pct = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "strategy_run_id": self.strategy_run_id,
            "model_version_id": self.model_version_id,
            "config_id": self.config_id,
            "cash_balance": float(self.cash_balance),
            "positions_value": float(self.positions_value),
            "total_equity": float(self.total_equity),
            "realized_pnl": float(self.realized_pnl),
            "unrealized_pnl": float(self.unrealized_pnl),
            "peak_equity": float(self.peak_equity),
            "drawdown_pct": float(self.drawdown_pct),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
