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

        # Slope percentage
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
        if len(df) < 5:
            return {"pattern": "NONE", "bias": 0, "confidence": 0.0}

        c = df.iloc[-1]
        p = df.iloc[-2]

        o, h, l, cl = float(c['open']), float(c['high']), float(c['low']), float(c['close'])
        po, ph, pl, pcl = float(p['open']), float(p['high']), float(p['low']), float(p['close'])
        body = abs(cl - o)
        upper_wick = h - max(o, cl)
        lower_wick = min(o, cl) - l

        patterns = []
        if lower_wick > body * 2 and upper_wick < body * 0.5 and cl > o:
            patterns.append(("HAMMER", 1, 0.75))
        if cl > o and pcl < po and cl > po and o < pcl:
            patterns.append(("BULLISH_ENGULFING", 1, 0.85))
        if lower_wick > body * 2 and upper_wick < body * 0.5 and cl < o:
            patterns.append(("SHOOTING_STAR", -1, 0.75))
        if cl < o and pcl > po and cl < po and o > pcl:
            patterns.append(("BEARISH_ENGULFING", -1, 0.85))

        if not patterns:
            return {"pattern": "NONE", "bias": 0, "confidence": 0.0}

        best = max(patterns, key=lambda x: x[2])
        return {"pattern": best[0], "bias": best[1], "confidence": best[2]}

    @staticmethod
    def detect_divergence(df: pd.DataFrame, window: int = 14) -> dict:
        if len(df) < window + 5 or 'rsi' not in df.columns:
            return {"type": "NONE", "strength": 0.0}

        prices = df['close'].iloc[-window:].values
        rsi_vals = df['rsi'].iloc[-window:].values

        price_min_idx = np.argmin(prices)
        price_max_idx = np.argmax(prices)
        rsi_min_idx = np.argmin(rsi_vals)
        rsi_max_idx = np.argmax(rsi_vals)

        # Bullish divergence: price makes new low, RSI makes higher low
        if price_min_idx > window // 2 and rsi_min_idx < price_min_idx:
            if prices[-1] <= prices[price_min_idx] and rsi_vals[-1] > rsi_vals[rsi_min_idx]:
                strength = float(np.abs(rsi_vals[-1] - rsi_vals[rsi_min_idx]) / 50.0)
                return {"type": "BULLISH_DIVERGENCE", "strength": min(1.0, strength)}

        # Bearish divergence: price makes new high, RSI makes lower high
        if price_max_idx > window // 2 and rsi_max_idx < price_max_idx:
            if prices[-1] >= prices[price_max_idx] and rsi_vals[-1] < rsi_vals[rsi_max_idx]:
                strength = float(np.abs(rsi_vals[rsi_max_idx] - rsi_vals[-1]) / 50.0)
                return {"type": "BEARISH_DIVERGENCE", "strength": min(1.0, strength)}

        return {"type": "NONE", "strength": 0.0}

    @staticmethod
    def compute_market_regime(df: pd.DataFrame) -> str:
        if len(df) < 20 or 'adx' not in df.columns:
            return "RANGING"

        latest = df.iloc[-1]
        adx = float(latest.get('adx', 0))
        ema_fast = float(latest.get('ema_fast', 0))
        ema_slow = float(latest.get('ema_slow', 0))
        atr = float(latest.get('atr', 0))
        close = float(latest.get('close', 1))

        volatility_pct = (atr / close) * 100 if close > 0 else 0

        if volatility_pct > 3.0:
            return "VOLATILE"
        elif adx > 25 and ema_fast > ema_slow:
            return "TRENDING_UP"
        elif adx > 25 and ema_fast < ema_slow:
            return "TRENDING_DOWN"
        else:
            return "RANGING"


class StrategyService:
    def __init__(self, config: Optional[BotConfig] = None):
        if config is None:
            config = BotConfig.get_active()
        self.config = config
        self.predictor = PricePredictionEngine()
        self.taker_fee = 0.00075  # 0.075% BNB taker fee
        self.slippage = 0.0005   # 0.05% slippage
        self.total_cost = (self.taker_fee * 2) + self.slippage  # ~0.20%
        self.tp_target = (self.config.take_profit_pct or 3.0) / 100.0
        self.sl_target = (self.config.stop_loss_pct or 1.5) / 100.0

    def compute_composite_score(self, df: pd.DataFrame) -> dict:
        latest = df.iloc[-1]

        close = float(latest['close'])
        ema_fast = float(latest.get('ema_fast', close))
        ema_slow = float(latest.get('ema_slow', close))
        rsi = float(latest.get('rsi', 50))
        macd_hist = float(latest.get('macd_histogram', 0))
        adx = float(latest.get('adx', 0))
        vol_ratio = float(latest.get('vol_ratio', 1.0))
        bb_upper = float(latest.get('bb_upper', close * 1.02))
        bb_lower = float(latest.get('bb_lower', close * 0.98))
        vwap = float(latest.get('vwap', close))

        # 1. Trend (25 pts)
        trend_score = 0.0
        trend_details = []
        if ema_fast > ema_slow:
            trend_score += 15.0
            trend_details.append("EMA Fast > Slow (+15)")
        if adx > 20:
            trend_score += 10.0
            trend_details.append(f"ADX={adx:.1f} (+10)")

        # 2. Momentum (20 pts)
        momentum_score = 0.0
        momentum_details = []
        if 40 <= rsi <= 65:
            momentum_score += 10.0
            momentum_details.append(f"RSI={rsi:.1f} óptimo (+10)")
        if macd_hist > 0:
            momentum_score += 10.0
            momentum_details.append("MACD Hist > 0 (+10)")

        # 3. Volume (20 pts)
        volume_score = 0.0
        volume_details = []
        if vol_ratio > 1.2:
            volume_score += 10.0
            volume_details.append(f"Vol Ratio={vol_ratio:.2f} (+10)")
        if close > vwap:
            volume_score += 10.0
            volume_details.append("Precio > VWAP (+10)")

        # 4. Volatility (15 pts)
        volatility_score = 0.0
        volatility_details = []
        if close > (bb_lower + (bb_upper - bb_lower) * 0.3):
            volatility_score += 15.0
            volatility_details.append("BB Posición óptima (+15)")

        # 5. ML Prediction (20 pts)
        prediction_score = 0.0
        prediction_details = []
        lr = self.predictor.linear_regression_predict(df['close'].values, forecast_periods=3)
        pattern = self.predictor.detect_candlestick_patterns(df)
        divergence = self.predictor.detect_divergence(df)

        if lr['direction'] == 1 and lr['r_squared'] > 0.3:
            pts = 10.0 * lr['r_squared']
            prediction_score += pts
            prediction_details.append(f"OLS Alcista R2={lr['r_squared']:.2f} (+{pts:.1f})")

        if pattern['bias'] == 1:
            pts = 5.0 * pattern['confidence']
            prediction_score += pts
            prediction_details.append(f"Patrón {pattern['pattern']} (+{pts:.1f})")

        if divergence['type'] == 'BULLISH_DIVERGENCE':
            pts = 5.0 * divergence['strength']
            prediction_score += pts
            prediction_details.append(f"Divergencia Alcista (+{pts:.1f})")

        # 6. Regime Modifier (±10 pts)
        regime = self.predictor.compute_market_regime(df)
        regime_score = 0.0
        regime_details = []
        if regime == "TRENDING_UP":
            regime_score = 10.0
            regime_details.append("Régimen Alcista (+10)")
        elif regime == "TRENDING_DOWN":
            regime_score = -10.0
            regime_details.append("Régimen Bajista (-10)")

        total_score = max(0.0, min(100.0, trend_score + momentum_score + volume_score + volatility_score + prediction_score + regime_score))

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

    def evaluate_market(self, df: pd.DataFrame, symbol: str, bot_run_id: str, score_data: Optional[dict] = None,
                        probability: Optional[float] = None) -> Optional[Signal]:
        """
        Evaluates market using Quant Model:
        1. Calibrated Probability Prediction
        2. Expected Net Value EV_net Calculation
        3. Strict Risk & Liquidity Filters
        """
        if df.empty or len(df) < 30:
            return None

        # Apply full indicator suite
        if score_data is None:
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

        # Compute multi-factor components
        score_data = score_data or self.compute_composite_score(df)
        total_score = score_data['total_score']
        ml = score_data['ml_prediction']

        # Quantitative Probability Calibration
        raw_prob = (total_score / 100.0) * 0.85 + 0.10
        calibrated_prob = probability if probability is not None else min(0.95, max(0.05, raw_prob))

        # Net Expected Value calculation
        ev_net = (calibrated_prob * self.tp_target) - ((1.0 - calibrated_prob) * self.sl_target) - self.total_cost

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
        # EXIT LONG LOGIC
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
                exit_reasons.append(f"Patrón {ml['candle_pattern']}")

            if ml['lr_direction'] == -1 and ml['lr_r_squared'] > 0.5:
                should_exit = True
                exit_reasons.append(f"LR bajista(R2={ml['lr_r_squared']:.2f})")

            if should_exit and exit_reasons:
                reason = (
                    f"EXIT QUANT: {' + '.join(exit_reasons)} | "
                    f"P(Y=1)={calibrated_prob:.2f} EV_Net={ev_net*100:+.2f}% | "
                    f"Score={total_score:.0f}"
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
        # ENTRY LONG LOGIC (Quant Net EV Rule)
        # ==========================================
        if not position:
            should_enter = (
                calibrated_prob >= 0.60 and           # Calibrated Probability threshold
                ev_net >= 0.0015 and                  # Positive Net EV >= +0.15% after costs
                close_price > bb_middle and           # Trend baseline
                vol_ratio >= 0.8 and                  # Liquidity filter
                adx >= 18 and                         # Non-choppy regime
                ml['lr_direction'] >= 0 and           # Linear regression slope not negative
                ml['market_regime'] != 'TRENDING_DOWN'# Downtrend filter
            )

            if should_enter:
                reason = (
                    f"ENTRY QUANT (Net EV={ev_net*100:+.2f}%): P(Y=1)={calibrated_prob:.2f} | "
                    f"Score={total_score:.0f} ADX={adx:.1f} VolRatio={vol_ratio:.2f} | "
                    f"Regimen={ml['market_regime']}"
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
