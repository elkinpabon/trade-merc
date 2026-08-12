from app.extensions import db
from datetime import datetime

class PortfolioSnapshot(db.Model):
    __tablename__ = 'portfolio_snapshots'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
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
            "cash_balance": float(self.cash_balance),
            "positions_value": float(self.positions_value),
            "total_equity": float(self.total_equity),
            "realized_pnl": float(self.realized_pnl),
            "unrealized_pnl": float(self.unrealized_pnl),
            "peak_equity": float(self.peak_equity),
            "drawdown_pct": float(self.drawdown_pct),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
