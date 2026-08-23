from app.extensions import db
from datetime import datetime

class BotConfig(db.Model):
    __tablename__ = 'bot_configs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), default='Default EMA Strategy Bot')
    exchange_id = db.Column(db.String(64), default='binance')
    mode = db.Column(db.String(20), default='paper')
    symbols = db.Column(db.Text, default='BTC/USDT,ETH/USDT,SOL/USDT,BNB/USDT,XRP/USDT,ADA/USDT,DOGE/USDT,LINK/USDT,AVAX/USDT,LTC/USDT')
    timeframe = db.Column(db.String(10), default='15m')
    virtual_balance = db.Column(db.Float, default=1000.0)
    ema_fast_period = db.Column(db.Integer, default=9)
    ema_slow_period = db.Column(db.Integer, default=21)
    rsi_period = db.Column(db.Integer, default=14)
    rsi_entry_threshold = db.Column(db.Float, default=50.0)
    stop_loss_pct = db.Column(db.Float, default=2.0)
    take_profit_pct = db.Column(db.Float, default=4.0)
    risk_per_trade_pct = db.Column(db.Float, default=0.25)
    slippage_pct = db.Column(db.Float, default=0.05)
    fee_pct = db.Column(db.Float, default=0.10)
    cooldown_seconds = db.Column(db.Integer, default=900)
    candle_limit = db.Column(db.Integer, default=100)
    polling_interval_seconds = db.Column(db.Integer, default=60)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "exchange_id": self.exchange_id,
            "mode": self.mode,
            "symbols": self.symbols.split(",") if self.symbols else [],
            "timeframe": self.timeframe,
            "virtual_balance": float(self.virtual_balance),
            "ema_fast_period": self.ema_fast_period,
            "ema_slow_period": self.ema_slow_period,
            "rsi_period": self.rsi_period,
            "rsi_entry_threshold": float(self.rsi_entry_threshold),
            "stop_loss_pct": float(self.stop_loss_pct),
            "take_profit_pct": float(self.take_profit_pct),
            "risk_per_trade_pct": float(self.risk_per_trade_pct),
            "slippage_pct": float(self.slippage_pct),
            "fee_pct": float(self.fee_pct),
            "cooldown_seconds": self.cooldown_seconds,
            "candle_limit": self.candle_limit,
            "polling_interval_seconds": self.polling_interval_seconds,
            "is_active": self.is_active,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class BotRun(db.Model):
    __tablename__ = 'bot_runs'

    id = db.Column(db.String(64), primary_key=True)
    config_id = db.Column(db.Integer, db.ForeignKey('bot_configs.id'), nullable=False)
    status = db.Column(db.String(20), default='stopped')
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    stopped_at = db.Column(db.DateTime, nullable=True)
    last_heartbeat = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "config_id": self.config_id,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "error_message": self.error_message,
        }
