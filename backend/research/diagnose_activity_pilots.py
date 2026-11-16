"""Recompute pilot signals with causal multi-timeframe features from exported DB candles.

Historical decision quote volume/spread/rank are retained; historical BBO is unknown.
This is a diagnostic on previously inspected data, never a profitability certificate.
"""
import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
from app.services.activity_profiles import PILOT_PROFILES, PILOT_LIMITS, features, context, assess
from research.paper_replay import replay, BAR_MS, DAY_MS


def diagnose(data, profile):
    candles = pd.DataFrame(data['candles']).rename(columns={'at': 'timestamp'})
    contexts = pd.DataFrame(data['context_candles'])
    source = pd.DataFrame(data['decisions'])
    changed, missing = [], 0
    for symbol, rows in source.groupby('symbol'):
        raw = candles[candles.symbol == symbol].sort_values('timestamp')
        f = features(raw).rename(columns={'timestamp': 'candle_at', 'close': 'feature_price'})
        f['history_count'] = range(1, len(f)+1)
        merged = rows.merge(f.drop(columns='symbol'), on='candle_at', how='left', validate='many_to_one').sort_values('at')
        for tf, minutes, prefix in [('1h',60,'h'), ('4h',240,'f')]:
            history = contexts[(contexts.symbol == symbol) & (contexts.timeframe == tf)].sort_values('timestamp')
            values = context(history)
            values['available_at'] = values['timestamp'] + minutes * 60_000
            values = values.rename(columns={k:prefix+'_'+k for k in ['timestamp','close','ema20','ema50']})
            merged = pd.merge_asof(merged, values, left_on='at', right_on='available_at', direction='backward',
                                   tolerance=2*minutes*60_000, suffixes=('', '_'+prefix))
        for row in merged.to_dict('records'):
            try:
                if row['history_count'] < 100:
                    raise ValueError('Insufficient warmup')
                # Spread levels are reconstructed solely for the spread filter, not BBO fills.
                spread = row['spread_pct']
                ticker = {'bid': 100., 'ask': 100.*(1+spread/100), 'quote_volume': row['quote_volume']}
                frame = {**row, 'close': row['feature_price']}
                h = {k:row['h_'+k] for k in ('close','ema20','ema50')}
                four = {k:row['f_'+k] for k in ('close','ema20','ema50')}
                d = assess(profile, frame, h, four, ticker, row['rank'])
                changed.append({k:row[k] for k in ('symbol','at','candle_at','price','spread_pct','rank')}
                               | {'eligible':d['eligible'], 'regime':d['checks']['trend_1h_4h'],
                                  'stop_pct':d['stop_loss_pct'], 'target_pct':d['take_profit_pct']})
            except (ValueError, TypeError, KeyError):
                missing += 1
    candidate = {**data, 'profile':profile, 'decisions':changed}
    split = int((data['start']+(data['end']-data['start'])*.7)//BAR_MS*BAR_MS)
    policy = {**PILOT_LIMITS, **PILOT_PROFILES[profile]}
    results = {'development':replay(candidate, start=data['start'], end=split-DAY_MS, experiment_policy=policy),
               'diagnostic_final':replay(candidate, start=split, end=data['end'], experiment_policy=policy),
               'stress_final':replay(candidate, start=split, end=data['end'], experiment_policy=policy, cost_multiplier=2)}
    return {'profile':profile, 'source_run':data['source_run'], 'source_decisions':len(source),
            'source_eligible':sum(d['eligible'] for d in data['decisions']),
            'pilot_eligible':sum(d['eligible'] for d in changed), 'missing_feature_rows':missing,
            'policy':policy, 'results':results,
            'data_sha256':hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            'profitability_validated':False, 'real_money_allowed':False,
            'limitations':['previously inspected data','estimated books and current rules','next 15m open execution model',
                           'EMA warmup may differ from a rolling live window; not an exact historical execution replay']}


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('dataset');parser.add_argument('profile',choices=PILOT_PROFILES)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    with open(args.dataset,encoding='utf-8') as f: data=json.load(f)
    report=diagnose(data,args.profile)
    with open(args.output,'w',encoding='utf-8') as f: json.dump(report,f,indent=2,allow_nan=False)
    print(json.dumps({k:v for k,v in report.items() if k!='results'}))
    for label,r in report['results'].items():print(label,{k:r[k] for k in ['closed_trades','net_pnl','profit_factor','max_drawdown_pct']})
