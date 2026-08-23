import os
import unittest

os.environ['DATABASE_URL'] = 'sqlite://'

from app import create_app
from app.extensions import db
from app.models import BotConfig, PaperFill, PaperOrder, PaperPosition, PortfolioSnapshot, Signal, Trade
from app.services.execution.paper_execution_engine import PaperExecutionEngine
from app.services.indicator_service import IndicatorService
from app.services.market_data_service import MarketDataService
from app.services.risk_service import RiskService
from app.utils.helpers import generate_uuid, utc_now


class PaperTradingTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.context = self.app.app_context()
        self.context.push()
        db.drop_all()
        db.create_all()
        self.config = BotConfig(
            exchange_id='binance', mode='paper', symbols='BTC/USDT', timeframe='15m',
            virtual_balance=100.0, stop_loss_pct=2.0, take_profit_pct=4.0,
            risk_per_trade_pct=0.25, fee_pct=0.1, slippage_pct=0.05,
        )
        db.session.add(self.config)
        db.session.commit()
        self.engine = PaperExecutionEngine(self.config)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_risk_size_uses_stop_distance(self):
        signal = Signal(
            id=generate_uuid(), bot_run_id='run', symbol='BTC/USDT', type='BUY',
            action='ENTER_LONG', price=100.0, status='PENDING', timestamp=utc_now(),
        )
        db.session.add(signal)
        db.session.commit()

        allowed, reason, quantity = RiskService(self.config).validate_signal_risk(signal, 100.0)

        self.assertTrue(allowed, reason)
        self.assertAlmostEqual(quantity, 0.125)

    def test_paper_trade_is_idempotent_and_counts_both_fees(self):
        signal_id = generate_uuid()
        buy = self.engine.place_order('BTC/USDT', 'BUY', 'MARKET', 2.0, 10.0, signal_id)
        retry = self.engine.place_order('BTC/USDT', 'BUY', 'MARKET', 2.0, 10.0, signal_id)

        self.assertTrue(buy['success'])
        self.assertTrue(retry['success'])
        self.assertTrue(retry['idempotent'])
        self.assertEqual(PaperOrder.query.count(), 1)
        self.assertEqual(PaperFill.query.count(), 1)

        close = self.engine.close_position('BTC/USDT', 11.0, reason='TAKE_PROFIT')
        trade = Trade.query.one()
        position = PaperPosition.query.filter_by(symbol='BTC/USDT').one()

        self.assertTrue(close['success'])
        self.assertFalse(position.is_open)
        self.assertEqual(trade.exit_reason, 'TAKE_PROFIT')
        self.assertGreater(trade.total_fee, 0.03)
        self.assertGreater(trade.realized_pnl, 0.0)

    def test_closed_symbol_can_be_reopened(self):
        self.assertTrue(self.engine.place_order('BTC/USDT', 'BUY', 'MARKET', 2.0, 10.0)['success'])
        self.assertTrue(self.engine.close_position('BTC/USDT', 10.5)['success'])
        reopened = self.engine.place_order('BTC/USDT', 'BUY', 'MARKET', 2.0, 10.0)

        self.assertTrue(reopened['success'])
        self.assertEqual(PaperPosition.query.count(), 1)
        self.assertTrue(PaperPosition.query.one().is_open)

    def test_rsi_handles_one_sided_moves(self):
        increasing = IndicatorService.calculate_rsi(__import__('pandas').Series(range(1, 30)))
        decreasing = IndicatorService.calculate_rsi(__import__('pandas').Series(range(30, 1, -1)))

        self.assertEqual(increasing.iloc[-1], 100.0)
        self.assertEqual(decreasing.iloc[-1], 0.0)

    def test_market_data_excludes_the_open_candle(self):
        service = object.__new__(MarketDataService)
        service.fetch_public_ohlcv = lambda *args: [
            {'timestamp': 1, 'open': 1, 'high': 1, 'low': 1, 'close': 1, 'volume': 1},
            {'timestamp': 2, 'open': 2, 'high': 2, 'low': 2, 'close': 2, 'volume': 2},
        ]

        candles = service.get_ohlcv_dataframe('BTC/USDT')

        self.assertEqual(len(candles), 1)
        self.assertEqual(candles.iloc[0]['close'], 1)


if __name__ == '__main__':
    unittest.main()
