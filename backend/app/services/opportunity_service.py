"""Versioned, deterministic paper strategies. Scores are NOT calibrated probabilities."""
import json
import math
from datetime import datetime, timezone

from app.extensions import db
from app.models import PaperPosition, Signal
from app.services.indicator_service import IndicatorService
from app.utils.helpers import generate_uuid, utc_now


PROFILES = ('trend-pullback-v2', 'relative-breakout-v1')


class OpportunityService:
    @staticmethod
    def rank(tickers):
        # Deterministic tie-breaking prevents alphabetic or API-order allocation bias.
        return sorted(tickers, key=lambda s: (-float(tickers[s].get('change_pct') or 0), s))

    @staticmethod
    def decide(profile, frame, hourly, four_hourly, ticker, relative_rank, round_trip_cost_pct=0.3):
        if profile not in PROFILES:
            raise ValueError(f'Unknown strategy profile: {profile}')
        for data, minutes in ((frame, 15), (hourly, 60), (four_hourly, 240)):
            if len(data) < 100:
                raise ValueError('Insufficient closed candle history for multi-timeframe decision')
            age = datetime.now(timezone.utc).timestamp() * 1000 - int(data.iloc[-1]['timestamp'])
            if age < minutes * 60_000 or age > 3 * minutes * 60_000:
                raise ValueError('Stale or open candle in multi-timeframe decision')
        latest, previous = frame.iloc[-1], frame.iloc[-2]
        price = float(latest['close'])
        atr = float(IndicatorService.calculate_atr(frame).iloc[-1])
        if not math.isfinite(atr) or atr <= 0 or price <= 0:
            raise ValueError('Invalid ATR or price')
        stop_pct = max(1.0, 2.0 * atr / price * 100.0)
        reward_risk = 2.5 if profile == 'trend-pullback-v2' else 3.0
        tp_pct = stop_pct * reward_risk
        bid, ask = float(ticker.get('bid') or 0), float(ticker.get('ask') or 0)
        spread_pct = (ask - bid) / bid * 100 if bid > 0 and ask >= bid else float('inf')
        hourly_ema20 = hourly['close'].ewm(span=20, adjust=False).mean()
        hourly_ema50 = hourly['close'].ewm(span=50, adjust=False).mean()
        four_ema50 = four_hourly['close'].ewm(span=50, adjust=False).mean()
        trend = (float(hourly.iloc[-1]['close']) > hourly_ema20.iloc[-1] > hourly_ema50.iloc[-1]
                 and float(four_hourly.iloc[-1]['close']) > four_ema50.iloc[-1]
                 and four_ema50.iloc[-1] > four_ema50.iloc[-5])
        ema20 = frame['close'].ewm(span=20, adjust=False).mean()
        volume_average = float(frame['volume'].iloc[-21:-1].mean())
        volume_ratio = float(latest['volume']) / volume_average if volume_average > 0 else 0
        pullback = (float(frame['low'].iloc[-5:-1].min()) <= float(ema20.iloc[-2])
                    and float(previous['close']) <= float(ema20.iloc[-2])
                    and price > float(ema20.iloc[-1]) and price > float(previous['high']))
        breakout = (price > float(frame['high'].iloc[-21:-1].max())
                    and price - float(frame['high'].iloc[-21:-1].max()) <= atr
                    and relative_rank <= 5)
        checks = {
            'liquidity': float(ticker.get('quote_volume') or 0) >= 20_000_000,
            'spread': spread_pct <= 0.10,
            'cost_headroom': tp_pct >= 5 * (round_trip_cost_pct + spread_pct),
            'trend_1h_4h': bool(trend),
            'volatility': 1.0 <= stop_pct <= 2.5,
            'not_extended': price <= float(ema20.iloc[-1]) + 2.5 * atr,
            'volume': volume_ratio >= (1.0 if profile == 'trend-pullback-v2' else 1.5),
            'setup': bool(pullback if profile == 'trend-pullback-v2' else breakout),
        }
        return {
            'profile': profile, 'eligible': all(checks.values()), 'checks': checks,
            'stop_loss_pct': stop_pct, 'take_profit_pct': tp_pct,
            'spread_pct': spread_pct if math.isfinite(spread_pct) else None,
            'volume_ratio': volume_ratio, 'relative_rank': relative_rank,
            'quote_volume': float(ticker.get('quote_volume') or 0),
            'round_trip_cost_pct': round_trip_cost_pct,
            'hourly_close': float(hourly.iloc[-1]['close']),
            'four_hourly_close': float(four_hourly.iloc[-1]['close']),
        }

    @staticmethod
    def signal(config, symbol, bot_run_id, frame, decision):
        position = PaperPosition.query.filter_by(symbol=symbol, is_open=True).first()
        last = Signal.query.filter_by(symbol=symbol).order_by(Signal.timestamp.desc()).first()
        if last and (utc_now() - last.timestamp).total_seconds() < config.cooldown_seconds:
            return None
        if position:
            # No noisy 15m score exits: exit on confirmed higher-timeframe trend loss.
            if decision['checks']['trend_1h_4h']:
                return None
            side, action = 'SELL', 'EXIT_LONG'
        elif decision['eligible']:
            side, action = 'BUY', 'ENTER_LONG'
        else:
            return None
        signal = Signal(
            id=generate_uuid(), bot_run_id=bot_run_id, symbol=symbol, type=side,
            action=action, price=float(frame.iloc[-1]['close']), status='PENDING',
            reason=f"{config.strategy_key}: {action}",
            indicators_json=json.dumps({'opportunity': decision}), timestamp=utc_now(),
        )
        db.session.add(signal)
        db.session.commit()
        return signal
