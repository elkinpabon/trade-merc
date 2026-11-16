import json
import os
import unittest
from datetime import timedelta

import pandas as pd

os.environ['DATABASE_URL'] = 'sqlite://'
from app import create_app
from app.extensions import db
from app.models import BotConfig, PaperPosition, Signal, SymbolRule, RiskEvent
from app.services.indicator_service import IndicatorService
from app.services.opportunity_service import OpportunityService
from app.services.risk_service import RiskService
from app.utils.helpers import utc_now, round_qty


class AuditRegressionTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.context = self.app.app_context()
        self.context.push()
        db.drop_all()
        db.create_all()
        self.config = BotConfig(strategy_key='relative-breakout-v1', virtual_balance=100,
                                risk_per_trade_pct=.25, cooldown_seconds=14400)
        db.session.add(self.config)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def recent_signal(self, status='EXECUTED'):
        signal = Signal(id='recent', bot_run_id='run', symbol='ETH/USDT', type='BUY', action='ENTER_LONG',
                        price=100, status=status, timestamp=utc_now() - timedelta(minutes=15))
        db.session.add(signal)
        db.session.commit()

    def test_regime_exit_is_not_blocked_by_entry_cooldown(self):
        self.recent_signal()
        db.session.add(PaperPosition(id='position', symbol='ETH/USDT', quantity=.1,
                                     entry_price=100, is_open=True))
        db.session.commit()
        decision = {'eligible': False, 'checks': {'trend_1h_4h': False}}
        signal = OpportunityService.signal(self.config, 'ETH/USDT', 'run',
                                           pd.DataFrame({'close': [99]}), decision)
        self.assertIsNotNone(signal)
        self.assertEqual(signal.action, 'EXIT_LONG')

    def test_entry_cooldown_still_blocks_new_entries(self):
        self.recent_signal()
        self.assertIsNone(OpportunityService.signal(self.config, 'ETH/USDT', 'run',
                           pd.DataFrame({'close': [100]}), {'eligible': True}))

    def test_rejected_signal_does_not_start_a_trade_cooldown(self):
        self.recent_signal(status='REJECTED')
        result = OpportunityService.signal(self.config, 'ETH/USDT', 'run',
                                           pd.DataFrame({'close': [100]}), {'eligible': True})
        self.assertIsNotNone(result)
        self.assertEqual(result.action, 'ENTER_LONG')

    def test_equal_directional_moves_do_not_create_false_adx_trend(self):
        frame = pd.DataFrame({'high': [101+i for i in range(60)],
                              'low': [99-i for i in range(60)], 'close': [100]*60})
        self.assertEqual(IndicatorService.calculate_adx(frame).iloc[-1], 0.)

    def test_adx_preserves_real_directional_trend(self):
        frame = pd.DataFrame({'high': [101+i for i in range(60)],
                              'low': [99+i for i in range(60)], 'close': [100+i for i in range(60)]})
        self.assertAlmostEqual(IndicatorService.calculate_adx(frame).iloc[-1], 100.)

    def sizing_signal(self):
        return Signal(symbol='ETH/USDT', action='ENTER_LONG',
                      indicators_json=json.dumps({'opportunity': {'stop_loss_pct': 2.5}}))

    def test_symbol_five_dollar_minimum_does_not_require_ten(self):
        db.session.add(SymbolRule(symbol='ETH/USDT', min_notional=5., min_qty=.001,
                                  qty_precision=3, price_precision=2))
        db.session.commit()
        allowed, reason, qty = RiskService(self.config).validate_signal_risk(self.sizing_signal(), 100)
        self.assertTrue(allowed, reason)
        self.assertGreaterEqual(qty * 100, 5)
        self.assertLess(qty * 100, 10)
        self.assertLessEqual(qty * 100 * .028, .25)

    def test_minimum_does_not_increase_risk_to_force_entry(self):
        db.session.add(SymbolRule(symbol='ETH/USDT', min_notional=10., min_qty=.001,
                                  qty_precision=3, price_precision=2))
        db.session.commit()
        allowed, _, qty = RiskService(self.config).validate_signal_risk(self.sizing_signal(), 100)
        self.assertFalse(allowed)
        self.assertEqual(qty, 0.)

    def test_dust_is_retained_and_logged_only_once(self):
        db.session.add(SymbolRule(symbol='UNI/USDT', min_notional=5., min_qty=.01,
                                  qty_precision=2, price_precision=3))
        db.session.add(PaperPosition(id='dust', symbol='UNI/USDT', quantity=.01,
                                     entry_price=7., is_open=True, stop_loss_price=8.))
        db.session.commit()
        for _ in range(2):
            self.assertEqual(RiskService(self.config).check_stop_loss_take_profit('UNI/USDT', 7.)['trigger'], 'DUST')
        self.assertTrue(PaperPosition.query.one().is_open)
        self.assertEqual(RiskEvent.query.filter_by(event_type='PAPER_DUST').count(), 1)

    def test_quantity_rounding_does_not_create_false_residual(self):
        self.assertEqual(round_qty(2.29, 2), 2.29)
        self.assertEqual(round_qty(2.299, 2), 2.29)
