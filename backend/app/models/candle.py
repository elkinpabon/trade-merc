from app.extensions import db
import datetime as dt_module

class Candle(db.Model):
    __tablename__ = 'candles'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    symbol = db.Column(db.String(32), nullable=False)
    timeframe = db.Column(db.String(10), nullable=False)
    timestamp = db.Column(db.BigInteger, nullable=False)
    datetime = db.Column(db.DateTime, nullable=False)
    open = db.Column(db.Float, nullable=False)
    high = db.Column(db.Float, nullable=False)
    low = db.Column(db.Float, nullable=False)
    close = db.Column(db.Float, nullable=False)
    volume = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=dt_module.datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('symbol', 'timeframe', 'timestamp', name='uq_candle'),
        db.Index('idx_symbol_tf_time', 'symbol', 'timeframe', 'timestamp'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "timestamp": int(self.timestamp),
            "datetime": self.datetime.isoformat() if self.datetime else None,
            "open": float(self.open),
            "high": float(self.high),
            "low": float(self.low),
            "close": float(self.close),
            "volume": float(self.volume),
        }
