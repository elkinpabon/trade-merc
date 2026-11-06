import threading
import time
from decimal import Decimal

import httpx

from .store import now_ms
from .strategy import quote_valid, spread_pct, POLICY

BASE = 'https://data-api.binance.vision/api/v3'
EXCLUDED = {'USDC', 'FDUSD', 'TUSD', 'DAI', 'USDP', 'USDE', 'USD1', 'USDS', 'USDG', 'USDD',
            'WBTC', 'WBETH', 'PAXG', 'XAUT', 'EUR', 'EURI', 'AEUR', 'BRL', 'TRY', 'ARS', 'UAH', 'RUB'}


class Market:
    def __init__(self):
        self.client = httpx.Client(timeout=httpx.Timeout(12, connect=5), limits=httpx.Limits(max_connections=6))
        self.lock = threading.RLock()
        self.rules, self.quotes = {}, {}
        self.blocked_until = 0.0
        self.universe_at = self.volume_at = 0

    def request(self, route, **params):
        if time.monotonic() < self.blocked_until:
            raise RuntimeError('Binance solicita espera; backoff activo')
        response = self.client.get(BASE + route, params=params, headers={'User-Agent': 'Pulse-paper-research/1.0'})
        if response.status_code in (418, 429):
            try:
                delay = float(response.headers.get('Retry-After', 60))
            except ValueError:
                delay = 60
            self.blocked_until = time.monotonic() + max(60, delay)
        response.raise_for_status()
        return response.json()

    def discover(self):
        data = self.request('/exchangeInfo')
        found = {}
        spot_count = 0
        for m in data['symbols']:
            if m['status'] != 'TRADING' or m['quoteAsset'] != 'USDT' or not m.get('isSpotTradingAllowed'):
                continue
            spot_count += 1
            base = m['baseAsset']
            if base in EXCLUDED or base.endswith(('USD', 'BULL', 'BEAR', 'UP', 'DOWN')):
                continue
            filters = {f['filterType']: f for f in m['filters']}
            lot, market_lot = filters.get('LOT_SIZE', {}), filters.get('MARKET_LOT_SIZE', {})
            step = Decimal(lot.get('stepSize', '0'))
            if step <= 0:
                continue
            market_step = Decimal(market_lot.get('stepSize', '0'))
            if market_step > 0:
                largest, smallest = max(step, market_step), min(step, market_step)
                if largest % smallest:
                    continue  # unsupported incompatible grids; fail closed
                step = largest
            minimum = max(Decimal(lot.get('minQty', '0')), Decimal(market_lot.get('minQty', '0')))
            maximums = [Decimal(x) for x in [lot.get('maxQty', '0'), market_lot.get('maxQty', '0')] if Decimal(x) > 0]
            if not maximums:
                continue
            n = filters.get('NOTIONAL', filters.get('MIN_NOTIONAL', {}))
            found[m['symbol']] = {'symbol': m['symbol'], 'base': base, 'step': str(step),
                                  'min_qty': str(minimum), 'max_qty': str(min(maximums)),
                                  'min_notional': n.get('minNotional', '5'),
                                  'max_notional': n.get('maxNotional', '1e30'),
                                  'tick': filters.get('PRICE_FILTER', {}).get('tickSize', '0'),
                                  'at': now_ms()}
        if not found:
            raise RuntimeError('Binance devolvió un universo vacío')
        with self.lock:
            self.rules = found
            self.universe_at = now_ms()
        return {'at': self.universe_at, 'spot_usdt_total': spot_count, 'eligible_assets': len(found)}

    def refresh(self):
        at = now_ms()
        if at - self.volume_at > 120_000:
            volumes = self.request('/ticker/24hr', type='FULL')
            with self.lock:
                for t in volumes:
                    symbol = t['symbol']
                    if symbol in self.rules:
                        old = self.quotes.get(symbol, {})
                        self.quotes[symbol] = {**old, 'symbol': symbol, 'base': self.rules[symbol]['base'],
                                              'last': float(t['lastPrice']), 'change_pct': float(t['priceChangePercent']),
                                              'volume_usdt': float(t['quoteVolume']), 'trades_24h': int(t['count'])}
                self.volume_at = now_ms()
        books = self.request('/ticker/bookTicker')
        timestamp = now_ms()
        with self.lock:
            for t in books:
                if t['symbol'] in self.quotes:
                    self.quotes[t['symbol']].update(bid=float(t['bidPrice']), ask=float(t['askPrice']), at=timestamp)
        return timestamp

    def snapshot(self):
        with self.lock:
            return {k: dict(v) for k, v in self.quotes.items()}, {k: dict(v) for k, v in self.rules.items()}

    def candidates(self):
        quotes, rules = self.snapshot()
        at = now_ms()
        if at - self.universe_at > 86_400_000 or at - self.volume_at > 300_000:
            raise RuntimeError('Metadatos o volumen obsoletos; no se abren entradas')
        eligible = [q for q in quotes.values() if quote_valid(q) and at - q.get('at', 0) <= 45_000
                    and q.get('volume_usdt', 0) >= POLICY.min_volume_usdt
                    and spread_pct(q) <= POLICY.max_spread_pct]
        # Broad discovery, cheap prefilter; never claim deep analysis of every market.
        eligible.sort(key=lambda q: (-abs(q['change_pct']), -q['volume_usdt'], q['symbol']))
        return eligible[:POLICY.scan_limit], len(eligible)

    def candles(self, symbol):
        return self.request('/klines', symbol=symbol, interval='5m', limit=100)
