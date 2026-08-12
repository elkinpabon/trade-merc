import ccxt
import requests
import pandas as pd
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.extensions import db
from app.models import Candle

class MarketDataService:
    """
    Ultra-Fast Public Market Data Ingestion Service.
    Uses Direct Binance REST APIs for sub-150ms candle fetching and batch tickers.
    """

    def __init__(self, exchange_id: str = "binance"):
        self.exchange_id = exchange_id
        exchange_class = getattr(ccxt, exchange_id)
        self.client = exchange_class({
            'enableRateLimit': True,
            'timeout': 5000,
        })

    def fetch_all_tickers(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Batch fetches real-time tickers for symbols in a single call."""
        try:
            raw_tickers = self.client.fetch_tickers(symbols)
            parsed_tickers = {}
            
            for sym, t in raw_tickers.items():
                if not t:
                    continue
                last_price = float(t.get('last') or t.get('close') or 0.0)
                change_pct = float(t.get('percentage') or 0.0)
                vol = float(t.get('baseVolume') or 0.0)
                quote_vol = float(t.get('quoteVolume') or 0.0)
                high = float(t.get('high') or last_price)
                low = float(t.get('low') or last_price)
                
                parsed_tickers[sym] = {
                    "symbol": sym,
                    "last": last_price,
                    "bid": float(t.get('bid') or last_price),
                    "ask": float(t.get('ask') or last_price),
                    "high": high,
                    "low": low,
                    "volume": vol,
                    "quote_volume": quote_vol,
                    "change_pct": change_pct,
                    "timestamp": int(t.get('timestamp') or 0)
                }
            return parsed_tickers
        except Exception as e:
            print(f"Warning: Batch ticker fetch failed: {e}")
            return {}

    def fetch_public_ohlcv(self, symbol: str, timeframe: str = '5m', limit: int = 100) -> List[Dict[str, Any]]:
        """
        Ultra-Fast direct OHLCV fetching via Binance REST API (<150ms).
        Fallback to CCXT if direct REST call fails.
        """
        clean_symbol = symbol.replace('/', '').replace('%2F', '').replace('%2f', '').upper()
        if not clean_symbol.endswith('USDT'):
            clean_symbol = f"{clean_symbol}USDT"

        url = f"https://api.binance.com/api/v3/klines?symbol={clean_symbol}&interval={timeframe}&limit={limit}"

        try:
            resp = requests.get(url, timeout=3, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                data = resp.json()
                parsed_candles = []
                for c in data:
                    ts_ms = int(c[0])
                    dt = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).replace(tzinfo=None)
                    parsed_candles.append({
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "timestamp": ts_ms,
                        "datetime": dt.isoformat(),
                        "open": float(c[1]),
                        "high": float(c[2]),
                        "low": float(c[3]),
                        "close": float(c[4]),
                        "volume": float(c[5])
                    })
                if parsed_candles:
                    return parsed_candles
        except Exception as err:
            print(f"Direct Binance REST candles failed ({clean_symbol}), falling back to CCXT: {err}")

        # Fallback CCXT
        try:
            raw_candles = self.client.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            parsed_candles = []
            for c in raw_candles:
                ts_ms = int(c[0])
                dt = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).replace(tzinfo=None)
                parsed_candles.append({
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "timestamp": ts_ms,
                    "datetime": dt.isoformat(),
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4]),
                    "volume": float(c[5])
                })
            return parsed_candles
        except Exception as e:
            print(f"CCXT OHLCV error: {e}")
            return []

    def get_ohlcv_dataframe(self, symbol: str, timeframe: str = '5m', limit: int = 100) -> pd.DataFrame:
        """Returns OHLCV candles as Pandas DataFrame for indicator calculations."""
        candles = self.fetch_public_ohlcv(symbol, timeframe, limit)
        if not candles:
            return pd.DataFrame()
        df = pd.DataFrame(candles)
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
