import unittest

from research.paper_replay import BAR_MS, DAY_MS, replay, validate


class CandleReplayTests(unittest.TestCase):
    def dataset(self, count=10):
        start = 10 * BAR_MS
        rule = {'min_notional': 5, 'min_qty': .001, 'qty_precision': 3}
        decisions = [{'symbol': s, 'at': start + 1, 'candle_at': start - BAR_MS,
                      'price': 100, 'eligible': s != 'BTC/USDT', 'regime': True,
                      'stop_pct': 1., 'target_pct': 2., 'spread_pct': .01, 'rank': i}
                     for i, s in enumerate(['BTC/USDT', 'ETH/USDT'])]
        return {'source_run': 'test', 'profile': 'trend-pullback-v2', 'start': start,
                'end': start + count * BAR_MS, 'previously_inspected': True,
                'historical_books_available': False, 'historical_rule_snapshots_available': False,
                'rules': {'ETH/USDT': rule}, 'decisions': decisions,
                'candles': [{'symbol': 'ETH/USDT', 'at': start + i * BAR_MS,
                             'open': 100., 'high': 100.2, 'low': 99.8, 'close': 100.}
                            for i in range(count)]}

    def test_entry_is_after_decision_available_and_not_signal_candle_extremes(self):
        data = self.dataset()
        data['candles'][0].update(high=1000., low=1.)
        result = replay(data)
        self.assertEqual(len(result['entries']), 1)
        e = result['entries'][0]
        self.assertGreater(e['entry_at'], e['decision_at'])
        self.assertEqual(e['entry_at'], data['start'] + BAR_MS)
        self.assertLess(e['entry_price'], 101)
        self.assertEqual(result['trades'][0]['reason'], 'END_OF_WINDOW')

    def test_stop_wins_when_both_barriers_cross_same_bar(self):
        data = self.dataset()
        data['candles'][1].update(high=105., low=95.)
        result = replay(data)
        self.assertEqual(result['trades'][0]['reason'], 'STOP')
        self.assertLess(result['net_pnl'], 0)

    def test_gap_stop_uses_adverse_open_not_fictitious_stop_price(self):
        data = self.dataset()
        data['candles'][2].update(open=95., high=95.2, low=94.8, close=95.)
        result = replay(data)
        self.assertEqual(result['trades'][0]['reason'], 'STOP_GAP')
        self.assertLess(result['net_pnl'], -.25)

    def test_fees_and_cash_reconcile_under_stressed_costs(self):
        data = self.dataset()
        normal, stress = replay(data), replay(data, cost_multiplier=2)
        self.assertAlmostEqual(normal['final_equity'], 100 + normal['net_pnl'], places=8)
        self.assertGreater(normal['fees'], 0)
        self.assertLess(stress['net_pnl'], normal['net_pnl'])

    def test_position_size_never_rounds_up_to_market_minimum(self):
        data = self.dataset()
        data['rules']['ETH/USDT']['min_notional'] = 30
        result = replay(data)
        self.assertEqual(result['closed_trades'], 0)
        self.assertGreater(result['blocks']['minimum_order'], 0)

    def test_candidate_never_uses_future_benchmark_regime(self):
        data = self.dataset()
        data['decisions'][0]['at'] = data['start'] + 2 * BAR_MS
        result = replay(data, 'protected-v1')
        self.assertEqual(len(result['entries']), 0)
        self.assertEqual(result['blocks']['benchmark_regime'], 1)

    def test_intrabar_trail_is_not_filled_retroactively(self):
        data = self.dataset()
        data['candles'][1].update(high=101.2, low=99.5, close=100.1)
        result = replay(data, 'protected-v1')
        self.assertGreaterEqual(result['trades'][0]['closed_at'], data['start'] + 2 * BAR_MS)

    def test_bad_ohlc_duplicate_or_unclosed_features_fail_closed(self):
        for kind in ['ohlc', 'duplicate', 'unclosed']:
            data = self.dataset()
            if kind == 'ohlc': data['candles'][0]['low'] = 102
            if kind == 'duplicate': data['candles'].append(dict(data['candles'][0]))
            if kind == 'unclosed': data['decisions'][1]['candle_at'] += BAR_MS
            with self.subTest(kind=kind), self.assertRaises(ValueError): replay(data)

    def test_validation_cannot_promote_inspected_data_or_missing_books(self):
        data = self.dataset(count=10 * DAY_MS // BAR_MS)
        report = validate(data)
        self.assertEqual(report['purge_ms'], DAY_MS)
        self.assertFalse(report['activation']['allowed'])
        self.assertFalse(report['activation']['criteria']['uninspected_out_of_sample'])
        self.assertFalse(report['activation']['criteria']['prospective_validation_complete'])
        self.assertEqual(len(report['data_sha256']), 64)
