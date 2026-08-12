from app.extensions import db
from datetime import datetime

class DailyMetric(db.Model):
    __tablename__ = 'daily_metrics'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.Date, unique=True, nullable=False)
    starting_balance = db.Column(db.Float, nullable=False)
    ending_equity = db.Column(db.Float, nullable=False)
    daily_pnl = db.Column(db.Float, nullable=False)
    daily_return_pct = db.Column(db.Float, nullable=False)
    total_trades = db.Column(db.Integer, default=0)
    winning_trades = db.Column(db.Integer, default=0)
    losing_trades = db.Column(db.Integer, default=0)
    max_drawdown_pct = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date.isoformat() if self.date else None,
            "starting_balance": float(self.starting_balance),
            "ending_equity": float(self.ending_equity),
            "daily_pnl": float(self.daily_pnl),
            "daily_return_pct": float(self.daily_return_pct),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "max_drawdown_pct": float(self.max_drawdown_pct),
        }

class StrategyMetric(db.Model):
    __tablename__ = 'strategy_metrics'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    total_trades = db.Column(db.Integer, default=0)
    win_rate = db.Column(db.Float, default=0.0)
    profit_factor = db.Column(db.Float, default=0.0)
    total_pnl = db.Column(db.Float, default=0.0)
    max_drawdown_pct = db.Column(db.Float, default=0.0)
    sharpe_ratio = db.Column(db.Float, default=0.0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "total_trades": self.total_trades,
            "win_rate": float(self.win_rate),
            "profit_factor": float(self.profit_factor),
            "total_pnl": float(self.total_pnl),
            "max_drawdown_pct": float(self.max_drawdown_pct),
            "sharpe_ratio": float(self.sharpe_ratio),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
