from typing import Dict, Any, List
import pandas as pd

class ScannerService:
    """
    Ultra-Fast Multi-Market Pattern Scanner & Anomaly Detector.
    Scans 50+ markets simultaneously to score momentum, volume spikes, and statistical anomalies.
    """

    @staticmethod
    def scan_tickers(tickers: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        scanned = []
        for symbol, t in tickers.items():
            last = t.get('last', 0.0)
            change = t.get('change_pct', 0.0)
            vol = t.get('quote_volume', 0.0)
            high = t.get('high', last)
            low = t.get('low', last)

            # Calculate Price Spread Range %
            spread_range = ((high - low) / low * 100.0) if low > 0 else 0.0
            
            # Anomaly Score Calculation (0 to 100)
            # High 24h change + High volatility range + Liquid Volume
            momentum_factor = min(abs(change) * 4.0, 40.0)
            volatility_factor = min(spread_range * 3.0, 30.0)
            liquidity_factor = 30.0 if vol > 10000000 else (vol / 10000000.0 * 30.0)
            
            anomaly_score = round(momentum_factor + volatility_factor + liquidity_factor, 1)

            # Signal opportunity tagging
            pattern_tag = "NEUTRAL"
            if change >= 3.0 and spread_range >= 5.0:
                pattern_tag = "BULLISH_BREAKOUT"
            elif change <= -3.0 and spread_range >= 5.0:
                pattern_tag = "BEARISH_PANIC"
            elif spread_range >= 8.0:
                pattern_tag = "HIGH_VOLATILITY"

            scanned.append({
                "symbol": symbol,
                "price": last,
                "change_pct": round(change, 2),
                "volume_24h": round(vol, 2),
                "spread_range_pct": round(spread_range, 2),
                "anomaly_score": anomaly_score,
                "pattern_tag": pattern_tag,
                "high": high,
                "low": low,
            })

        # Sort by opportunity anomaly score descending
        scanned.sort(key=lambda x: x["anomaly_score"], reverse=True)
        return scanned
