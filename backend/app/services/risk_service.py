import json
from typing import Tuple, Dict, Any, List, Optional
from app.extensions import db
from app.models import BotConfig, PaperPosition, PortfolioSnapshot, RiskEvent, Signal
from app.utils.helpers import utc_now, round_price, round_qty

class RiskService:
    """
    Dedicated Risk Management Engine.
    Enforces position sizing, stop loss, take profit, max drawdown limits, circuit breakers,
    and logs risk audit events.
    """

    def __init__(self, config: BotConfig):
        self.config = config
        self.max_concurrent_positions = 2 # Spot max 2 symbols
        self.max_allowed_drawdown_pct = 15.0 # Circuit breaker limit

    def check_stop_loss_take_profit(self, symbol: str, current_price: float) -> Optional[Dict[str, Any]]:
        """Checks if active position for symbol hit Stop-Loss or Take-Profit."""
        position = PaperPosition.query.filter_by(symbol=symbol, is_open=True).first()
        if not position or position.quantity <= 0:
            return None

        # Update current price and unrealized PnL
        position.current_price = current_price
        entry_val = position.quantity * position.entry_price
        curr_val = position.quantity * current_price
        position.unrealized_pnl = curr_val - entry_val
        position.unrealized_pnl_pct = ((current_price - position.entry_price) / position.entry_price * 100.0) if position.entry_price > 0 else 0.0
        db.session.commit()

        # Stop Loss Trigger
        if position.stop_loss_price and current_price <= position.stop_loss_price:
            self.log_risk_event(
                event_type="STOP_LOSS_TRIGGERED",
                symbol=symbol,
                message=f"Stop Loss triggered for {symbol}: Price ${current_price:.2f} <= SL ${position.stop_loss_price:.2f}",
                details={"current_price": current_price, "sl_price": position.stop_loss_price}
            )
            return {"trigger": "STOP_LOSS", "reason": "STOP_LOSS_TRIGGERED", "position": position}

        # Take Profit Trigger
        if position.take_profit_price and current_price >= position.take_profit_price:
            self.log_risk_event(
                event_type="TAKE_PROFIT_TRIGGERED",
                symbol=symbol,
                message=f"Take Profit triggered for {symbol}: Price ${current_price:.2f} >= TP ${position.take_profit_price:.2f}",
                details={"current_price": current_price, "tp_price": position.take_profit_price}
            )
            return {"trigger": "TAKE_PROFIT", "reason": "TAKE_PROFIT_TRIGGERED", "position": position}

        return None

    def validate_signal_risk(self, signal: Signal, current_price: float) -> tuple[bool, str, float]:
        """
        Validates risk constraints before order execution.
        Calculates position size based on risk_per_trade_pct.
        Returns: (is_allowed, rejection_reason, calculated_quantity)
        """
        latest_snapshot = PortfolioSnapshot.query.order_by(PortfolioSnapshot.id.desc()).first()
        cash = latest_snapshot.cash_balance if latest_snapshot else self.config.virtual_balance
        total_equity = latest_snapshot.total_equity if latest_snapshot else self.config.virtual_balance

        # 1. Circuit Breaker Check
        if latest_snapshot and latest_snapshot.drawdown_pct >= self.max_allowed_drawdown_pct:
            msg = f"Circuit breaker active: Portfolio Drawdown ({latest_snapshot.drawdown_pct:.2f}%) exceeds max limit ({self.max_allowed_drawdown_pct:.2f}%)"
            self.log_risk_event("CIRCUIT_BREAKER", signal.symbol, msg, {"drawdown_pct": latest_snapshot.drawdown_pct})
            return False, msg, 0.0

        # 2. Maximum Open Positions Check
        if signal.action == 'ENTER_LONG':
            open_positions_count = PaperPosition.query.filter_by(is_open=True).count()
            if open_positions_count >= self.max_concurrent_positions:
                msg = f"Risk limit exceeded: Maximum open positions ({self.max_concurrent_positions}) reached."
                self.log_risk_event("MAX_POSITIONS_REACHED", signal.symbol, msg)
                return False, msg, 0.0

            # 3. Position sizing based on the loss at the configured stop.
            risk_amount = total_equity * (self.config.risk_per_trade_pct / 100.0)
            sl_pct = self.config.stop_loss_pct / 100.0

            if current_price <= 0 or sl_pct <= 0:
                return False, "Invalid market price", 0.0

            quantity_by_risk = risk_amount / (current_price * sl_pct)
            max_capital_per_trade = min(cash * 0.95, total_equity * 0.20)
            quantity = min(quantity_by_risk, max_capital_per_trade / current_price)

            if quantity * current_price < 10.0:
                msg = f"Order capital allocation (${quantity * current_price:.2f}) below minimum requirements."
                self.log_risk_event("MIN_CAPITAL_FAIL", signal.symbol, msg)
                return False, msg, 0.0

            return True, "APPROVED", quantity

        elif signal.action == 'EXIT_LONG':
            position = PaperPosition.query.filter_by(symbol=signal.symbol, is_open=True).first()
            if not position or position.quantity <= 0:
                return False, "No active position to exit", 0.0
            return True, "APPROVED", position.quantity

        return False, "Unknown action", 0.0

    def log_risk_event(self, event_type: str, symbol: Optional[str], message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Persists a risk management audit log into database."""
        event = RiskEvent(
            event_type=event_type,
            symbol=symbol,
            message=message,
            details_json=json.dumps(details) if details else None,
            timestamp=utc_now()
        )
        db.session.add(event)
        db.session.commit()
