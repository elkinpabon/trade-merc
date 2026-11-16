import unittest

from app.services.execution_quotes import executable_price


class ExecutionQuoteTests(unittest.TestCase):
    def quote(self, **values):
        return {'bid': 99.99, 'ask': 100., 'timestamp': 100000, **values}

    def test_buy_uses_ask_and_sell_uses_bid(self):
        self.assertEqual(executable_price(self.quote(), 'BUY', 100, 100001), 100)
        self.assertEqual(executable_price(self.quote(), 'SELL', now_ms=100001), 99.99)

    def test_missing_bid_cannot_become_zero_spread(self):
        with self.assertRaises(ValueError):
            executable_price({'last': 100, 'ask': 100, 'timestamp': 100000}, 'BUY', 100, 100001)

    def test_stale_future_inverted_nan_and_wide_quotes_rejected(self):
        for quote in [self.quote(timestamp=1), self.quote(timestamp=200000),
                      self.quote(bid=101), self.quote(ask=float('nan')), self.quote(bid=99)]:
            with self.subTest(quote=quote), self.assertRaises(ValueError):
                executable_price(quote, 'BUY', 100, 100001)

    def test_chasing_entry_blocked_but_exit_not_blocked_by_drift_or_spread(self):
        with self.assertRaisesRegex(ValueError, '0.30%'):
            executable_price(self.quote(bid=100.39, ask=100.4), 'BUY', 100, 100001)
        self.assertEqual(executable_price(self.quote(bid=90, ask=100), 'SELL', 100, 100001), 90)
