"""Additional admission protection; never stops liquidation of an open position."""
from decimal import Decimal

from sqlalchemy import select

from .store import Position

REVISION = 'net-cost-and-loss-guard-v1'
WINDOW = 30
MIN_CLOSED = 20


def entry_guard(session):
    closed = session.scalars(select(Position).where(Position.status == 'CLOSED')
                             .order_by(Position.closed_at.desc(), Position.id.desc()).limit(WINDOW)).all()
    pnl = [Decimal(p.pnl) for p in closed if p.pnl is not None]
    profit = sum((p for p in pnl if p > 0), Decimal(0))
    loss = -sum((p for p in pnl if p < 0), Decimal(0))
    net = sum(pnl, Decimal(0))
    blocked = len(pnl) >= MIN_CLOSED and net < 0 and loss > profit
    return {'revision': REVISION, 'blocked': blocked, 'closed_trades': len(pnl),
            'window': WINDOW, 'minimum_closed_trades': MIN_CLOSED, 'net_pnl': float(net),
            'profit_factor': float(profit / loss) if loss else None,
            'reason': ('Entradas suspendidas: expectativa realizada negativa; se requiere validar una estrategia nueva'
                       if blocked else 'Recopilando evidencia paper; no implica rentabilidad validada')}


def net_break_even_bid(entry, entry_fee, quantity, fee_pct, slippage_pct):
    """Bid needed to recover actual cost basis after modeled exit costs (not a guarantee)."""
    if quantity <= 0:
        raise ValueError('Quantity must be positive')
    factor = (1 - Decimal(str(fee_pct)) / 100) * (1 - Decimal(str(slippage_pct)) / 100)
    if factor <= 0:
        raise ValueError('Invalid exit costs')
    return (entry + entry_fee / quantity) / factor
