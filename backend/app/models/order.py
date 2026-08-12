from app.extensions import db
from datetime import datetime

class PaperOrder(db.Model):
    __tablename__ = 'paper_orders'

    id = db.Column(db.String(64), primary_key=True)
    signal_id = db.Column(db.String(64), nullable=True)
    symbol = db.Column(db.String(32), nullable=False)
    side = db.Column(db.String(10), nullable=False) # BUY / SELL
    type = db.Column(db.String(10), nullable=False) # MARKET / LIMIT
    quantity = db.Column(db.Float, nullable=False)
    requested_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='FILLED') # NEW, FILLED, CANCELLED, REJECTED
    simulated_fee = db.Column(db.Float, default=0.0)
    simulated_slippage = db.Column(db.Float, default=0.0)
    rejection_reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "signal_id": self.signal_id,
            "symbol": self.symbol,
            "side": self.side,
            "type": self.type,
            "quantity": float(self.quantity),
            "requested_price": float(self.requested_price),
            "status": self.status,
            "simulated_fee": float(self.simulated_fee),
            "simulated_slippage": float(self.simulated_slippage),
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class PaperFill(db.Model):
    __tablename__ = 'paper_fills'

    id = db.Column(db.String(64), primary_key=True)
    order_id = db.Column(db.String(64), db.ForeignKey('paper_orders.id'), nullable=False)
    symbol = db.Column(db.String(32), nullable=False)
    side = db.Column(db.String(10), nullable=False)
    fill_price = db.Column(db.Float, nullable=False)
    fill_quantity = db.Column(db.Float, nullable=False)
    fee_amount = db.Column(db.Float, nullable=False)
    fee_currency = db.Column(db.String(16), default='USDT')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "fill_price": float(self.fill_price),
            "fill_quantity": float(self.fill_quantity),
            "fee_amount": float(self.fee_amount),
            "fee_currency": self.fee_currency,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

class PaperPosition(db.Model):
    __tablename__ = 'paper_positions'

    id = db.Column(db.String(64), primary_key=True)
    symbol = db.Column(db.String(32), nullable=False, unique=True)
    side = db.Column(db.String(10), default='LONG')
    quantity = db.Column(db.Float, default=0.0)
    entry_price = db.Column(db.Float, default=0.0)
    current_price = db.Column(db.Float, default=0.0)
    unrealized_pnl = db.Column(db.Float, default=0.0)
    unrealized_pnl_pct = db.Column(db.Float, default=0.0)
    stop_loss_price = db.Column(db.Float, nullable=True)
    take_profit_price = db.Column(db.Float, nullable=True)
    is_open = db.Column(db.Boolean, default=True)
    opened_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": float(self.quantity),
            "entry_price": float(self.entry_price),
            "current_price": float(self.current_price),
            "unrealized_pnl": float(self.unrealized_pnl),
            "unrealized_pnl_pct": float(self.unrealized_pnl_pct),
            "stop_loss_price": float(self.stop_loss_price) if self.stop_loss_price else None,
            "take_profit_price": float(self.take_profit_price) if self.take_profit_price else None,
            "is_open": self.is_open,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
