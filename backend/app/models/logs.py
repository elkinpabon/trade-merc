from app.extensions import db
from datetime import datetime
import json

class RiskEvent(db.Model):
    __tablename__ = 'risk_events'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_type = db.Column(db.String(50), nullable=False)
    symbol = db.Column(db.String(32), nullable=True)
    message = db.Column(db.Text, nullable=False)
    details_json = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        details = {}
        if self.details_json:
            try:
                details = json.loads(self.details_json)
            except Exception:
                details = {}
        return {
            "id": self.id,
            "event_type": self.event_type,
            "symbol": self.symbol,
            "message": self.message,
            "details": details,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

class BotLog(db.Model):
    __tablename__ = 'bot_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    level = db.Column(db.String(10), default='INFO') # DEBUG, INFO, WARNING, ERROR
    module = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "level": self.level,
            "module": self.module,
            "message": self.message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

class SystemHealth(db.Model):
    __tablename__ = 'system_health'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    component = db.Column(db.String(50), nullable=False, unique=True)
    status = db.Column(db.String(20), nullable=False) # HEALTHY, DEGRADED, DOWN
    details = db.Column(db.Text, nullable=True)
    last_check = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "component": self.component,
            "status": self.status,
            "details": self.details,
            "last_check": self.last_check.isoformat() if self.last_check else None,
        }
