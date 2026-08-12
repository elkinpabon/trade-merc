from app.extensions import db
from datetime import datetime
import json

class Signal(db.Model):
    __tablename__ = 'signals'

    id = db.Column(db.String(64), primary_key=True)
    bot_run_id = db.Column(db.String(64), nullable=False)
    symbol = db.Column(db.String(32), nullable=False)
    type = db.Column(db.String(10), nullable=False) # BUY / SELL
    action = db.Column(db.String(20), nullable=False) # ENTER_LONG / EXIT_LONG
    price = db.Column(db.Float, nullable=False)
    reason = db.Column(db.Text, nullable=True)
    indicators_json = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='PENDING') # PENDING, EXECUTED, REJECTED
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        indicators = {}
        if self.indicators_json:
            try:
                indicators = json.loads(self.indicators_json)
            except Exception:
                indicators = {}
        return {
            "id": self.id,
            "bot_run_id": self.bot_run_id,
            "symbol": self.symbol,
            "type": self.type,
            "action": self.action,
            "price": float(self.price),
            "reason": self.reason,
            "indicators": indicators,
            "status": self.status,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
