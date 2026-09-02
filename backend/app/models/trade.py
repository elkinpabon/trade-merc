from app.extensions import db
from datetime import datetime

class Trade(db.Model):
    __tablename__ = 'trades'

    id = db.Column(db.String(64), primary_key=True)
    strategy_run_id = db.Column(db.String(64), db.ForeignKey('strategy_runs.id'), nullable=True, index=True)
    model_version_id = db.Column(db.String(64), db.ForeignKey('model_versions.id'), nullable=True)
    config_id = db.Column(db.Integer, db.ForeignKey('bot_configs.id'), nullable=True)
    symbol = db.Column(db.String(32), nullable=False)
    side = db.Column(db.String(10), default='LONG')
    entry_order_id = db.Column(db.String(64), nullable=True)
    exit_order_id = db.Column(db.String(64), nullable=True)
    entry_price = db.Column(db.Float, nullable=False)
    exit_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    realized_pnl = db.Column(db.Float, nullable=False)
    realized_pnl_pct = db.Column(db.Float, nullable=False)
    total_fee = db.Column(db.Float, default=0.0)
    exit_reason = db.Column(db.String(50), default='SIGNAL') # SIGNAL, STOP_LOSS, TAKE_PROFIT, MANUAL
    opened_at = db.Column(db.DateTime, nullable=False)
    closed_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "strategy_run_id": self.strategy_run_id,
            "model_version_id": self.model_version_id,
            "config_id": self.config_id,
            "symbol": self.symbol,
            "side": self.side,
            "entry_order_id": self.entry_order_id,
            "exit_order_id": self.exit_order_id,
            "entry_price": float(self.entry_price),
            "exit_price": float(self.exit_price),
            "quantity": float(self.quantity),
            "realized_pnl": float(self.realized_pnl),
            "realized_pnl_pct": float(self.realized_pnl_pct),
            "total_fee": float(self.total_fee),
            "exit_reason": self.exit_reason,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        }
