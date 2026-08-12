from app.extensions import db
from datetime import datetime

class Exchange(db.Model):
    __tablename__ = 'exchanges'

    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    supports_paper = db.Column(db.Boolean, default=True)
    supports_live = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "is_active": self.is_active,
            "supports_paper": self.supports_paper,
            "supports_live": self.supports_live,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class ExchangeSettings(db.Model):
    __tablename__ = 'exchange_settings'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    exchange_id = db.Column(db.String(64), db.ForeignKey('exchanges.id'), nullable=False)
    mode = db.Column(db.String(20), default='paper')
    testnet = db.Column(db.Boolean, default=False)
    rate_limit_ms = db.Column(db.Integer, default=200)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "exchange_id": self.exchange_id,
            "mode": self.mode,
            "testnet": self.testnet,
            "rate_limit_ms": self.rate_limit_ms,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class ExchangeCredentials(db.Model):
    __tablename__ = 'exchange_credentials'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    exchange_name = db.Column(db.String(64), nullable=False)
    api_key_encrypted = db.Column(db.Text, nullable=True)
    api_secret_encrypted = db.Column(db.Text, nullable=True)
    passphrase_encrypted = db.Column(db.Text, nullable=True)
    testnet_flag = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self, include_masked=True):
        return {
            "id": self.id,
            "exchange_name": self.exchange_name,
            "has_api_key": bool(self.api_key_encrypted),
            "has_api_secret": bool(self.api_secret_encrypted),
            "has_passphrase": bool(self.passphrase_encrypted),
            "testnet_flag": self.testnet_flag,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
