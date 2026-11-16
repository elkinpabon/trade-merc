import json
from decimal import Decimal, ROUND_CEILING
from typing import Tuple, Dict, Any, List, Optional
from app.extensions import db
from app.models import BotConfig, PaperPosition, PortfolioSnapshot, RiskEvent, Signal, SymbolRule, PaperOrder, Trade
from app.services.activity_profiles import PILOT_PROFILES, PILOT_LIMITS
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
        if config.strategy_key in PILOT_PROFILES:
            self.max_allowed_drawdown_pct = PILOT_LIMITS['max_drawdown_pct']

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

        rule = SymbolRule.query.filter_by(symbol=symbol).first()
        precision = rule.qty_precision if rule else 6
        sellable = round_qty(position.quantity, precision)
        minimum_qty = rule.min_qty if rule else 0.0001
        minimum_notional = rule.min_notional if rule else 10.0
        if sellable < minimum_qty or sellable * current_price < minimum_notional:
            message = f'Paper residual below exchange minimum: position={position.id}'
            if not RiskEvent.query.filter_by(event_type='PAPER_DUST', symbol=symbol, message=message).first():
                self.log_risk_event('PAPER_DUST', symbol, message, {
                    'position_id': position.id, 'strategy_run_id': position.strategy_run_id,
                    'quantity': float(position.quantity), 'sellable_quantity': sellable,
                    'price': current_price, 'minimum_qty': float(minimum_qty),
                    'minimum_notional': float(minimum_notional),
                    'treatment': 'retained_open_and_valued_no_sale',
                })
            return {'trigger': 'DUST', 'reason': 'POSITION_BELOW_EXCHANGE_MINIMUM',
                    'position': position, 'sellable_quantity': sellable,
                    'minimum_qty': minimum_qty, 'minimum_notional': minimum_notional}

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

        if self.config.strategy_key in PILOT_PROFILES:
            if (utc_now() - position.opened_at).total_seconds() >= PILOT_PROFILES[self.config.strategy_key]['max_hold_minutes'] * 60:
                return {'trigger': 'TIME_EXIT', 'reason': 'PILOT_MAX_HOLD', 'position': position}
            # Recover the original ATR risk from the immutable entry signal; do not
            # recompute R from a stop that has already moved to net break-even.
            entry_order = db.session.get(PaperOrder, position.entry_order_id) if position.entry_order_id else None
            entry_signal = db.session.get(Signal, entry_order.signal_id) if entry_order and entry_order.signal_id else None
            decision = json.loads(entry_signal.indicators_json or '{}').get('opportunity', {}) if entry_signal else {}
            original_risk = position.entry_price * float(decision.get('stop_loss_pct') or 0) / 100
            if original_risk > 0 and current_price >= position.entry_price + original_risk:
                exit_factor = (1-float(self.config.fee_pct)/100) * (1-float(self.config.slippage_pct)/100)
                break_even = (position.entry_price + float(position.entry_fee_amount or 0)/position.quantity) / exit_factor
                precision = rule.price_precision if rule else (6 if current_price < 1 else 4 if current_price < 100 else 2)
                tick = Decimal(str(rule.tick_size)) if rule and rule.tick_size else Decimal(1).scaleb(-precision)
                net_stop = float((Decimal(str(break_even))/tick).to_integral_value(rounding=ROUND_CEILING)*tick)
                if (position.stop_loss_price or 0) < net_stop <= current_price:
                    position.stop_loss_price = net_stop
                    db.session.commit()
                    self.log_risk_event('PILOT_NET_BREAK_EVEN', symbol,
                                        f'Net-cost stop raised for position {position.id}',
                                        {'strategy_run_id': position.strategy_run_id, 'stop': net_stop})
        return None

    def pilot_entry_rejection(self, total_equity):
        if self.config.strategy_key not in PILOT_PROFILES:
            return None
        from app.services.experiment_service import ExperimentService
        run = ExperimentService.active_run(self.config.id)
        if not run:
            return 'No active authorized pilot experiment'
        now = utc_now()
        day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        base_query = PortfolioSnapshot.query.filter_by(strategy_run_id=run.id)
        previous = base_query.filter(PortfolioSnapshot.timestamp < day).order_by(PortfolioSnapshot.id.desc()).first()
        base = previous or base_query.order_by(PortfolioSnapshot.id.asc()).first()
        if base and total_equity <= float(base.total_equity) * (1-PILOT_LIMITS['daily_loss_pct']/100):
            return 'Pilot daily loss limit (1.5%) reached'
        entries = PaperOrder.query.filter_by(strategy_run_id=run.id, side='BUY', status='FILLED').filter(PaperOrder.created_at >= day).count()
        if entries >= PILOT_LIMITS['max_entries_per_day']:
            return 'Pilot daily entry cap (8) reached'
        last_close = Trade.query.filter_by(config_id=self.config.id).order_by(Trade.closed_at.desc()).first()
        if last_close and (now-last_close.closed_at).total_seconds() < self.config.cooldown_seconds:
            return 'Pilot cooldown after exit'
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

        # Exits must remain possible even when the drawdown breaker is active.
        if signal.action == 'EXIT_LONG':
            position = PaperPosition.query.filter_by(symbol=signal.symbol, is_open=True).first()
            return (True, 'APPROVED', position.quantity) if position and position.quantity > 0 else (False, 'No active position to exit', 0.0)

        pilot_rejection = self.pilot_entry_rejection(total_equity)
        if pilot_rejection:
            self.log_risk_event('PILOT_ENTRY_BLOCKED', signal.symbol, pilot_rejection)
            return False, pilot_rejection, 0.0

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
            opportunity = json.loads(signal.indicators_json or '{}').get('opportunity')
            if opportunity:
                sl_pct = float(opportunity['stop_loss_pct']) / 100.0

            if current_price <= 0 or sl_pct <= 0:
                return False, "Invalid market price", 0.0

            # Include estimated round-trip fees and slippage in new-profile risk.
            costs = (2 * (float(self.config.fee_pct) + float(self.config.slippage_pct)) / 100.0
                     if opportunity else 0.0)
            quantity_by_risk = risk_amount / (current_price * (sl_pct + costs))
            max_capital_per_trade = min(cash * 0.95, total_equity * 0.20)
            quantity = min(quantity_by_risk, max_capital_per_trade / current_price)

            rule = SymbolRule.query.filter_by(symbol=signal.symbol).first()
            quantity = round_qty(quantity, rule.qty_precision if rule else 6)
            minimum_notional = float(rule.min_notional) if rule else 10.0
            minimum_qty = float(rule.min_qty) if rule else 0.0001
            if quantity < minimum_qty or quantity * current_price < minimum_notional:
                msg = (f"Order capital allocation (${quantity * current_price:.2f}) or quantity "
                       f"({quantity}) below symbol requirements (${minimum_notional:.2f}, {minimum_qty}).")
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
        try:
            db.session.commit()
        except Exception as error:
            # Audit persistence must never prevent risk controls from rejecting a trade.
            db.session.rollback()
            print(f"Risk event audit skipped: {error}")
