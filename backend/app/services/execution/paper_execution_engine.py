from typing import Dict, Any, Optional, List
from datetime import datetime
from app.services.execution.base_execution_engine import BaseExecutionEngine
from app.extensions import db
from app.models import PaperOrder, PaperFill, PaperPosition, Trade, BotConfig, PortfolioSnapshot, SymbolRule
from app.utils.helpers import generate_uuid, round_qty, round_price, utc_now

class PaperExecutionEngine(BaseExecutionEngine):
    """
    Robust Production-Grade Paper Trading Execution Engine.
    Simulates realistic execution including fee deduction, slippage,
    min notional validation, quantity/price precision rounding, and portfolio tracking.
    """

    def __init__(self, config: BotConfig):
        # Extract plain primitive values to prevent SQLAlchemy DetachedInstanceError across sessions
        self.virtual_balance = float(config.virtual_balance) if config else 1000.0
        self.slippage_pct = float(config.slippage_pct) if config else 0.05
        self.fee_pct = float(config.fee_pct) if config else 0.10
        self.stop_loss_pct = float(config.stop_loss_pct) if config else 2.0
        self.take_profit_pct = float(config.take_profit_pct) if config else 4.0

    def estimate_fees(self, notional: float, fee_pct: float) -> float:
        return notional * (fee_pct / 100.0)

    def estimate_slippage(self, requested_price: float, side: str, slippage_pct: float) -> float:
        slippage_factor = slippage_pct / 100.0
        if side.upper() == 'BUY':
            return requested_price * (1.0 + slippage_factor)
        else:
            return requested_price * (1.0 - slippage_factor)

    def validate_symbol_rules(self, symbol: str, quantity: float, price: float) -> tuple[bool, str]:
        rule = SymbolRule.query.filter_by(symbol=symbol).first()
        if not rule:
            min_notional = 10.0
            min_qty = 0.0001
        else:
            min_notional = rule.min_notional
            min_qty = rule.min_qty

        notional = quantity * price
        if notional < min_notional:
            return False, f"Order notional (${notional:.2f}) is below minimum requirement (${min_notional:.2f})"

        if quantity < min_qty:
            return False, f"Order quantity ({quantity}) is below minimum allowed ({min_qty})"

        return True, "OK"

    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, price: float, signal_id: Optional[str] = None) -> Dict[str, Any]:
        side = side.upper()
        order_type = order_type.upper()

        rule = SymbolRule.query.filter_by(symbol=symbol).first()
        qty_prec = rule.qty_precision if rule else 6
        price_prec = rule.price_precision if rule else 2

        quantity = round_qty(quantity, qty_prec)
        price = round_price(price, price_prec)

        valid, msg = self.validate_symbol_rules(symbol, quantity, price)
        if not valid:
            rejected_order = PaperOrder(
                id=generate_uuid(),
                signal_id=signal_id,
                symbol=symbol,
                side=side,
                type=order_type,
                quantity=quantity,
                requested_price=price,
                status='REJECTED',
                rejection_reason=msg,
                created_at=utc_now()
            )
            db.session.add(rejected_order)
            db.session.commit()
            return {"success": False, "error": msg, "order": rejected_order.to_dict()}

        fill_price = round_price(self.estimate_slippage(price, side, self.slippage_pct), price_prec)
        notional = quantity * fill_price
        fee_amount = round_price(self.estimate_fees(notional, self.fee_pct), 4)

        latest_snapshot = PortfolioSnapshot.query.order_by(PortfolioSnapshot.id.desc()).first()
        current_cash = latest_snapshot.cash_balance if latest_snapshot else self.virtual_balance

        if side == 'BUY':
            total_required = notional + fee_amount
            if current_cash < total_required:
                msg = f"Insufficient balance: Required ${total_required:.2f}, Available ${current_cash:.2f}"
                rejected_order = PaperOrder(
                    id=generate_uuid(),
                    signal_id=signal_id,
                    symbol=symbol,
                    side=side,
                    type=order_type,
                    quantity=quantity,
                    requested_price=price,
                    status='REJECTED',
                    rejection_reason=msg,
                    created_at=utc_now()
                )
                db.session.add(rejected_order)
                db.session.commit()
                return {"success": False, "error": msg, "order": rejected_order.to_dict()}

        order_id = generate_uuid()
        fill_id = generate_uuid()

        order = PaperOrder(
            id=order_id,
            signal_id=signal_id,
            symbol=symbol,
            side=side,
            type=order_type,
            quantity=quantity,
            requested_price=price,
            status='FILLED',
            simulated_fee=fee_amount,
            simulated_slippage=abs(fill_price - price),
            created_at=utc_now()
        )
        db.session.add(order)
        db.session.flush()

        fill = PaperFill(
            id=fill_id,
            order_id=order_id,
            symbol=symbol,
            side=side,
            fill_price=fill_price,
            fill_quantity=quantity,
            fee_amount=fee_amount,
            fee_currency='USDT',
            timestamp=utc_now()
        )
        db.session.add(fill)
        db.session.flush()

        position = PaperPosition.query.filter_by(symbol=symbol, is_open=True).first()

        if side == 'BUY':
            new_cash = current_cash - (notional + fee_amount)

            if not position:
                position = PaperPosition(
                    id=generate_uuid(),
                    symbol=symbol,
                    side='LONG',
                    quantity=quantity,
                    entry_price=fill_price,
                    current_price=fill_price,
                    unrealized_pnl=0.0,
                    unrealized_pnl_pct=0.0,
                    stop_loss_price=round_price(fill_price * (1.0 - self.stop_loss_pct / 100.0), price_prec),
                    take_profit_price=round_price(fill_price * (1.0 + self.take_profit_pct / 100.0), price_prec),
                    is_open=True,
                    opened_at=utc_now()
                )
                db.session.add(position)
            else:
                total_qty = position.quantity + quantity
                avg_entry = ((position.quantity * position.entry_price) + notional) / total_qty
                position.quantity = total_qty
                position.entry_price = round_price(avg_entry, price_prec)
                position.current_price = fill_price
                position.stop_loss_price = round_price(avg_entry * (1.0 - self.stop_loss_pct / 100.0), price_prec)
                position.take_profit_price = round_price(avg_entry * (1.0 + self.take_profit_pct / 100.0), price_prec)
                position.updated_at = utc_now()

        elif side == 'SELL':
            if not position:
                db.session.rollback()
                return {"success": False, "error": "No open position to sell."}

            close_qty = min(quantity, position.quantity)
            gross_proceeds = close_qty * fill_price
            new_cash = current_cash + gross_proceeds - fee_amount

            cost_basis = close_qty * position.entry_price
            realized_pnl = (gross_proceeds - fee_amount) - cost_basis
            realized_pnl_pct = (realized_pnl / cost_basis) * 100.0 if cost_basis > 0 else 0.0

            trade = Trade(
                id=generate_uuid(),
                symbol=symbol,
                side='LONG',
                entry_order_id=position.id,
                exit_order_id=order_id,
                entry_price=position.entry_price,
                exit_price=fill_price,
                quantity=close_qty,
                realized_pnl=round_price(realized_pnl, 4),
                realized_pnl_pct=round_price(realized_pnl_pct, 2),
                total_fee=fee_amount,
                exit_reason='SIGNAL',
                opened_at=position.opened_at,
                closed_at=utc_now()
            )
            db.session.add(trade)

            position.quantity -= close_qty
            if position.quantity <= 0.000001:
                position.is_open = False
                position.quantity = 0.0

        open_positions = PaperPosition.query.filter_by(is_open=True).all()
        pos_val = sum(p.quantity * p.current_price for p in open_positions)
        total_equity = new_cash + pos_val

        prev_peak = latest_snapshot.peak_equity if latest_snapshot else total_equity
        peak_equity = max(prev_peak, total_equity)
        drawdown_pct = ((peak_equity - total_equity) / peak_equity * 100.0) if peak_equity > 0 else 0.0

        snapshot = PortfolioSnapshot(
            cash_balance=round_price(new_cash, 2),
            positions_value=round_price(pos_val, 2),
            total_equity=round_price(total_equity, 2),
            realized_pnl=round_price((total_equity - self.virtual_balance), 2),
            unrealized_pnl=round_price(sum(p.unrealized_pnl for p in open_positions), 2),
            peak_equity=round_price(peak_equity, 2),
            drawdown_pct=round_price(drawdown_pct, 2),
            timestamp=utc_now()
        )
        db.session.add(snapshot)
        db.session.commit()

        return {
            "success": True,
            "order": order.to_dict(),
            "fill": fill.to_dict(),
            "position": position.to_dict() if position else None
        }

    def close_position(self, symbol: str, current_price: float, reason: str = 'MANUAL') -> Dict[str, Any]:
        position = PaperPosition.query.filter_by(symbol=symbol, is_open=True).first()
        if not position or position.quantity <= 0:
            return {"success": False, "error": f"No open position found for {symbol}"}

        res = self.place_order(
            symbol=symbol,
            side='SELL',
            order_type='MARKET',
            quantity=position.quantity,
            price=current_price
        )
        if res.get("success") and res.get("order"):
            trade = Trade.query.filter_by(symbol=symbol).order_by(Trade.closed_at.desc()).first()
            if trade:
                trade.exit_reason = reason
                db.session.commit()
        return res

    def cancel_order(self, order_id: str) -> bool:
        order = PaperOrder.query.get(order_id)
        if order and order.status == 'NEW':
            order.status = 'CANCELLED'
            db.session.commit()
            return True
        return False

    def get_balance(self) -> Dict[str, float]:
        latest = PortfolioSnapshot.query.order_by(PortfolioSnapshot.id.desc()).first()
        if latest:
            return {
                "cash_balance": latest.cash_balance,
                "positions_value": latest.positions_value,
                "total_equity": latest.total_equity,
                "unrealized_pnl": latest.unrealized_pnl,
                "realized_pnl": latest.realized_pnl,
                "drawdown_pct": latest.drawdown_pct,
            }
        return {
            "cash_balance": self.virtual_balance,
            "positions_value": 0.0,
            "total_equity": self.virtual_balance,
            "unrealized_pnl": 0.0,
            "realized_pnl": 0.0,
            "drawdown_pct": 0.0,
        }

    def sync_positions(self) -> List[Dict[str, Any]]:
        positions = PaperPosition.query.filter_by(is_open=True).all()
        return [p.to_dict() for p in positions]

    def sync_orders(self) -> List[Dict[str, Any]]:
        orders = PaperOrder.query.order_by(PaperOrder.created_at.desc()).limit(50).all()
        return [o.to_dict() for o in orders]

    def health_check(self) -> Dict[str, Any]:
        return {
            "status": "HEALTHY",
            "mode": "PAPER_TRADING",
            "engine": "PaperExecutionEngine",
            "active_positions": PaperPosition.query.filter_by(is_open=True).count()
        }
