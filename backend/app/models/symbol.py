from app.extensions import db
from datetime import datetime

class Symbol(db.Model):
    __tablename__ = 'symbols'

    id = db.Column(db.String(32), primary_key=True)
    base = db.Column(db.String(16), nullable=False)
    quote = db.Column(db.String(16), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "base": self.base,
            "quote": self.quote,
            "is_active": self.is_active,
        }

class SymbolRule(db.Model):
    __tablename__ = 'symbol_rules'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    symbol = db.Column(db.String(32), nullable=False, unique=True)
    min_notional = db.Column(db.Float, default=10.0)
    min_qty = db.Column(db.Float, default=0.0001)
    qty_precision = db.Column(db.Integer, default=6)
    price_precision = db.Column(db.Integer, default=2)
    tick_size = db.Column(db.Float, default=0.01)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "symbol": self.symbol,
            "min_notional": float(self.min_notional),
            "min_qty": float(self.min_qty),
            "qty_precision": self.qty_precision,
            "price_precision": self.price_precision,
            "tick_size": float(self.tick_size),
        }
