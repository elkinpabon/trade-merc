"""A frozen, testable hypothesis. No forecast probabilities or profit guarantees."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from math import isfinite

VERSION = 'impulse-consolidation-v1'


def decimal(value):
    return Decimal(str(value))


def floor_step(value, step):
    value, step = decimal(value), decimal(step)
    if step <= 0:
        raise ValueError('Quantity step must be positive')
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step


@dataclass(frozen=True)
class Policy:
    initial_cash: float = 50.0
    risk_pct: float = 0.5
    max_exposure_pct: float = 30.0
    fee_pct: float = 0.1
    slippage_pct: float = 0.05
    max_spread_pct: float = 0.12
    daily_loss_pct: float = 3.0
    max_drawdown_pct: float = 10.0
    max_hold_minutes: int = 90
    cooldown_minutes: int = 30
    min_volume_usdt: float = 10_000_000.0
    scan_limit: int = 40


POLICY = Policy()


def quote_valid(ticker):
    try:
        bid, ask = float(ticker['bid']), float(ticker['ask'])
        return all(isfinite(x) and x > 0 for x in (bid, ask)) and ask >= bid
    except (TypeError, KeyError, ValueError):
        return False


def spread_pct(ticker):
    if not quote_valid(ticker):
        return None
    return (float(ticker['ask']) / float(ticker['bid']) - 1) * 100


def ema(values, span):
    result = float(values[0])
    alpha = 2 / (span + 1)
    for value in values[1:]:
        result += alpha * (float(value) - result)
    return result


def evaluate(candles, ticker, now_ms, policy=POLICY):
    """Binance 5m candles: decisions use only consecutive, fully CLOSED bars.

    Candidate pattern: impulse over 6 bars, 3-bar consolidation, breakout.
    This is a hypothesis for prospective testing, not a verified edge.
    """
    bars = [c for c in candles if int(c[6]) < now_ms]
    if len(bars) < 60:
        raise ValueError('Historia insuficiente: se requieren 60 velas cerradas')
    bars = bars[-100:]
    if now_ms - int(bars[-1][6]) > 420_000:
        raise ValueError('Velas obsoletas')
    if any(int(b[0]) - int(a[0]) != 300_000 for a, b in zip(bars, bars[1:])):
        raise ValueError('Huecos en las velas de 5 minutos')
    for bar in bars:
        o, h, l, c, v = map(float, bar[1:6])
        if not all(isfinite(x) for x in (o, h, l, c, v)) or min(o, h, l, c) <= 0 or v < 0 or h < max(o, c, l) or l > min(o, c):
            raise ValueError('OHLCV inválido')
    closes = [float(c[4]) for c in bars]
    last = bars[-1]
    price = closes[-1]
    atr = sum(max(float(b[2]) - float(b[3]), abs(float(b[2]) - float(a[4])), abs(float(b[3]) - float(a[4])))
              for a, b in zip(bars[-15:-1], bars[-14:])) / 14
    if atr <= 0:
        raise ValueError('Volatilidad insuficiente')
    consolidation = bars[-4:-1]
    range_high = max(float(c[2]) for c in consolidation)
    range_low = min(float(c[3]) for c in consolidation)
    impulse_start = float(bars[-10][4])
    impulse_end = float(bars[-4][4])
    impulse_pct = (impulse_end / impulse_start - 1) * 100
    impulse_size = impulse_end - impulse_start
    avg_volume = sum(float(c[5]) for c in bars[-25:-1]) / 24
    volume_ratio = float(last[5]) / avg_volume if avg_volume else 0
    quote_volume = float(last[7])
    taker_ratio = float(last[10]) / quote_volume if quote_volume > 0 else 0
    spread = spread_pct(ticker)
    stop_pct = max(0.8, atr / price * 150, (price - range_low) / price * 100)
    target_pct = stop_pct * 2
    one_hour_return = (price / closes[-13] - 1) * 100
    checks = {
        'liquidity': float(ticker['volume_usdt']) >= policy.min_volume_usdt,
        'spread': spread is not None and spread <= policy.max_spread_pct,
        'impulse': 0.5 <= impulse_pct <= 6.0,
        'consolidation': range_high - range_low <= 2 * atr and impulse_size > 0 and range_low >= impulse_start + .4 * impulse_size,
        'breakout': price > range_high and price - range_high <= atr,
        'volume': volume_ratio >= 1.5,
        'buy_pressure': taker_ratio >= .55,
        'trend': price > ema(closes, 20) > ema(closes, 50),
        'risk': .8 <= stop_pct <= 3.0,
        'costs': spread is not None and target_pct >= 4 * (2 * (policy.fee_pct + policy.slippage_pct) + spread),
    }
    labels = {'liquidity': 'Liquidez insuficiente', 'spread': 'Spread alto o desconocido',
              'impulse': 'Sin impulso válido', 'consolidation': 'Consolidación no confirmada',
              'breakout': 'Esperando ruptura', 'volume': 'Volumen sin expansión',
              'buy_pressure': 'Compradores sin confirmar', 'trend': 'Tendencia no alineada',
              'risk': 'Stop demasiado amplio', 'costs': 'Margen insuficiente frente a costes'}
    score = round(sum(checks.values()) / len(checks) * 100)
    return {'eligible': all(checks.values()), 'score': score, 'checks': checks,
            'reasons': [labels[k] for k, v in checks.items() if not v],
            'candle_at': int(last[0]), 'price': price, 'atr': atr,
            'stop_pct': stop_pct, 'target_pct': target_pct, 'volume_ratio': volume_ratio,
            'impulse_pct': impulse_pct, 'return_1h': one_hour_return,
            'taker_ratio': taker_ratio, 'range_high': range_high, 'range_low': range_low,
            'spread_pct': spread, 'strategy': VERSION}


def size_order(cash, equity, ask, stop_pct, rule, policy=POLICY):
    """Never round up to satisfy a minimum. Reserve both fees and slippage in risk."""
    cash, equity, ask = map(decimal, (cash, equity, ask))
    fee = decimal(policy.fee_pct) / 100
    slip = decimal(policy.slippage_pct) / 100
    fill = ask * (1 + slip)
    risk_per_unit = ask * (decimal(stop_pct) / 100 + 2 * fee + 2 * slip)
    if min(cash, equity, ask, risk_per_unit) <= 0:
        raise ValueError('Capital o precio inválido')
    budget = min(cash / (1 + fee), equity * decimal(policy.max_exposure_pct) / 100)
    qty = floor_step(min(equity * decimal(policy.risk_pct) / 100 / risk_per_unit,
                         budget / fill, decimal(rule['max_qty'])), rule['step'])
    if qty <= 0 or qty < decimal(rule['min_qty']) or qty * ask < decimal(rule['min_notional']):
        raise ValueError('El tamaño por riesgo no alcanza el mínimo del mercado')
    if qty * ask > decimal(rule.get('max_notional', '1e30')):
        raise ValueError('El tamaño supera el máximo del mercado')
    notional = qty * fill
    return {'quantity': qty, 'fill': fill, 'fee': notional * fee, 'debit': notional * (1 + fee)}
