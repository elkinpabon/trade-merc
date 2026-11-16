"""Read-only operational audit. Never imports create_app or writes trading data.

Run with the database's DB_* environment variables. Outputs aggregates, not secrets.
"""
import collections
import json
import os
from datetime import datetime, timezone
from urllib.parse import unquote, urlsplit

import pymysql


def audit(connection):
    def rows(sql, args=()):
        if not sql.lstrip().upper().startswith('SELECT '):
            raise ValueError('The audit permits SELECT queries only')
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(sql, args)
            return cursor.fetchall()

    runs = rows("SELECT id, status, config_id, started_at, finished_at FROM strategy_runs WHERE run_type='EXPERIMENT' ORDER BY started_at DESC LIMIT 1")
    if not runs:
        return {'error': 'No experiment'}
    run = runs[0]
    end = run['finished_at'] or datetime.now(timezone.utc).replace(tzinfo=None)
    bounds = (run['started_at'], end)
    evaluations = rows('SELECT symbol, action, features_json FROM strategy_evaluations WHERE created_at BETWEEN %s AND %s ORDER BY created_at', bounds)
    passed, combinations, setups = collections.Counter(), collections.Counter(), []
    setup_failures = collections.Counter()
    for evaluation in evaluations:
        decision = json.loads(evaluation['features_json'] or '{}').get('opportunity', {})
        checks = decision.get('checks', {})
        passed.update(k for k, v in checks.items() if v)
        combinations[','.join(sorted(k for k, v in checks.items() if not v))] += 1
        if checks.get('setup'):
            setup_failures.update(k for k, v in checks.items() if not v)
            setups.append({'symbol': evaluation['symbol'], **decision})
    trades = rows('SELECT symbol, entry_price, exit_price, quantity, realized_pnl, realized_pnl_pct, total_fee, exit_reason, opened_at, closed_at FROM trades WHERE strategy_run_id=%s ORDER BY closed_at', (run['id'],))
    cycles = rows("SELECT status, error_message, COUNT(*) AS count, MIN(started_at) AS first_at, MAX(started_at) AS last_at FROM worker_cycles WHERE strategy_run_id=%s GROUP BY status,error_message ORDER BY count DESC LIMIT 25", (run['id'],))
    signals = rows('SELECT action,status,reason,COUNT(*) AS count FROM signals WHERE timestamp BETWEEN %s AND %s GROUP BY action,status,reason ORDER BY count DESC LIMIT 20', bounds)
    risks = rows('SELECT event_type,COUNT(*) AS count FROM risk_events WHERE timestamp BETWEEN %s AND %s GROUP BY event_type ORDER BY count DESC', bounds)
    positions = rows('SELECT symbol, quantity, entry_price, stop_loss_price, take_profit_price, strategy_run_id FROM paper_positions WHERE is_open=1')
    return {'run': run, 'evaluations': len(evaluations), 'checks_passed': passed,
            'failed_combinations': combinations.most_common(20), 'setups': setups[:5],
            'setup_failures': setup_failures,
            'setup_count': len(setups), 'trades': trades, 'cycles': cycles,
            'signals': signals, 'risk_counts': risks, 'open_positions': positions}


if __name__ == '__main__':
    url = urlsplit(os.environ.get('DATABASE_URL', ''))
    host = url.hostname or os.environ['DB_HOST']
    connection = pymysql.connect(
        host=host, port=url.port or int(os.environ.get('DB_PORT', '3306')),
        user=unquote(url.username) if url.username else os.environ['DB_USER'],
        password=unquote(url.password) if url.password else os.environ['DB_PASSWORD'],
        database=url.path.lstrip('/') if url.path else os.environ['DB_NAME'], connect_timeout=20, read_timeout=90,
        **({'ssl': {'check_hostname': True}} if 'tidbcloud.com' in host else {}),
    )
    try:
        print(json.dumps(audit(connection), default=str))
    finally:
        connection.rollback()
        connection.close()
