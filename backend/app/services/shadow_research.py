"""Prospective candidate entry intents only. There is deliberately no submission path."""
import math
from datetime import datetime, timezone

from .execution_quotes import executable_price

REVISION = 'protected-v1-shadow-2026-11-16'


def benchmark_context(hourly, four_hourly, now_ms=None):
    at = now_ms if now_ms is not None else int(datetime.now(timezone.utc).timestamp() * 1000)
    for frame, minutes in ((hourly, 60), (four_hourly, 240)):
        if len(frame) < 100:
            raise ValueError('Insufficient benchmark history')
        age = at - int(frame.iloc[-1]['timestamp'])
        if not minutes * 60_000 <= age <= 3 * minutes * 60_000:
            raise ValueError('Stale or unclosed benchmark candle')
    h20 = hourly['close'].ewm(span=20, adjust=False).mean()
    h50 = hourly['close'].ewm(span=50, adjust=False).mean()
    f50 = four_hourly['close'].ewm(span=50, adjust=False).mean()
    values = [float(hourly.iloc[-1]['close']), float(h20.iloc[-1]), float(h50.iloc[-1]),
              float(four_hourly.iloc[-1]['close']), float(f50.iloc[-1]), float(f50.iloc[-5])]
    if not all(math.isfinite(v) and v > 0 for v in values):
        raise ValueError('Invalid benchmark prices')
    return {'status': 'OK', 'bullish': bool(values[0] > values[1] > values[2]
                                          and values[3] > values[4] > values[5]),
            'observed_at': at, 'hourly_candle_at': int(hourly.iloc[-1]['timestamp']),
            'four_hour_candle_at': int(four_hourly.iloc[-1]['timestamp'])}


def candidate_intent(decision, benchmark, quote, reference_price, rule, at=None):
    at = at if at is not None else int(datetime.now(timezone.utc).timestamp() * 1000)
    checks = {'base_setup': bool(decision['eligible']),
              'benchmark_regime': bool(benchmark.get('status') == 'OK' and benchmark.get('bullish')
                                       and 0 <= at - benchmark.get('observed_at', 0) <= 180_000),
              'executable_quote': False, 'configured_rule_available': rule is not None}
    quote_error = None
    try:
        executable_price(quote, 'BUY', reference_price, at)
        checks['executable_quote'] = True
    except ValueError as exc:
        quote_error = str(exc)
    return {'revision': REVISION, 'candidate': decision['profile'] + ':protected-v1',
            'mode': 'SHADOW', 'entry_intent': all(checks.values()), 'checks': checks,
            'blocked_by': [k for k, v in checks.items() if not v], 'quote_error': quote_error,
            'order_submission_allowed': False, 'profitability_validated': False,
            'recorded_at': at, 'benchmark': benchmark,
            'quote': {k: quote.get(k) for k in ('bid', 'ask', 'timestamp')},
            'configured_rule': rule, 'note': 'Entry intent, not an order or a simulated fill'}
