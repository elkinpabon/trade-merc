import json
from datetime import datetime, timezone
from decimal import Decimal
from threading import RLock

from sqlalchemy import select

from .store import Account, Decision, Position, Snapshot, now_ms
from .strategy import POLICY, decimal, floor_step, quote_valid, size_order, spread_pct


class PaperEngine:
    """One writer, atomic ledger, fixed costs; no exchange trading credentials or live path."""
    def __init__(self, store, policy=POLICY):
        self.store, self.policy, self.lock = store, policy, RLock()
        self.last_snapshot = 0

    def enter(self, symbol, decision, quote, rule, at=None):
        at = at or now_ms()
        key = f"{symbol}:{decision['candle_at']}"
        with self.lock, self.store.Session.begin() as s:
            if s.scalar(select(Decision.id).where(Decision.signal_key == key)):
                return 'ALREADY_EVALUATED'
            a = s.get(Account, 1, with_for_update=True)
            positions = s.scalars(select(Position).where(Position.status == 'OPEN')).all()
            equity = a.cash + sum((p.quantity * p.mark for p in positions), Decimal(0))
            today = datetime.fromtimestamp(at / 1000, timezone.utc).date().isoformat()
            if a.day != today:
                a.day, a.day_equity = today, equity
            reason, status, order = '', 'WATCH', None
            if not decision['eligible']:
                reason = ' · '.join(decision['reasons'])
            elif not quote_valid(quote) or at - quote.get('at', 0) > 45_000 or quote.get('at', 0) > at:
                status, reason = 'REJECTED', 'Cotización ausente u obsoleta'
            elif spread_pct(quote) > self.policy.max_spread_pct:
                status, reason = 'REJECTED', 'Spread excede el límite de ejecución'
            elif positions:
                status, reason = 'REJECTED', 'Una posición ya ocupa el capital permitido'
            elif equity <= a.day_equity * (1 - decimal(self.policy.daily_loss_pct) / 100):
                status, reason = 'REJECTED', 'Límite diario de pérdidas'
            elif equity <= a.peak * (1 - decimal(self.policy.max_drawdown_pct) / 100):
                status, reason = 'REJECTED', 'Límite de drawdown; entradas bloqueadas'
            elif s.scalar(select(Position.id).where(Position.symbol == symbol, Position.closed_at > at - self.policy.cooldown_minutes * 60_000)):
                status, reason = 'REJECTED', 'Enfriamiento tras la última operación'
            elif abs(float(quote['ask']) / decision['price'] - 1) > .003:
                status, reason = 'REJECTED', 'Precio se alejó más de 0,30% de la señal'
            else:
                try:
                    order = size_order(a.cash, equity, quote['ask'], decision['stop_pct'], rule, self.policy)
                except ValueError as exc:
                    status, reason = 'REJECTED', str(exc)
            if order:
                stop = order['fill'] * (1 - decimal(decision['stop_pct']) / 100)
                s.add(Position(symbol=symbol, status='OPEN', quantity=order['quantity'], entry=order['fill'],
                               mark=decimal(quote['bid']), stop=stop, initial_stop=stop,
                               target=order['fill'] * (1 + decimal(decision['target_pct']) / 100),
                               high=order['fill'], entry_fee=order['fee'], opened_at=at, signal_key=key))
                a.cash -= order['debit']
                status, reason = 'ENTERED', 'Impulso + consolidación + ruptura confirmados'
            details = {**decision, 'quote_at_execution': quote, 'rule_at_execution': rule}
            s.add(Decision(signal_key=key, symbol=symbol, at=at, score=decision['score'],
                           status=status, reason=reason, details=json.dumps(details, allow_nan=False)))
            return status

    def monitor(self, quotes, rules, at=None):
        at = at or now_ms()
        with self.lock, self.store.Session.begin() as s:
            a = s.get(Account, 1, with_for_update=True)
            positions = s.scalars(select(Position).where(Position.status == 'OPEN')).all()
            fresh = True
            for p in positions:
                q = quotes.get(p.symbol)
                if not q or not quote_valid(q) or at - q.get('at', 0) > 45_000 or q.get('at', 0) > at:
                    fresh = False
                    continue
                bid = decimal(q['bid'])
                p.mark = bid
                p.high = max(p.high, bid)
                initial_risk = p.entry - p.initial_stop
                if bid >= p.entry + initial_risk:
                    p.stop = max(p.stop, p.high - initial_risk)
                reason = ('STOP' if bid <= p.stop else 'TARGET' if bid >= p.target else
                          'TIMEOUT' if at - p.opened_at >= self.policy.max_hold_minutes * 60_000 else None)
                if not reason:
                    continue
                rule = rules.get(p.symbol)
                if not rule:
                    fresh = False
                    continue
                # Keep an unsellable position valued and visible; never fabricate a dust fill.
                qty = floor_step(p.quantity, rule['step'])
                if qty != p.quantity or qty < decimal(rule['min_qty']) or qty * bid < decimal(rule['min_notional']):
                    p.dust = 1
                    continue
                p.dust = 0
                fill = bid * (1 - decimal(self.policy.slippage_pct) / 100)
                fee = p.quantity * fill * decimal(self.policy.fee_pct) / 100
                proceeds = p.quantity * fill - fee
                a.cash += proceeds
                p.exit_price, p.exit_fee = fill, fee
                p.pnl = proceeds - p.quantity * p.entry - p.entry_fee
                p.closed_at, p.exit_reason, p.status = at, reason, 'CLOSED'
            remaining = [p for p in positions if p.status == 'OPEN']
            equity = a.cash + sum((p.quantity * p.mark for p in remaining), Decimal(0))
            today = datetime.fromtimestamp(at / 1000, timezone.utc).date().isoformat()
            if a.day != today and fresh:
                a.day, a.day_equity = today, equity
            a.peak = max(a.peak, equity)
            btc = quotes.get('BTCUSDT')
            benchmark = None
            if btc and quote_valid(btc) and at - btc.get('at', 0) <= 45_000:
                if not a.benchmark_price:
                    a.benchmark_price = decimal(btc['ask']) * (1 + decimal(self.policy.slippage_pct) / 100)
                # Liquidation value of a fractional buy-and-hold reference, after modeled costs.
                f = decimal(self.policy.fee_pct) / 100
                benchmark = a.initial_cash / (a.benchmark_price * (1 + f)) * decimal(btc['bid']) * (1 - decimal(self.policy.slippage_pct) / 100) * (1 - f)
            if fresh and at - self.last_snapshot >= 60_000:
                s.add(Snapshot(at=at, cash=a.cash, equity=equity, benchmark=benchmark,
                               drawdown=(a.peak-equity)/a.peak*100 if a.peak else 0))
                self.last_snapshot = at
            return {'at': at, 'position_quotes_fresh': fresh, 'equity': float(equity),
                    'cash': float(a.cash), 'dust_positions': sum(p.dust for p in remaining)}
