import ccxt
import json
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
        """Batch fetches public Binance tickers without loading exchange metadata."""
        try:
            requested = {symbol.replace('/', '').upper(): symbol for symbol in symbols}
            response = requests.get(
                'https://data-api.binance.vision/api/v3/ticker/24hr',
                params={'symbols': json.dumps(list(requested), separators=(',', ':'))}, timeout=5,
                headers={'User-Agent': 'TRADEMERC-paper-bot/1.0'},
            )
            response.raise_for_status()
            parsed_tickers = {}
            for ticker in response.json():
                symbol = requested.get(ticker.get('symbol', ''))
                if not symbol:
                    continue
                last_price = float(ticker.get('lastPrice') or 0.0)
                parsed_tickers[symbol] = {
                    'symbol': symbol,
                    'last': last_price,
                    'bid': float(ticker.get('bidPrice') or last_price),
                    'ask': float(ticker.get('askPrice') or last_price),
                    'high': float(ticker.get('highPrice') or last_price),
                    'low': float(ticker.get('lowPrice') or last_price),
                    'volume': float(ticker.get('volume') or 0.0),
                    'quote_volume': float(ticker.get('quoteVolume') or 0.0),
                    'change_pct': float(ticker.get('priceChangePercent') or 0.0),
                    'timestamp': int(ticker.get('closeTime') or 0),
                }
            return parsed_tickers
        except Exception as direct_error:
            print(f"Warning: Binance data API ticker fetch failed: {direct_error}")
        try:
            raw_tickers = self.client.fetch_tickers(symbols)
            return {
                symbol: {
                    'symbol': symbol,
                    'last': float(ticker.get('last') or ticker.get('close') or 0.0),
                    'bid': float(ticker.get('bid') or ticker.get('last') or 0.0),
                    'ask': float(ticker.get('ask') or ticker.get('last') or 0.0),
                    'high': float(ticker.get('high') or ticker.get('last') or 0.0),
                    'low': float(ticker.get('low') or ticker.get('last') or 0.0),
                    'volume': float(ticker.get('baseVolume') or 0.0),
                    'quote_volume': float(ticker.get('quoteVolume') or 0.0),
                    'change_pct': float(ticker.get('percentage') or 0.0),
                    'timestamp': int(ticker.get('timestamp') or 0),
                }
                for symbol, ticker in raw_tickers.items() if ticker
            }
        except Exception as ccxt_error:
            print(f"Warning: Batch ticker fetch failed: {ccxt_error}")
            return {}

    def fetch_public_ohlcv(self, symbol: str, timeframe: str = '5m', limit: int = 100) -> List[Dict[str, Any]]:
        """
        Ultra-Fast direct OHLCV fetching via Binance REST API (<150ms).
        Fallback to CCXT if direct REST call fails.
        """
        clean_symbol = symbol.replace('/', '').replace('%2F', '').replace('%2f', '').upper()
        if not clean_symbol.endswith('USDT'):
            clean_symbol = f"{clean_symbol}USDT"

        url = f"https://data-api.binance.vision/api/v3/klines?symbol={clean_symbol}&interval={timeframe}&limit={limit}"

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
        """Returns only closed OHLCV candles for reproducible decisions."""
        candles = self.fetch_public_ohlcv(symbol, timeframe, limit)
        if not candles:
            return pd.DataFrame()
        # The final exchange candle is still forming and must never be used as a feature or label.
        closed_candles = [{**candle, 'symbol': candle.get('symbol', symbol), 'timeframe': candle.get('timeframe', timeframe)} for candle in candles[:-1]]
        self.persist_closed_candles(closed_candles)
        df = pd.DataFrame(closed_candles)
        if df.empty:
            return df
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df

    @staticmethod
    def persist_closed_candles(candles: List[Dict[str, Any]]) -> None:
        """Upserts closed candles so research and labels use the same market data."""
        if not candles:
            return
        for candle in candles:
            existing = Candle.query.filter_by(
                symbol=candle['symbol'], timeframe=candle['timeframe'], timestamp=candle['timestamp']
            ).first()
            if existing:
                continue
            candle_datetime = candle.get('datetime') or datetime.fromtimestamp(candle['timestamp'] / 1000.0, tz=timezone.utc).replace(tzinfo=None)
            db.session.add(Candle(
                symbol=candle['symbol'], timeframe=candle['timeframe'], timestamp=candle['timestamp'],
                datetime=datetime.fromisoformat(candle_datetime) if isinstance(candle_datetime, str) else candle_datetime, open=candle['open'], high=candle['high'],
                low=candle['low'], close=candle['close'], volume=candle['volume'],
            ))
        db.session.commit()
