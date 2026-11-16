"""Fail-closed executable quotes, independent of exchange order submission."""
import math
from datetime import datetime, timezone


def executable_price(ticker, side, signal_price=None, now_ms=None):
    now_ms = now_ms if now_ms is not None else int(datetime.now(timezone.utc).timestamp() * 1000)
    try:
        bid, ask = float(ticker['bid']), float(ticker['ask'])
        age = now_ms - int(ticker['timestamp'])
        if not all(math.isfinite(v) and v > 0 for v in (bid, ask)) or ask < bid:
            raise ValueError('Invalid bid/ask')
        if age < 0 or age > 45_000:
            raise ValueError('Stale executable quote')
        side = side.upper()
        if side not in ('BUY', 'SELL'):
            raise ValueError('Unknown side')
        price = ask if side == 'BUY' else bid
        if side == 'BUY':
            if (ask / bid - 1) * 100 > .10:
                raise ValueError('Executable spread exceeds 0.10%')
            if not signal_price or not math.isfinite(float(signal_price)) or float(signal_price) <= 0:
                raise ValueError('Invalid signal price')
            if abs(price / float(signal_price) - 1) > .003:
                raise ValueError('Entry moved more than 0.30% from closed-candle signal')
        return price
    except (KeyError, TypeError, OverflowError) as exc:
        raise ValueError('Missing executable quote') from exc
