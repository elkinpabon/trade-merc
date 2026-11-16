import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select, func

from pulse.strategy import POLICY, evaluate, floor_step, size_order
from pulse.store import Store, Account, Position, Decision, Snapshot, ResearchCandle, now_ms
from pulse.execution import PaperEngine
from pulse.protection import entry_guard

RULE = {'min_qty': '0.01', 'max_qty': '100000', 'step': '0.01', 'min_notional': '5', 'max_notional': '1000000'}


class PaperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store('sqlite:///' + str(Path(self.temp.name) / 'test.db'))
        self.store.initialize(POLICY)
        self.engine = PaperEngine(self.store)
        self.at = now_ms()

    def tearDown(self):
        self.store.engine.dispose()
        self.temp.cleanup()

    def decision(self, candle=1):
        return {'eligible': True, 'score': 100, 'reasons': [], 'stop_pct': 1.0,
                'target_pct': 2.0, 'candle_at': candle, 'price': 100.0}

    def quote(self, bid=99.99, ask=100, at=None):
        return {'bid': bid, 'ask': ask, 'at': at or self.at}

    def test_decimal_step_and_risk_budget(self):
        self.assertEqual(floor_step('2.3', '.01'), Decimal('2.3'))
        self.assertEqual(floor_step('2.34', '.05'), Decimal('2.30'))
        order = size_order(50, 50, 100, 1, RULE)
        self.assertLessEqual(order['debit'], Decimal(50))
        self.assertLessEqual(order['quantity'] * order['fill'], Decimal(15))
        self.assertLessEqual(order['quantity'] * Decimal(100) * Decimal('.013'), Decimal('.25'))

    def test_entry_retry_does_not_duplicate_debits(self):
        self.assertEqual(self.engine.enter('ETHUSDT', self.decision(), self.quote(), RULE, self.at), 'ENTERED')
        with self.store.Session() as s:
            cash = s.get(Account, 1).cash
        self.assertEqual(self.engine.enter('ETHUSDT', self.decision(), self.quote(), RULE, self.at), 'ALREADY_EVALUATED')
        with self.store.Session() as s:
            self.assertEqual(s.get(Account, 1).cash, cash)
            self.assertEqual(s.scalar(select(func.count(Position.id))), 1)

    def test_market_exit_conserves_cash_and_fees(self):
        self.engine.enter('ETHUSDT', self.decision(), self.quote(), RULE, self.at)
        self.engine.monitor({'ETHUSDT': self.quote(103,103.02)}, {'ETHUSDT': RULE}, self.at+1000)
        with self.store.Session() as s:
            p = s.scalar(select(Position))
            a = s.get(Account, 1)
            self.assertEqual(p.status, 'CLOSED')
            self.assertEqual(p.exit_reason, 'TARGET')
            self.assertAlmostEqual(float(a.cash), 50 + float(p.pnl), places=8)
            expected = p.quantity * (p.exit_price-p.entry) - p.entry_fee-p.exit_fee
            self.assertAlmostEqual(float(expected), float(p.pnl), places=8)
        self.engine.monitor({'ETHUSDT': self.quote(103,103.02)}, {'ETHUSDT': RULE}, self.at+2000)
        with self.store.Session() as s:
            self.assertEqual(s.scalar(select(func.count(Position.id))), 1)

    def test_stale_quotes_block_entries_and_exits(self):
        status = self.engine.enter('ETHUSDT', self.decision(), self.quote(at=self.at-60_000), RULE, self.at)
        self.assertEqual(status, 'REJECTED')
        self.engine.enter('ETHUSDT', self.decision(2), self.quote(), RULE, self.at)
        result = self.engine.monitor({'ETHUSDT': self.quote(90,90.01)}, {'ETHUSDT': RULE}, self.at+60_000)
        self.assertFalse(result['position_quotes_fresh'])
        with self.store.Session() as s:
            self.assertEqual(s.scalar(select(Position)).status, 'OPEN')

    def test_minimum_order_and_one_position_are_enforced(self):
        status = self.engine.enter('ETHUSDT', self.decision(), self.quote(), {**RULE,'min_notional':'20'}, self.at)
        self.assertEqual(status, 'REJECTED')
        self.assertEqual(self.engine.enter('ETHUSDT', self.decision(2), self.quote(), RULE, self.at), 'ENTERED')
        self.assertEqual(self.engine.enter('BTCUSDT', self.decision(2), self.quote(), RULE, self.at), 'REJECTED')

    def test_daily_limit_blocks_entry_but_not_stop(self):
        self.engine.enter('ETHUSDT', self.decision(), self.quote(), RULE, self.at)
        with self.store.Session.begin() as s:
            a=s.get(Account,1)
            a.day_equity=100
        self.engine.monitor({'ETHUSDT': self.quote(98,98.01)}, {'ETHUSDT': RULE}, self.at+1000)
        with self.store.Session() as s:
            self.assertEqual(s.scalar(select(Position)).status,'CLOSED')
        self.assertEqual(self.engine.enter('BTCUSDT', self.decision(), self.quote(), RULE,self.at+1000),'REJECTED')

    def test_untradeable_residual_is_not_invented_sale(self):
        self.engine.enter('ETHUSDT', self.decision(), self.quote(), RULE, self.at)
        self.engine.monitor({'ETHUSDT': self.quote(98,98.01)}, {'ETHUSDT': {**RULE,'min_notional':'50'}}, self.at+1000)
        with self.store.Session() as s:
            p=s.scalar(select(Position))
            self.assertEqual(p.status,'OPEN')
            self.assertEqual(p.dust,1)
            self.assertIsNone(p.pnl)
            snap=s.scalar(select(Snapshot))
            self.assertAlmostEqual(float(snap.equity),float(s.get(Account,1).cash+p.quantity*p.mark),places=8)

    def seed_losses(self, count=20):
        with self.store.Session.begin() as s:
            for i in range(count):
                s.add(Position(symbol=f'LOSS{i}', status='CLOSED', quantity=1, entry=10, mark=9.9,
                               stop=9.8, initial_stop=9.8, target=10.4, high=10, entry_fee=.01,
                               pnl=Decimal('-.1'), opened_at=self.at-10000, closed_at=self.at-5000+i,
                               signal_key=f'loss:{i}', dust=0))

    def test_negative_realized_expectancy_blocks_entries_but_not_exits(self):
        self.engine.enter('ETHUSDT', self.decision(), self.quote(), RULE, self.at)
        self.seed_losses()
        self.assertEqual(self.engine.enter('BTCUSDT', self.decision(), self.quote(), RULE, self.at), 'REJECTED')
        with self.store.Session() as s:
            self.assertTrue(entry_guard(s)['blocked'])
            decision = s.scalar(select(Decision).where(Decision.symbol == 'BTCUSDT'))
            self.assertIn('expectativa', decision.reason)
        self.engine.monitor({'ETHUSDT': self.quote(98,98.01)}, {'ETHUSDT': RULE}, self.at+1000)
        with self.store.Session() as s:
            self.assertEqual(s.scalar(select(Position).where(Position.symbol == 'ETHUSDT')).status, 'CLOSED')

    def test_small_sample_is_not_mistaken_for_proven_negative_edge(self):
        self.seed_losses(5)
        with self.store.Session() as s:
            self.assertFalse(entry_guard(s)['blocked'])

    def test_activated_trailing_stop_covers_both_fees_and_exit_slippage(self):
        self.engine.enter('ETHUSDT', self.decision(), self.quote(), RULE, self.at)
        self.engine.monitor({'ETHUSDT': self.quote(101.1,101.11)}, {'ETHUSDT': RULE}, self.at+1000)
        with self.store.Session() as s:
            p=s.scalar(select(Position))
            stop=p.stop
            self.assertGreater(stop, p.entry)
            self.assertGreater(stop, p.high-(p.entry-p.initial_stop))
        self.engine.monitor({'ETHUSDT': self.quote(float(stop),float(stop)+.01)}, {'ETHUSDT': RULE}, self.at+2000)
        with self.store.Session() as s:
            p=s.scalar(select(Position))
            self.assertEqual(p.status, 'CLOSED')
            self.assertAlmostEqual(float(p.pnl), 0, places=8)

    def test_research_journal_is_idempotent_and_excludes_open_bars(self):
        start = self.at // 300000 * 300000
        def bar(at):
            return [at,'100','101','99','100','10',at+299999,'1000',20,'6','600','0']
        bars = [bar(start-300000), bar(start)]
        self.assertEqual(self.store.record_closed_candles('ETHUSDT', bars, self.at), 1)
        self.assertEqual(self.store.record_closed_candles('ETHUSDT', bars, self.at), 0)
        with self.store.Session() as s:
            rows=s.scalars(select(ResearchCandle)).all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].open_at, start-300000)


class SignalTests(unittest.TestCase):
    def bars(self):
        at = now_ms()
        end = at//300_000*300_000
        rows=[]
        for i in range(100):
            close=100 if i<90 else [100,100.3,100.7,101.1,101.5,101.8,102,102,102,102.3][i-90]
            op=close-.05
            high,low=close+.15,close-.2
            vol=300 if i==99 else 100
            start=end-(100-i)*300_000
            rows.append([start,str(op),str(high),str(low),str(close),str(vol),start+299999,str(vol*close),100,str(vol*.65),str(vol*close*.65),'0'])
        return rows,at

    def test_pattern_and_volume_gate(self):
        bars,at=self.bars()
        ticker={'bid':102.29,'ask':102.31,'volume_usdt':30_000_000}
        decision=evaluate(bars,ticker,at)
        self.assertTrue(decision['eligible'],decision)
        bars[-1][5]='10'
        self.assertFalse(evaluate(bars,ticker,at)['eligible'])

    def test_forming_bar_not_used_and_missing_bar_rejected(self):
        bars,at=self.bars()
        ticker={'bid':102.29,'ask':102.31,'volume_usdt':30_000_000}
        expected=evaluate(bars,ticker,at)
        future=bars[-1].copy()
        future[0]+=300_000
        future[6]+=300_000
        future[4]='1000'
        self.assertEqual(evaluate(bars+[future],ticker,at),expected)
        bars.pop(-4)
        with self.assertRaisesRegex(ValueError,'Huecos'):
            evaluate(bars,ticker,at)

    def test_missing_bid_is_not_zero_spread(self):
        bars,at=self.bars()
        result=evaluate(bars,{'bid':0,'ask':102.31,'volume_usdt':30_000_000},at)
        self.assertFalse(result['eligible'])
        self.assertFalse(result['checks']['spread'])


if __name__ == '__main__':
    unittest.main()
