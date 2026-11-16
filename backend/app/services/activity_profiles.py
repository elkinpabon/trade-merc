"""Explicitly authorized PAPER hypotheses, not calibrated or proven profitable models."""
import math

from app.services.indicator_service import IndicatorService

PILOT_PROFILES = {
    'intraday-reclaim-paper-v1': {'cooldown_seconds': 3600, 'max_hold_minutes': 360},
    'intraday-breakout-paper-v1': {'cooldown_seconds': 3600, 'max_hold_minutes': 480},
}
PILOT_LIMITS = {'risk_per_trade_pct': .25, 'daily_loss_pct': 1.5,
                'max_drawdown_pct': 5., 'max_entries_per_day': 8,
                'max_positions': 2, 'max_exposure_pct': 20., 'reward_risk': 2.}
REVISION = 'activity-paper-v1-2026-11-16'


def features(frame):
    """Vectorized, causal features shared by live decisions and historical diagnostics."""
    f = frame.copy()
    f['ema20'] = f['close'].ewm(span=20, adjust=False).mean()
    f['ema50'] = f['close'].ewm(span=50, adjust=False).mean()
    f['previous_ema20'] = f['ema20'].shift(1)
    f['previous_high'] = f['high'].shift(1)
    f['recent_low'] = f['low'].shift(1).rolling(4).min()
    f['breakout_high'] = f['high'].shift(1).rolling(10).max()
    f['atr'] = IndicatorService.calculate_atr(f)
    f['rsi'] = IndicatorService.calculate_rsi(f['close'])
    f['volume_ratio'] = f['volume'] / f['volume'].shift(1).rolling(20).mean().replace(0, float('nan'))
    return f


def context(frame):
    f = frame[['timestamp', 'close']].copy()
    f['ema20'] = f['close'].ewm(span=20, adjust=False).mean()
    f['ema50'] = f['close'].ewm(span=50, adjust=False).mean()
    return f


def assess(profile, f, hourly, four, ticker, relative_rank, round_trip_cost_pct=.3):
    if profile not in PILOT_PROFILES:
        raise ValueError('Unknown activity pilot')
    required = [float(f[k]) for k in ('close', 'open', 'atr', 'rsi', 'volume_ratio', 'ema20',
                                     'ema50', 'previous_ema20', 'previous_high', 'recent_low', 'breakout_high')]
    required += [float(row[k]) for row in (hourly, four) for k in ('close', 'ema20', 'ema50')]
    if not all(math.isfinite(v) for v in required) or min(float(f['close']), float(f['atr'])) <= 0:
        raise ValueError('Invalid activity pilot features')
    price, atr = float(f['close']), float(f['atr'])
    stop = max(1., 2 * atr / price * 100)
    target = 2 * stop
    bid, ask = float(ticker.get('bid') or 0), float(ticker.get('ask') or 0)
    spread = (ask / bid - 1) * 100 if 0 < bid <= ask and math.isfinite(ask) else float('inf')
    if profile == 'intraday-reclaim-paper-v1':
        regime = float(hourly['close']) >= float(hourly['ema50']) * .995 and float(hourly['ema20']) >= float(hourly['ema50']) * .998
        setup = (float(f['recent_low']) <= float(f['previous_ema20']) and price > float(f['ema20'])
                 and price > float(f['previous_high']) and price > float(f['open']))
        momentum = 40 <= float(f['rsi']) <= 70
        local_trend = float(f['ema20']) >= float(f['ema50']) * .998
        volume = float(f['volume_ratio']) >= 1.
    else:
        regime = float(hourly['close']) >= float(hourly['ema20'])
        setup = 0 < price - float(f['breakout_high']) <= atr and relative_rank <= 10
        momentum = 45 <= float(f['rsi']) <= 75
        local_trend = float(f['ema20']) >= float(f['ema50'])
        volume = float(f['volume_ratio']) >= 1.2
    regime = bool(regime and float(four['close']) >= float(four['ema50']) * .95)
    checks = {'liquidity': float(ticker.get('quote_volume') or 0) >= 20_000_000,
              'spread': spread <= .10,
              'cost_headroom': target >= 5 * (round_trip_cost_pct + spread),
              'trend_1h_4h': regime, 'intraday_trend': bool(local_trend),
              'volatility': 1 <= stop <= 2.5,
              'not_extended': price <= float(f['ema20']) + 2.5 * atr,
              'volume': bool(volume), 'momentum': bool(momentum), 'setup': bool(setup)}
    return {'profile': profile, 'implementation_revision': REVISION,
            'experimental_paper': True, 'profitability_validated': False,
            'eligible': all(checks.values()), 'checks': checks,
            'stop_loss_pct': stop, 'take_profit_pct': target,
            'spread_pct': spread if math.isfinite(spread) else None,
            'volume_ratio': float(f['volume_ratio']), 'rsi': float(f['rsi']),
            'quote_volume': float(ticker.get('quote_volume') or 0),
            'relative_rank': relative_rank, 'round_trip_cost_pct': round_trip_cost_pct,
            'blocked_by': [k for k, v in checks.items() if not v],
            'pilot_policy': {**PILOT_LIMITS, **PILOT_PROFILES[profile]}}
