import json
import os
import unittest
from datetime import datetime, timezone

import numpy as np
import pandas as pd

os.environ['DATABASE_URL'] = 'sqlite://'
from app import create_app
from app.extensions import db
from app.models import BotConfig, PaperPosition, PortfolioSnapshot, Signal
from app.services.opportunity_service import OpportunityService
from app.services.risk_service import RiskService
from app.services.execution.paper_execution_engine import PaperExecutionEngine
from app.utils.helpers import utc_now


class OpportunityTest(unittest.TestCase):
    def frame(self, minutes):
        end = (int(datetime.now(timezone.utc).timestamp() * 1000) // (minutes * 60_000) - 1) * minutes * 60_000
        closes = np.linspace(95, 100, 120)
        data = pd.DataFrame({'close': closes, 'high': closes + .2, 'low': closes - .2,
                             'open': closes - .1, 'volume': [100.] * 120,
                             'timestamp': [end - (119 - i) * minutes * 60_000 for i in range(120)]})
        data['datetime'] = pd.to_datetime(data['timestamp'], unit='ms')
        return data

    def test_breakout_is_filtered_by_liquidity_rank_and_spread(self):
        frame = self.frame(15)
        frame.loc[119, ['close', 'high', 'volume']] = [100.5, 100.7, 300.]
        hourly, four = self.frame(60), self.frame(240)
        ticker = {'bid': 100.49, 'ask': 100.51, 'quote_volume': 50_000_000}
        decision = OpportunityService.decide('relative-breakout-v1', frame, hourly, four, ticker, 1)
        self.assertTrue(decision['eligible'], decision)
        self.assertFalse(OpportunityService.decide('relative-breakout-v1', frame, hourly, four, ticker, 6)['eligible'])
        self.assertFalse(OpportunityService.decide('relative-breakout-v1', frame, hourly, four, {**ticker, 'ask': 102}, 1)['eligible'])
        self.assertFalse(OpportunityService.decide('relative-breakout-v1', frame, hourly, four, {**ticker, 'quote_volume': 10}, 1)['eligible'])

    def test_missing_history_and_forming_candle_are_not_tradeable(self):
        frame = self.frame(15)
        ticker = {'bid': 100, 'ask': 100.01, 'quote_volume': 50_000_000}
        with self.assertRaisesRegex(ValueError, 'history'):
            OpportunityService.decide('trend-pullback-v2', frame, self.frame(60).iloc[:10], self.frame(240), ticker, 1)
        frame.loc[119, 'timestamp'] = int(datetime.now(timezone.utc).timestamp() * 1000)
        with self.assertRaisesRegex(ValueError, 'open candle'):
            OpportunityService.decide('trend-pullback-v2', frame, self.frame(60), self.frame(240), ticker, 1)

    def test_pullback_recovers_ema_without_requiring_momentum_top_five(self):
        frame = self.frame(15)
        frame.loc[118, ['close', 'high', 'low']] = [98.8, 99.0, 98.6]
        frame.loc[119, ['close', 'high', 'volume']] = [100.0, 100.2, 150.]
        ticker = {'bid': 99.99, 'ask': 100.01, 'quote_volume': 50_000_000}
        decision = OpportunityService.decide('trend-pullback-v2', frame, self.frame(60), self.frame(240), ticker, 15)
        self.assertTrue(decision['eligible'], decision)
        self.assertAlmostEqual(decision['take_profit_pct'] / decision['stop_loss_pct'], 2.5)

    def test_atr_risk_matches_execution_and_breaker_allows_exit(self):
        app = create_app()
        with app.app_context():
            db.drop_all()
            db.create_all()
            config = BotConfig(strategy_key='relative-breakout-v1')
            db.session.add(config)
            db.session.commit()
            decision = {'stop_loss_pct': 1.5, 'take_profit_pct': 4.5}
            signal = Signal(id='atr-entry', bot_run_id='run', symbol='ETH/USDT',
                            action='ENTER_LONG', type='BUY', price=100, status='PENDING',
                            timestamp=utc_now(), indicators_json=json.dumps({'opportunity': decision}))
            db.session.add(signal)
            db.session.commit()
            allowed, _, quantity = RiskService(config).validate_signal_risk(signal, 100)
            self.assertTrue(allowed)
            self.assertAlmostEqual(quantity * 100 * .018, .25)
            engine = PaperExecutionEngine(config)
            result = engine.place_order('ETH/USDT', 'BUY', 'MARKET', quantity, 100, signal.id)
            self.assertTrue(result['success'])
            position = PaperPosition.query.one()
            self.assertAlmostEqual(position.stop_loss_price, position.entry_price * .985, places=2)
            self.assertAlmostEqual(position.take_profit_price, position.entry_price * 1.045, places=2)
            snapshot = PortfolioSnapshot.query.order_by(PortfolioSnapshot.id.desc()).first()
            snapshot.drawdown_pct = 20
            db.session.commit()
            exit_signal = Signal(symbol='ETH/USDT', action='EXIT_LONG')
            self.assertTrue(RiskService(config).validate_signal_risk(exit_signal, 95)[0])
            db.session.remove()
            db.drop_all()


if __name__ == '__main__':
    unittest.main()
