import pandas as pd
import numpy as np
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from app.extensions import db
from app.models import BotConfig, Signal, PaperPosition
from app.services.indicator_service import IndicatorService
from app.utils.helpers import generate_uuid, utc_now


class PricePredictionEngine:
    """
    Lightweight ML-based price prediction using:
    1. Linear Regression on normalized price features
    2. Candlestick pattern recognition (Hammer, Engulfing, Doji, Morning Star)
    3. Momentum divergence detection (price vs RSI)
    4. Mean-reversion vs trend-following adaptive mode
    All pure numpy — no sklearn or tensorflow needed for production speed.
    """

    @staticmethod
    def linear_regression_predict(values: np.ndarray, forecast_periods: int = 3) -> dict:
        """
        OLS Linear Regression on recent price data to predict next N candles.
        Returns slope direction, predicted price, and R² confidence.
        """
        n = len(values)
        if n < 10:
            return {"direction": 0, "predicted_price": float(values[-1]), "r_squared": 0.0, "slope_pct": 0.0}

        x = np.arange(n, dtype=np.float64)
        y = values.astype(np.float64)

        # Normalize to prevent overflow
        y_mean = np.mean(y)
        y_std = np.std(y) if np.std(y) > 0 else 1.0
        y_norm = (y - y_mean) / y_std

        x_mean = np.mean(x)
        x_std = np.std(x) if np.std(x) > 0 else 1.0
        x_norm = (x - x_mean) / x_std

        # OLS: y = mx + b
        cov_xy = np.sum(x_norm * y_norm)
        var_x = np.sum(x_norm ** 2)
        slope = cov_xy / var_x if var_x > 0 else 0.0
        intercept = np.mean(y_norm) - slope * np.mean(x_norm)

        # Predicted values
        y_pred_norm = slope * x_norm + intercept
        ss_res = np.sum((y_norm - y_pred_norm) ** 2)
        ss_tot = np.sum((y_norm - np.mean(y_norm)) ** 2)
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        # Forecast next candle (denormalized)
        x_future = (n + forecast_periods - x_mean) / x_std
        y_future_norm = slope * x_future + intercept
        predicted_price = y_future_norm * y_std + y_mean

        # Slope percentage (annualized-ish)
        slope_pct = (slope * y_std / y_mean * 100) if y_mean > 0 else 0.0
        direction = 1 if slope > 0.01 else (-1 if slope < -0.01 else 0)

        return {
            "direction": direction,
            "predicted_price": float(predicted_price),
            "r_squared": float(max(0, min(1, r_squared))),
            "slope_pct": float(slope_pct)
        }

    @staticmethod
    def detect_candlestick_patterns(df: pd.DataFrame) -> dict:
        """
        Detects key Japanese candlestick reversal/continuation patterns.
        Returns pattern name, bullish/bearish bias, and confidence.
        """
        if len(df) < 5:
            return {"pattern": "NONE", "bias": 0, "confidence": 0.0}

        c = df.iloc[-1]
        p = df.iloc[-2]
        pp = df.iloc[-3]

        o, h, l, cl = float(c['open']), float(c['high']), float(c['low']), float(c['close'])
        po, ph, pl, pcl = float(p['open']), float(p['high']), float(p['low']), float(p['close'])
        body = abs(cl - o)
        upper_wick = h - max(o, cl)
        lower_wick = min(o, cl) - l
        candle_range = h - l if h - l > 0 else 0.0001

        prev_body = abs(pcl - po)
        prev_range = ph - pl if ph - pl > 0 else 0.0001

        patterns = []

        # HAMMER (bullish reversal): Small body at top, long lower wick
        if lower_wick > body * 2 and upper_wick < body * 0.5 and cl > o:
            patterns.append(("HAMMER", 1, 0.75))

        # INVERTED HAMMER (bullish): Small body at bottom, long upper wick after downtrend
        if upper_wick > body * 2 and lower_wick < body * 0.5:
            patterns.append(("INVERTED_HAMMER", 1, 0.60))

        # BULLISH ENGULFING: Current green candle engulfs previous red
        if pcl < po and cl > o and cl > po and o < pcl and body > prev_body:
            patterns.append(("BULLISH_ENGULFING", 1, 0.80))

        # BEARISH ENGULFING: Current red candle engulfs previous green
        if pcl > po and cl < o and cl < po and o > pcl and body > prev_body:
            patterns.append(("BEARISH_ENGULFING", -1, 0.80))

        # DOJI: Very small body relative to range
        if body < candle_range * 0.1 and candle_range > 0:
            patterns.append(("DOJI", 0, 0.50))

        # MORNING STAR (3-candle bullish reversal)
        ppo, ppcl = float(pp['open']), float(pp['close'])
        if ppcl < ppo and abs(pcl - po) < prev_range * 0.3 and cl > o and cl > (ppo + ppcl) / 2:
            patterns.append(("MORNING_STAR", 1, 0.85))

        # EVENING STAR (3-candle bearish reversal)
        if ppcl > ppo and abs(pcl - po) < prev_range * 0.3 and cl < o and cl < (ppo + ppcl) / 2:
            patterns.append(("EVENING_STAR", -1, 0.85))

        # THREE WHITE SOLDIERS
        if len(df) >= 4:
            c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
            if (float(c1['close']) > float(c1['open']) and
                float(c2['close']) > float(c2['open']) and
                float(c3['close']) > float(c3['open']) and
                float(c2['close']) > float(c1['close']) and
                float(c3['close']) > float(c2['close'])):
                patterns.append(("THREE_WHITE_SOLDIERS", 1, 0.85))

        if not patterns:
            return {"pattern": "NONE", "bias": 0, "confidence": 0.0}

        # Return highest confidence pattern
        best = max(patterns, key=lambda x: x[2])
        return {"pattern": best[0], "bias": best[1], "confidence": best[2]}

    @staticmethod
    def detect_divergence(df: pd.DataFrame) -> dict:
        """
        Detects bullish/bearish divergence between price and RSI.
        Bullish divergence: Price makes lower low but RSI makes higher low.
        Bearish divergence: Price makes higher high but RSI makes lower high.
        """
        if len(df) < 20 or 'rsi' not in df.columns:
            return {"type": "NONE", "strength": 0.0}

        lookback = min(20, len(df))
        recent = df.tail(lookback)
        prices = recent['close'].values
        rsis = recent['rsi'].values

        mid = lookback // 2

        price_low1 = np.min(prices[:mid])
        price_low2 = np.min(prices[mid:])
        rsi_low1 = np.min(rsis[:mid])
        rsi_low2 = np.min(rsis[mid:])

        price_high1 = np.max(prices[:mid])
        price_high2 = np.max(prices[mid:])
        rsi_high1 = np.max(rsis[:mid])
        rsi_high2 = np.max(rsis[mid:])

        # Bullish divergence
        if price_low2 < price_low1 and rsi_low2 > rsi_low1:
            strength = min(1.0, abs(rsi_low2 - rsi_low1) / 10.0)
            return {"type": "BULLISH_DIVERGENCE", "strength": strength}

        # Bearish divergence
        if price_high2 > price_high1 and rsi_high2 < rsi_high1:
            strength = min(1.0, abs(rsi_high1 - rsi_high2) / 10.0)
            return {"type": "BEARISH_DIVERGENCE", "strength": strength}

        return {"type": "NONE", "strength": 0.0}

    @staticmethod
    def compute_market_regime(df: pd.DataFrame) -> str:
        """
        Determines current market regime: TRENDING_UP, TRENDING_DOWN, RANGING, or VOLATILE.
        Uses ADX + ATR + price position relative to Bollinger Bands.
        """
        if len(df) < 20:
            return "UNKNOWN"

        latest = df.iloc[-1]
        adx = float(latest.get('adx', 0))
        atr = float(latest.get('atr', 0))
        close = float(latest.get('close', 1))
        bb_upper = float(latest.get('bb_upper', close))
        bb_lower = float(latest.get('bb_lower', close))
        ema_fast = float(latest.get('ema_fast', close))
        ema_slow = float(latest.get('ema_slow', close))

        atr_pct = (atr / close * 100) if close > 0 else 0

        if adx > 30 and ema_fast > ema_slow:
            return "TRENDING_UP"
        elif adx > 30 and ema_fast < ema_slow:
            return "TRENDING_DOWN"
        elif atr_pct > 3.0:
            return "VOLATILE"
        else:
            return "RANGING"


class StrategyService:
    """
    Advanced Multi-Factor Quantitative Trading Strategy Engine with ML Prediction.
    Scores each market on a 0-100 scale using Trend, Momentum, Volume,
    Volatility, Pattern Recognition, and Price Prediction factors.
    Only high-conviction setups (score >= 60) with ML confirmation trigger entries.
    """

    def __init__(self, config: BotConfig):
        self.config = config
        self.predictor = PricePredictionEngine()

    def _score_trend(self, latest: pd.Series) -> tuple:
        """Trend Factor Score (0-20 points): EMA alignment + ADX strength."""
        score = 0.0
        details = []

        ema_fast = float(latest.get('ema_fast', 0))
        ema_slow = float(latest.get('ema_slow', 0))
        adx = float(latest.get('adx', 0))
        close = float(latest.get('close', 0))
        vwap = float(latest.get('vwap', 0))

        # EMA alignment (0-8 pts)
        if ema_fast > ema_slow:
            ema_spread_pct = ((ema_fast - ema_slow) / ema_slow * 100) if ema_slow > 0 else 0
            ema_pts = min(8.0, 4.0 + ema_spread_pct * 2)
            score += ema_pts
            details.append(f"EMA alcista +{ema_pts:.1f}")
        else:
            details.append("EMA bajista +0")

        # ADX strength (0-8 pts)
        if adx >= 40:
            score += 8.0
            details.append(f"ADX fuerte({adx:.0f}) +8")
        elif adx >= 25:
            pts = 4.0 + (adx - 25) / 15 * 4
            score += pts
            details.append(f"ADX moderado({adx:.0f}) +{pts:.1f}")
        elif adx >= 15:
            pts = (adx - 15) / 10 * 4
            score += pts
            details.append(f"ADX debil({adx:.0f}) +{pts:.1f}")

        # Price above VWAP (0-4 pts)
        if close > vwap and vwap > 0:
            score += 4.0
            details.append("Sobre VWAP +4")

        return min(20.0, score), details

    def _score_momentum(self, latest: pd.Series) -> tuple:
        """Momentum Factor Score (0-20 points): RSI + MACD + Stochastic RSI."""
        score = 0.0
        details = []

        rsi = float(latest.get('rsi', 50))
        macd_hist = float(latest.get('macd_histogram', 0))
        macd_bullish = bool(latest.get('macd_bullish_cross', False))
        stoch_k = float(latest.get('stoch_rsi_k', 50))
        stoch_d = float(latest.get('stoch_rsi_d', 50))

        # RSI sweet spot (0-8 pts)
        if 45 <= rsi <= 65:
            score += 8.0
            details.append(f"RSI optimo({rsi:.0f}) +8")
        elif 35 <= rsi <= 75:
            score += 4.0
            details.append(f"RSI aceptable({rsi:.0f}) +4")
        elif rsi < 30:
            score += 6.0
            details.append(f"RSI sobreventa({rsi:.0f}) +6")

        # MACD histogram (0-6 pts)
        if macd_hist > 0:
            pts = min(6.0, 3.0 + abs(macd_hist) * 80)
            score += pts
            details.append(f"MACD+ +{pts:.1f}")
        elif macd_bullish:
            score += 5.0
            details.append("MACD cruce +5")

        # Stochastic RSI (0-6 pts)
        if stoch_k < 25 and stoch_k > stoch_d:
            score += 6.0
            details.append(f"StochRSI rebote +6")
        elif stoch_k > stoch_d and stoch_k < 80:
            score += 3.0
            details.append(f"StochRSI alcista +3")

        return min(20.0, score), details

    def _score_volume(self, latest: pd.Series, df: pd.DataFrame) -> tuple:
        """Volume Factor Score (0-20 points): Volume surge + OBV confirmation."""
        score = 0.0
        details = []

        vol_ratio = float(latest.get('vol_ratio', 1.0))
        obv_current = float(latest.get('obv', 0))

        # Volume surge (0-12 pts)
        if vol_ratio >= 2.5:
            score += 12.0
            details.append(f"Vol explosivo({vol_ratio:.1f}x) +12")
        elif vol_ratio >= 1.5:
            pts = 6.0 + (vol_ratio - 1.5) * 6
            score += pts
            details.append(f"Vol alto({vol_ratio:.1f}x) +{pts:.1f}")
        elif vol_ratio >= 1.0:
            score += 3.0
            details.append(f"Vol normal({vol_ratio:.1f}x) +3")

        # OBV trend (0-8 pts)
        if len(df) >= 10:
            obv_sma = df['obv'].tail(10).mean()
            if obv_current > obv_sma:
                score += 8.0
                details.append("OBV alcista +8")
            elif obv_current > obv_sma * 0.95:
                score += 4.0
                details.append("OBV neutral +4")

        return min(20.0, score), details

    def _score_volatility(self, latest: pd.Series) -> tuple:
        """Volatility Factor Score (0-15 points): BB position + ATR quality."""
        score = 0.0
        details = []

        close = float(latest.get('close', 0))
        bb_upper = float(latest.get('bb_upper', close))
        bb_middle = float(latest.get('bb_middle', close))
        bb_lower = float(latest.get('bb_lower', close))
        bb_width = float(latest.get('bb_width', 0))
        atr = float(latest.get('atr', 0))

        # BB position (0-8 pts)
        if close > bb_middle and (bb_upper - bb_middle) > 0:
            bb_pos = (close - bb_middle) / (bb_upper - bb_middle)
            if bb_pos < 0.7:
                pts = 6.0 + bb_pos * 2
                score += pts
                details.append(f"BB alcista({bb_pos:.0%}) +{pts:.1f}")
            else:
                score += 3.0
                details.append(f"BB techo +3")
        elif close > bb_lower and (bb_middle - bb_lower) > 0:
            bb_pos = (close - bb_lower) / (bb_middle - bb_lower)
            if bb_pos < 0.3:
                score += 7.0
                details.append(f"BB rebote +7")

        # BB squeeze (0-4 pts)
        if bb_width < 0.03:
            score += 4.0
            details.append(f"BB squeeze +4")
        elif bb_width < 0.05:
            score += 2.0

        # ATR quality (0-3 pts)
        if atr > 0 and close > 0:
            atr_pct = (atr / close) * 100
            if 0.5 <= atr_pct <= 3.0:
                score += 3.0
                details.append(f"ATR optimo +3")

        return min(15.0, score), details

    def _score_prediction(self, df: pd.DataFrame) -> tuple:
        """ML Prediction Score (0-15 points): Linear regression + candlestick patterns + divergence."""
        score = 0.0
        details = []

        close_values = df['close'].values

        # Linear Regression Prediction (0-6 pts)
        lr = self.predictor.linear_regression_predict(close_values, forecast_periods=3)
        if lr['direction'] == 1 and lr['r_squared'] > 0.3:
            pts = min(6.0, 3.0 + lr['r_squared'] * 4)
            score += pts
            details.append(f"LR alcista(R2={lr['r_squared']:.2f}) +{pts:.1f}")
        elif lr['direction'] == -1 and lr['r_squared'] > 0.3:
            details.append(f"LR bajista(R2={lr['r_squared']:.2f}) +0")

        # Candlestick Pattern (0-5 pts)
        pattern = self.predictor.detect_candlestick_patterns(df)
        if pattern['bias'] == 1 and pattern['confidence'] > 0.5:
            pts = min(5.0, pattern['confidence'] * 5)
            score += pts
            details.append(f"{pattern['pattern']}({pattern['confidence']:.0%}) +{pts:.1f}")
        elif pattern['bias'] == -1:
            details.append(f"{pattern['pattern']} bajista +0")

        # Divergence Detection (0-4 pts)
        div = self.predictor.detect_divergence(df)
        if div['type'] == 'BULLISH_DIVERGENCE':
            pts = min(4.0, 2.0 + div['strength'] * 3)
            score += pts
            details.append(f"Div.Alcista({div['strength']:.1f}) +{pts:.1f}")
        elif div['type'] == 'BEARISH_DIVERGENCE':
            details.append(f"Div.Bajista +0")

        return min(15.0, score), details

    def _score_regime(self, df: pd.DataFrame) -> tuple:
        """Market Regime Score (0-10 points): Adaptive mode detection."""
        score = 0.0
        details = []

        regime = self.predictor.compute_market_regime(df)

        if regime == "TRENDING_UP":
            score += 10.0
            details.append("Regimen TENDENCIA ALCISTA +10")
        elif regime == "RANGING":
            score += 5.0
            details.append("Regimen RANGO +5")
        elif regime == "VOLATILE":
            score += 3.0
            details.append("Regimen VOLATIL +3")
        else:
            details.append(f"Regimen {regime} +0")

        return min(10.0, score), details

    def compute_composite_score(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Computes the full multi-factor composite score with ML prediction."""
        latest = df.iloc[-1]

        trend_score, trend_details = self._score_trend(latest)
        momentum_score, momentum_details = self._score_momentum(latest)
        volume_score, volume_details = self._score_volume(latest, df)
        volatility_score, volatility_details = self._score_volatility(latest)
        prediction_score, prediction_details = self._score_prediction(df)
        regime_score, regime_details = self._score_regime(df)

        total_score = trend_score + momentum_score + volume_score + volatility_score + prediction_score + regime_score

        # ML Prediction data
        lr = self.predictor.linear_regression_predict(df['close'].values, forecast_periods=3)
        pattern = self.predictor.detect_candlestick_patterns(df)
        divergence = self.predictor.detect_divergence(df)
        regime = self.predictor.compute_market_regime(df)

        return {
            "total_score": round(total_score, 1),
            "trend_score": round(trend_score, 1),
            "momentum_score": round(momentum_score, 1),
            "volume_score": round(volume_score, 1),
            "volatility_score": round(volatility_score, 1),
            "prediction_score": round(prediction_score, 1),
            "regime_score": round(regime_score, 1),
            "trend_details": trend_details,
            "momentum_details": momentum_details,
            "volume_details": volume_details,
            "volatility_details": volatility_details,
            "prediction_details": prediction_details,
            "regime_details": regime_details,
            "ml_prediction": {
                "lr_direction": lr['direction'],
                "lr_predicted_price": lr['predicted_price'],
                "lr_r_squared": lr['r_squared'],
                "lr_slope_pct": lr['slope_pct'],
                "candle_pattern": pattern['pattern'],
                "candle_bias": pattern['bias'],
                "candle_confidence": pattern['confidence'],
                "divergence_type": divergence['type'],
                "divergence_strength": divergence['strength'],
                "market_regime": regime,
            },
            "indicators": {
                "close": float(latest.get('close', 0)),
                "ema_fast": float(latest.get('ema_fast', 0)),
                "ema_slow": float(latest.get('ema_slow', 0)),
                "rsi": float(latest.get('rsi', 50)),
                "macd_line": float(latest.get('macd_line', 0)),
                "macd_signal": float(latest.get('macd_signal', 0)),
                "macd_histogram": float(latest.get('macd_histogram', 0)),
                "bb_upper": float(latest.get('bb_upper', 0)),
                "bb_middle": float(latest.get('bb_middle', 0)),
                "bb_lower": float(latest.get('bb_lower', 0)),
                "bb_width": float(latest.get('bb_width', 0)),
                "atr": float(latest.get('atr', 0)),
                "adx": float(latest.get('adx', 0)),
                "stoch_rsi_k": float(latest.get('stoch_rsi_k', 50)),
                "stoch_rsi_d": float(latest.get('stoch_rsi_d', 50)),
                "obv": float(latest.get('obv', 0)),
                "vwap": float(latest.get('vwap', 0)),
                "vol_ratio": float(latest.get('vol_ratio', 1.0)),
                "bullish_cross": bool(latest.get('bullish_cross', False)),
                "bearish_cross": bool(latest.get('bearish_cross', False)),
                "macd_bullish_cross": bool(latest.get('macd_bullish_cross', False)),
            }
        }

    def evaluate_market(self, df: pd.DataFrame, symbol: str, bot_run_id: str) -> Optional[Signal]:
        """
        Evaluates market using multi-factor scoring + ML prediction.
        Entry requires score >= 60 with prediction confirmation.
        """
        if df.empty or len(df) < 30:
            return None

        # Apply full indicator suite
        df = IndicatorService.apply_indicators(
            df,
            ema_fast=self.config.ema_fast_period,
            ema_slow=self.config.ema_slow_period,
            rsi_period=self.config.rsi_period
        )

        latest = df.iloc[-1]
        close_price = float(latest['close'])
        rsi = float(latest.get('rsi', 50))
        adx = float(latest.get('adx', 0))
        vol_ratio = float(latest.get('vol_ratio', 1.0))
        bb_middle = float(latest.get('bb_middle', close_price))
        bearish_cross = bool(latest.get('bearish_cross', False))

        # Compute composite score
        score_data = self.compute_composite_score(df)
        total_score = score_data['total_score']
        ml = score_data['ml_prediction']

        # Check existing position
        position = PaperPosition.query.filter_by(symbol=symbol, is_open=True).first()

        # Check Cooldown
        last_signal = Signal.query.filter_by(symbol=symbol).order_by(Signal.timestamp.desc()).first()
        if last_signal:
            cooldown_delta = timedelta(seconds=self.config.cooldown_seconds)
            if utc_now() - last_signal.timestamp < cooldown_delta:
                return None

        indicators_json_str = json.dumps(score_data['indicators'])

        # ==========================================
        # EXIT LONG LOGIC (check first)
        # ==========================================
        if position:
            should_exit = False
            exit_reasons = []

            if total_score < 25:
                should_exit = True
                exit_reasons.append(f"Score critico({total_score:.0f}/100)")

            if bearish_cross and adx > 25:
                should_exit = True
                exit_reasons.append("Cruce EMA bajista con ADX fuerte")

            if rsi > 80:
                should_exit = True
                exit_reasons.append(f"RSI sobrecompra({rsi:.0f})")

            if ml['divergence_type'] == 'BEARISH_DIVERGENCE' and ml['divergence_strength'] > 0.5:
                should_exit = True
                exit_reasons.append("Divergencia bajista RSI/Precio")

            if ml['candle_pattern'] in ('BEARISH_ENGULFING', 'EVENING_STAR') and ml['candle_confidence'] > 0.7:
                should_exit = True
                exit_reasons.append(f"Patron {ml['candle_pattern']}")

            if ml['lr_direction'] == -1 and ml['lr_r_squared'] > 0.5:
                should_exit = True
                exit_reasons.append(f"LR bajista(R2={ml['lr_r_squared']:.2f})")

            if should_exit and exit_reasons:
                reason = (
                    f"EXIT ML: {' + '.join(exit_reasons)} | "
                    f"Score={total_score:.0f} T={score_data['trend_score']:.0f} M={score_data['momentum_score']:.0f} "
                    f"V={score_data['volume_score']:.0f} Vol={score_data['volatility_score']:.0f} "
                    f"Pred={score_data['prediction_score']:.0f} Reg={score_data['regime_score']:.0f}"
                )
                signal = Signal(
                    id=generate_uuid(), bot_run_id=bot_run_id, symbol=symbol,
                    type='SELL', action='EXIT_LONG', price=close_price,
                    reason=reason, indicators_json=indicators_json_str,
                    status='PENDING', timestamp=utc_now()
                )
                db.session.add(signal)
                db.session.commit()
                return signal

        # ==========================================
        # ENTRY LONG LOGIC
        # ==========================================
        if not position:
            # Multi-factor + ML entry conditions:
            entry_conditions = [
                total_score >= 60,                          # Composite score threshold
                close_price > bb_middle,                    # Above BB middle
                vol_ratio >= 0.8,                           # Reasonable volume
                adx >= 18,                                  # Trend present
                ml['lr_direction'] >= 0,                    # LR not bearish
                ml['market_regime'] != 'TRENDING_DOWN',     # Not in downtrend
            ]

            # ML bonus: lower threshold if strong ML signals
            ml_bonus = (
                (ml['candle_bias'] == 1 and ml['candle_confidence'] > 0.7) or
                (ml['divergence_type'] == 'BULLISH_DIVERGENCE') or
                (ml['lr_direction'] == 1 and ml['lr_r_squared'] > 0.5)
            )

            if ml_bonus and total_score >= 50:
                entry_conditions[0] = True  # Allow entry at lower score with ML confirmation

            if all(entry_conditions):
                reason = (
                    f"ENTRY ML Score={total_score:.0f}/100 | "
                    f"T={score_data['trend_score']:.0f} M={score_data['momentum_score']:.0f} "
                    f"V={score_data['volume_score']:.0f} Vol={score_data['volatility_score']:.0f} "
                    f"Pred={score_data['prediction_score']:.0f} Reg={score_data['regime_score']:.0f} | "
                    f"LR(R2={ml['lr_r_squared']:.2f},pred=${ml['lr_predicted_price']:.2f}) "
                    f"Pattern={ml['candle_pattern']} Regime={ml['market_regime']} "
                    f"RSI={rsi:.0f} ADX={adx:.0f}"
                )
                signal = Signal(
                    id=generate_uuid(), bot_run_id=bot_run_id, symbol=symbol,
                    type='BUY', action='ENTER_LONG', price=close_price,
                    reason=reason, indicators_json=indicators_json_str,
                    status='PENDING', timestamp=utc_now()
                )
                db.session.add(signal)
                db.session.commit()
                return signal

        return None
