"""SELECT-only export for a diagnostic replay; no app startup, schema changes or secrets in output."""
import base64
import gzip
import json
import os
from datetime import timezone
from urllib.parse import unquote, urlsplit

import pymysql


def millis(value):
    return int(value.replace(tzinfo=timezone.utc).timestamp() * 1000)


def dataset(connection):
    def query(sql, args=()):
        if not sql.startswith('SELECT '):
            raise ValueError('SELECT only')
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(sql, args)
            return cursor.fetchall()
    run = query("SELECT * FROM strategy_runs WHERE run_type='EXPERIMENT' ORDER BY started_at DESC LIMIT 1")[0]
    end = run['finished_at'] or run['planned_end_at']
    if not run['finished_at']:
        raise ValueError('Export only completed A/B experiments')
    config = json.loads(run['config_snapshot_json'])
    decisions = []
    for row in query('SELECT symbol,decision_candle_ts,created_at,entry_price,features_json FROM strategy_evaluations '
                     'WHERE model_version_id=%s AND created_at BETWEEN %s AND %s ORDER BY created_at,symbol',
                     (run['model_version_id'], run['started_at'], end)):
        d = json.loads(row['features_json']).get('opportunity')
        if not d:
            continue
        decisions.append({'symbol': row['symbol'], 'at': millis(row['created_at']),
                          'candle_at': row['decision_candle_ts'], 'price': float(row['entry_price']),
                          'eligible': bool(d['eligible']), 'regime': bool(d['checks']['trend_1h_4h']),
                          'stop_pct': d['stop_loss_pct'], 'target_pct': d['take_profit_pct'],
                          'spread_pct': d['spread_pct'], 'rank': d['relative_rank']})
    symbols = config['symbols'].split(',')
    placeholders = ','.join(['%s'] * len(symbols))
    bars = query('SELECT symbol,timestamp,open,high,low,close FROM candles WHERE timeframe=%s AND '
                 f'symbol IN ({placeholders}) AND timestamp >= %s AND timestamp + 900000 <= %s ORDER BY timestamp,symbol',
                 ('15m', *symbols, millis(run['started_at']) // 900000 * 900000, millis(end)))
    rules = query(f'SELECT symbol,min_notional,min_qty,qty_precision FROM symbol_rules WHERE symbol IN ({placeholders})', symbols)
    return {'schema': 1, 'source_run': run['id'], 'profile': config['strategy_key'],
            'start': millis(run['started_at']), 'end': millis(end),
            'previously_inspected': True, 'historical_books_available': False,
            'historical_rule_snapshots_available': False,
            'decisions': decisions,
            'candles': [{'symbol': b['symbol'], 'at': int(b['timestamp']),
                         **{k: float(b[k]) for k in ('open', 'high', 'low', 'close')}} for b in bars],
            'rules': {r['symbol']: {k: float(r[k]) for k in ('min_notional', 'min_qty', 'qty_precision')} for r in rules}}


if __name__ == '__main__':
    u = urlsplit(os.environ['DATABASE_URL'])
    connection = pymysql.connect(host=u.hostname, port=u.port or 3306, user=unquote(u.username),
                                 password=unquote(u.password), database=u.path.lstrip('/'),
                                 connect_timeout=20, read_timeout=120,
                                 **({'ssl': {'check_hostname': True}} if 'tidbcloud.com' in u.hostname else {}))
    try:
        payload = json.dumps(dataset(connection), separators=(',', ':'), allow_nan=False).encode()
        print('REPLAY_DATA_BEGIN')
        print(base64.b64encode(gzip.compress(payload)).decode())
        print('REPLAY_DATA_END')
    finally:
        connection.rollback()
        connection.close()
