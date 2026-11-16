"""Causal diagnostic replay of SAVED decisions, not a strategy optimizer or live broker.

Unknown historical books/rules and previously inspected data prohibit activation.
Entries use the NEXT bar open after decision availability, not the signal close.
"""
import argparse
import hashlib
import json
import math
from collections import defaultdict
from decimal import Decimal, ROUND_DOWN

BAR_MS = 900_000
DAY_MS = 86_400_000
VARIANTS = ('baseline', 'protected-v1')


def replay(data, variant='baseline', start=None, end=None, cost_multiplier=1., experiment_policy=None):
    if variant not in VARIANTS or cost_multiplier < 1:
        raise ValueError('Unknown variant or optimistic cost multiplier')
    start, end = start or data['start'], end or data['end']
    if start >= end:
        raise ValueError('Invalid replay period')
    fee, slip = .001 * cost_multiplier, .0005 * cost_multiplier
    cash, peak, drawdown = 100., 100., 0.
    positions, cooldown, regimes = {}, {}, {}
    trades, entries, gaps = [], [], 0
    blocks = defaultdict(int)
    decisions = sorted(data['decisions'], key=lambda d: (d['at'], d['symbol']))
    policy = experiment_policy or {}
    cooldown_ms = int(policy.get('cooldown_seconds', 14400) * 1000)
    hold_ms = int(policy.get('max_hold_minutes', 1440 if variant == 'protected-v1' else 0) * 60_000)
    day_key, day_equity, day_entries = None, 100., 0
    index = 0
    bars = defaultdict(dict)
    for b in data['candles']:
        if start <= b['at'] and b['at'] + BAR_MS <= end:
            if b['symbol'] in bars[b['at']]:
                raise ValueError('Duplicate candle')
            values = [b[k] for k in ('open', 'high', 'low', 'close')]
            if (not all(math.isfinite(v) and v > 0 for v in values)
                    or b['low'] > min(b['open'], b['close']) or b['high'] < max(b['open'], b['close'])
                    or b['low'] > b['high']):
                raise ValueError('Invalid candle')
            bars[b['at']][b['symbol']] = b

    def close(symbol, price, timestamp, reason):
        nonlocal cash
        p = positions.pop(symbol)
        fill = price * (1 - p['spread'] / 2) * (1 - slip)
        exit_fee = p['qty'] * fill * fee
        cash += p['qty'] * fill - exit_fee
        trades.append({'symbol': symbol, 'opened_at': p['at'], 'closed_at': timestamp,
                       'pnl': p['qty'] * (fill - p['entry']) - p['entry_fee'] - exit_fee,
                       'fees': p['entry_fee'] + exit_fee, 'reason': reason})
        cooldown[symbol] = timestamp + cooldown_ms

    for timestamp, market in sorted(bars.items()):
        if timestamp // DAY_MS != day_key:
            day_key = timestamp // DAY_MS
            day_equity = cash + sum(p['qty']*p['mark'] for p in positions.values())
            day_entries = 0
        ready = []
        while index < len(decisions) and decisions[index]['at'] <= timestamp:
            d = decisions[index]
            index += 1
            if d['at'] < d['candle_at'] + BAR_MS:
                raise ValueError('Decision contains an unclosed feature candle')
            regimes[d['symbol']] = (d['at'], d['regime'])
            # Never use a decision made after this bar's open, or carry an old entry forward.
            if d['eligible'] and start <= d['at'] and timestamp - d['at'] < BAR_MS:
                ready.append(d)
        for symbol in list(positions):
            if symbol not in market:
                gaps += 1
                continue
            p, b = positions[symbol], market[symbol]
            if policy:
                p['mark'] = b['open']  # observable at entry time, not this bar's future close
            if timestamp - p['last_bar'] != BAR_MS:
                gaps += 1
            regime_at, regime = regimes.get(symbol, (0, True))
            if not regime and timestamp - regime_at <= 2 * BAR_MS:
                close(symbol, b['open'], timestamp, 'REGIME')
            elif hold_ms and timestamp - p['at'] >= hold_ms:
                close(symbol, b['open'], timestamp, 'TIMEOUT')
        for d in sorted(ready, key=lambda d: (d['rank'], d['symbol'])):
            symbol = d['symbol']
            if symbol not in market or symbol in positions or len(positions) >= 2 or timestamp < cooldown.get(symbol, 0):
                blocks['portfolio_or_cooldown'] += 1
                continue
            marked = cash + sum(p['qty']*p['mark'] for p in positions.values())
            if policy and (day_entries >= policy['max_entries_per_day']
                           or marked <= day_equity*(1-policy['daily_loss_pct']/100)
                           or marked <= peak*(1-policy['max_drawdown_pct']/100)):
                blocks['pilot_risk_limits'] += 1
                continue
            if variant == 'protected-v1':
                bt, bullish = regimes.get('BTC/USDT', (0, False))
                if not bullish or timestamp - bt > 2 * BAR_MS:
                    blocks['benchmark_regime'] += 1
                    continue
            rule, spread = data['rules'].get(symbol), d.get('spread_pct')
            if not rule or spread is None or not math.isfinite(spread) or not 0 <= spread <= .10:
                blocks['rules_or_spread'] += 1
                continue
            b = market[symbol]
            if (variant == 'protected-v1' or policy) and abs(b['open'] / d['price'] - 1) > .003:
                blocks['entry_drift'] += 1
                continue
            entry = b['open'] * (1 + spread / 200) * (1 + slip)
            risk = float(d['stop_pct']) / 100
            target_pct = float(d['target_pct']) / 100
            if not all(math.isfinite(v) and v > 0 for v in (entry, risk, target_pct)):
                raise ValueError('Invalid decision barriers')
            equity = cash + sum(p['qty'] * p['mark'] for p in positions.values())
            step = Decimal(1).scaleb(-int(rule['qty_precision']))
            raw = min(equity * .0025 / (entry * (risk + 2 * fee + 2 * slip + spread / 100)),
                      equity * .20 / entry, cash / (entry * (1 + fee)))
            qty = float(Decimal(str(raw)).quantize(step, rounding=ROUND_DOWN))
            if qty < rule['min_qty'] or qty * entry < rule['min_notional']:
                blocks['minimum_order'] += 1
                continue
            entry_fee = qty * entry * fee
            cash -= qty * entry + entry_fee
            day_entries += 1
            positions[symbol] = {'qty': qty, 'entry': entry, 'entry_fee': entry_fee,
                                 'spread': spread / 100, 'stop': entry * (1 - risk),
                                 'target': entry * (1 + target_pct), 'initial_risk': entry * risk,
                                 'at': timestamp, 'mark': entry, 'last_bar': timestamp - BAR_MS}
            entries.append({'symbol': symbol, 'decision_at': d['at'], 'entry_at': timestamp,
                            'entry_price': entry, 'quantity': qty, 'equity': equity})
        for symbol in list(positions):
            if symbol not in market:
                continue
            p, b = positions[symbol], market[symbol]
            # STOP_FIRST: never claim the favorable ordering of intrabar extremes.
            if b['open'] <= p['stop']:
                close(symbol, b['open'], timestamp, 'STOP_GAP')
            elif b['low'] <= p['stop']:
                close(symbol, p['stop'], timestamp + BAR_MS, 'STOP')
            elif b['high'] >= p['target']:
                close(symbol, p['target'], timestamp + BAR_MS, 'TARGET')
            else:
                p['mark'], p['last_bar'] = b['close'], timestamp
                if (variant == 'protected-v1' or policy) and b['high'] >= p['entry'] + p['initial_risk']:
                    # New trail becomes effective NEXT bar; no lookahead fill on this bar.
                    break_even = (p['entry'] + p['entry_fee'] / p['qty']) / ((1 - fee) * (1 - slip) * (1 - p['spread'] / 2))
                    p['stop'] = max(p['stop'], break_even) if policy else max(p['stop'], break_even, b['high'] - p['initial_risk'])
        equity = cash + sum(p['qty'] * p['mark'] for p in positions.values())
        peak = max(peak, equity)
        drawdown = max(drawdown, (peak - equity) / peak * 100)
    for symbol in list(positions):
        close(symbol, positions[symbol]['mark'], end, 'END_OF_WINDOW')
    peak = max(peak, cash)
    drawdown = max(drawdown, (peak - cash) / peak * 100)
    profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
    loss = -sum(t['pnl'] for t in trades if t['pnl'] < 0)
    net = sum(t['pnl'] for t in trades)
    if abs(cash - 100 - net) > 1e-7:
        raise AssertionError('Cash/PnL reconciliation failed')
    return {'variant': variant, 'start': start, 'end': end, 'closed_trades': len(trades),
            'net_pnl': net, 'final_equity': cash, 'fees': sum(t['fees'] for t in trades),
            'profit_factor': profit / loss if loss else None, 'max_drawdown_pct': drawdown,
            'data_gaps_while_holding': gaps, 'blocks': dict(blocks), 'trades': trades, 'entries': entries}


def validate(data):
    """Predeclared diagnostic split, one candidate only; never automatically starts trading."""
    start, end = data['start'], data['end']
    split = int((start + (end - start) * .7) // BAR_MS * BAR_MS)
    train_end = split - DAY_MS  # purge the candidate's maximum holding horizon
    if train_end <= start:
        raise ValueError('Insufficient period for chronological split and 24h purge')
    results = {}
    for variant in VARIANTS:
        results[variant] = {'development': replay(data, variant, start, train_end),
                            'diagnostic_holdout': replay(data, variant, split, end),
                            'stress_holdout': replay(data, variant, split, end, cost_multiplier=2.)}
    candidate, baseline = results['protected-v1'], results['baseline']
    test, stress = candidate['diagnostic_holdout'], candidate['stress_holdout']
    criteria = {
        'at_least_100_holdout_trades': test['closed_trades'] >= 100,
        'holdout_net_positive': test['net_pnl'] > 0,
        'holdout_pf_at_least_1_2': test['profit_factor'] is not None and test['profit_factor'] >= 1.2,
        'holdout_drawdown_at_most_5_pct': test['max_drawdown_pct'] <= 5,
        'stress_net_positive': stress['net_pnl'] > 0,
        'outperforms_baseline_holdout': test['net_pnl'] > baseline['diagnostic_holdout']['net_pnl'],
        'no_held_data_gaps': test['data_gaps_while_holding'] == 0,
        'uninspected_out_of_sample': data.get('previously_inspected') is False,
        'point_in_time_books_and_rules': bool(data.get('historical_books_available') and data.get('historical_rule_snapshots_available')),
        'prospective_validation_complete': False,
    }
    fingerprint = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    return {'source_run': data['source_run'], 'profile': data['profile'], 'data_sha256': fingerprint,
            'model': 'next-15m-open; saved closed-candle decisions; STOP_FIRST; current rules; spread estimate',
            'split_at': split, 'purge_ms': DAY_MS, 'results': results,
            'activation': {'allowed': all(criteria.values()), 'criteria': criteria},
            'warning': 'Previously inspected data and estimated historical execution: diagnostic only, not a verified edge.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    with open(args.input, encoding='utf-8') as f:
        report = validate(json.load(f))
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, allow_nan=False)
    print(json.dumps({'profile': report['profile'], 'activation': report['activation'], 'output': args.output}))
