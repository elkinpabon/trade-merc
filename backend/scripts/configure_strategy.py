"""Configure an isolated, flat paper account; never mutates an active experiment."""
import argparse
import json
import os
import sys

import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app
from app.extensions import db
from app.models import BotConfig, BotRun, PaperPosition, StrategyRun, SymbolRule
from app.services.model_service import ModelService
from app.services.opportunity_service import PROFILES
from app.utils.helpers import generate_uuid, utc_now


def discover():
    response = requests.get('https://data-api.binance.vision/api/v3/exchangeInfo', timeout=30)
    response.raise_for_status()
    excluded = {'USDC', 'FDUSD', 'TUSD', 'DAI', 'USDP', 'USDE', 'USD1', 'EUR', 'WBTC', 'WBETH', 'PAXG', 'XAUT', 'USDS', 'USDG', 'USDD', 'USDF'}
    allowed = {row['symbol']: row['baseAsset'] + '/USDT' for row in response.json()['symbols']
               if row['quoteAsset'] == 'USDT' and row['status'] == 'TRADING'
               and row.get('isSpotTradingAllowed') and row['baseAsset'] not in excluded
               and not row['baseAsset'].endswith('USD')
               and not row['baseAsset'].endswith(('UP', 'DOWN', 'BULL', 'BEAR'))}
    response = requests.get('https://data-api.binance.vision/api/v3/ticker/24hr', timeout=30)
    response.raise_for_status()
    rows = sorted((row for row in response.json() if row['symbol'] in allowed
                   and float(row['quoteVolume']) >= 20_000_000),
                  key=lambda row: (-float(row['quoteVolume']), row['symbol']))
    if len(rows) < 20:
        raise RuntimeError('Not enough liquid spot markets')
    selected = []
    for row in rows:
        history = requests.get('https://data-api.binance.vision/api/v3/klines',
                               params={'symbol': row['symbol'], 'interval': '4h', 'limit': 201}, timeout=15)
        history.raise_for_status()
        if len(history.json()) >= 201:
            selected.append(allowed[row['symbol']])
        if len(selected) == 20:
            return selected
    raise RuntimeError('Not enough liquid markets with at least 200 closed 4h candles')


def sync_rules(symbols):
    from decimal import Decimal
    response = requests.get('https://data-api.binance.vision/api/v3/exchangeInfo', timeout=30)
    response.raise_for_status()
    markets = {row['symbol']: row for row in response.json()['symbols']}
    for symbol in symbols:
        market = markets[symbol.replace('/', '')]
        if market['status'] != 'TRADING' or not market.get('isSpotTradingAllowed'):
            raise ValueError(f'Inactive spot market: {symbol}')
        filters = {row['filterType']: row for row in market['filters']}
        lot, price = filters['LOT_SIZE'], filters['PRICE_FILTER']
        notional = filters.get('NOTIONAL', filters.get('MIN_NOTIONAL', {}))
        rule = SymbolRule.query.filter_by(symbol=symbol).first()
        if not rule:
            rule = SymbolRule(symbol=symbol)
            db.session.add(rule)
        rule.min_notional = float(notional.get('minNotional', 10))
        rule.min_qty = float(lot['minQty'])
        rule.qty_precision = max(0, -Decimal(lot['stepSize']).normalize().as_tuple().exponent)
        rule.price_precision = max(0, -Decimal(price['tickSize']).normalize().as_tuple().exponent)
        rule.tick_size = float(price['tickSize'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('profile', choices=PROFILES)
    parser.add_argument('--symbols', help='Frozen comma-separated universe; otherwise discover top 20 by volume')
    args = parser.parse_args()
    app = create_app()
    with app.app_context():
        if PaperPosition.query.filter_by(is_open=True).count() or StrategyRun.query.filter_by(run_type='EXPERIMENT', status='RUNNING').count():
            raise SystemExit('Account must be flat and no experiment may be RUNNING')
        # Keep every completed experiment's config untouched for historical reports.
        config = BotConfig()
        db.session.add(config)
        config.strategy_key = args.profile
        config.name = args.profile
        config.symbols = args.symbols or ','.join(discover())
        sync_rules(config.symbols.split(','))
        config.mode, config.timeframe, config.virtual_balance = 'paper', '15m', 100.0
        config.risk_per_trade_pct, config.stop_loss_pct, config.take_profit_pct = 0.25, 2.0, 4.0
        config.fee_pct, config.slippage_pct = 0.10, 0.05
        config.cooldown_seconds, config.candle_limit = 14400, 200
        config.polling_interval_seconds, config.is_active = 900, True
        db.session.flush()
        config.model_version_id = ModelService.for_config(config).id
        # A new bot run gives each experiment an independent attribution namespace.
        for run in BotRun.query.filter_by(status='running').all():
            run.status, run.stopped_at = 'stopped', utc_now()
        db.session.add(BotRun(id=generate_uuid(), config_id=config.id, status='running', started_at=utc_now()))
        db.session.commit()
        print(json.dumps(config.to_dict(), default=str))


if __name__ == '__main__':
    main()
