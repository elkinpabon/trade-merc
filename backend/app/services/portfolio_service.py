from app.extensions import db
from app.models import PortfolioSnapshot, PaperPosition, Trade, BotConfig
from app.utils.helpers import round_price, utc_now

class PortfolioService:
    """
    Portfolio Management & Real-time Valuation Engine.
    Tracks virtual balances, unrealized/realized PnL, equity peak, and maximum drawdown.
    """

    def __init__(self, config: BotConfig):
        self.config = config

    def get_summary(self) -> dict:
        latest = PortfolioSnapshot.query.order_by(PortfolioSnapshot.id.desc()).first()
        open_positions = PaperPosition.query.filter_by(is_open=True).all()
        recent_trades = Trade.query.order_by(Trade.closed_at.desc()).limit(10).all()

        total_trades_count = Trade.query.count()
        winning_trades = Trade.query.filter(Trade.realized_pnl > 0).count()
        win_rate = (winning_trades / total_trades_count * 100.0) if total_trades_count > 0 else 0.0

        if not latest:
            return {
                "cash_balance": self.config.virtual_balance,
                "positions_value": 0.0,
                "total_equity": self.config.virtual_balance,
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "peak_equity": self.config.virtual_balance,
                "drawdown_pct": 0.0,
                "total_trades": total_trades_count,
                "win_rate": round_price(win_rate, 2),
                "open_positions_count": len(open_positions),
                "positions": [p.to_dict() for p in open_positions],
                "recent_trades": [t.to_dict() for t in recent_trades]
            }

        return {
            "cash_balance": round_price(latest.cash_balance, 2),
            "positions_value": round_price(latest.positions_value, 2),
            "total_equity": round_price(latest.total_equity, 2),
            "realized_pnl": round_price(latest.realized_pnl, 2),
            "unrealized_pnl": round_price(latest.unrealized_pnl, 2),
            "peak_equity": round_price(latest.peak_equity, 2),
            "drawdown_pct": round_price(latest.drawdown_pct, 2),
            "total_trades": total_trades_count,
            "win_rate": round_price(win_rate, 2),
            "open_positions_count": len(open_positions),
            "positions": [p.to_dict() for p in open_positions],
            "recent_trades": [t.to_dict() for t in recent_trades]
        }

    def update_valuation(self, symbol_prices: dict[str, float]) -> PortfolioSnapshot:
        """Recalculates portfolio equity given current market prices and returns updated snapshot."""
        latest = PortfolioSnapshot.query.order_by(PortfolioSnapshot.id.desc()).first()
        cash = latest.cash_balance if latest else self.config.virtual_balance
        prev_peak = latest.peak_equity if latest else self.config.virtual_balance

        open_positions = PaperPosition.query.filter_by(is_open=True).all()
        pos_val = 0.0
        unrealized = 0.0

        for p in open_positions:
            if p.symbol in symbol_prices:
                p.current_price = symbol_prices[p.symbol]
                entry_val = p.quantity * p.entry_price
                curr_val = p.quantity * p.current_price
                p.unrealized_pnl = curr_val - entry_val
                p.unrealized_pnl_pct = ((p.current_price - p.entry_price) / p.entry_price * 100.0) if p.entry_price > 0 else 0.0

            pos_val += p.quantity * p.current_price
            unrealized += p.unrealized_pnl

        total_equity = cash + pos_val
        realized = total_equity - self.config.virtual_balance
        peak = max(prev_peak, total_equity)
        drawdown = ((peak - total_equity) / peak * 100.0) if peak > 0 else 0.0

        snapshot = PortfolioSnapshot(
            cash_balance=round_price(cash, 2),
            positions_value=round_price(pos_val, 2),
            total_equity=round_price(total_equity, 2),
            realized_pnl=round_price(realized, 2),
            unrealized_pnl=round_price(unrealized, 2),
            peak_equity=round_price(peak, 2),
            drawdown_pct=round_price(drawdown, 2),
            timestamp=utc_now()
        )
        db.session.add(snapshot)
        db.session.commit()
        return snapshot
