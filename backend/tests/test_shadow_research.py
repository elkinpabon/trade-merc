import unittest

import pandas as pd

from app.services.shadow_research import benchmark_context, candidate_intent


class ShadowResearchTests(unittest.TestCase):
    def test_valid_intent_is_never_permission_to_submit_an_order(self):
        result = candidate_intent({'eligible': True, 'profile': 'trend-pullback-v2'},
                                  {'status': 'OK', 'bullish': True, 'observed_at': 100000},
                                  {'bid': 99.99, 'ask': 100, 'timestamp': 100000}, 100,
                                  {'min_notional': 5}, at=100001)
        self.assertTrue(result['entry_intent'])
        self.assertFalse(result['order_submission_allowed'])
        self.assertFalse(result['profitability_validated'])
        self.assertEqual(result['mode'], 'SHADOW')

    def test_missing_or_stale_benchmark_blocks_candidate(self):
        for benchmark in [{'status': 'UNAVAILABLE'}, {'status': 'OK', 'bullish': True, 'observed_at': 1}]:
            result = candidate_intent({'eligible': True, 'profile': 'relative-breakout-v1'}, benchmark,
                                      {'bid': 99.99, 'ask': 100, 'timestamp': 200000}, 100,
                                      {'min_notional': 5}, at=200001)
            self.assertFalse(result['entry_intent'])
            self.assertIn('benchmark_regime', result['blocked_by'])

    def test_open_benchmark_bar_cannot_be_used(self):
        frame = pd.DataFrame({'close': [100.] * 120, 'timestamp': [100000000] * 120})
        with self.assertRaisesRegex(ValueError, 'unclosed'):
            benchmark_context(frame, frame, now_ms=100000001)
