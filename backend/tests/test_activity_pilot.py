import json
import os
import unittest
from datetime import timedelta
from unittest.mock import patch

import pandas as pd

os.environ['DATABASE_URL'] = 'sqlite://'
from app import create_app
from app.extensions import db
from app.models import BotConfig, BotRun, PaperOrder, PaperPosition, PortfolioSnapshot, Signal, StrategyRun, Trade
from app.services.activity_profiles import assess, features, PILOT_PROFILES
from app.services.experiment_service import ExperimentService
from app.services.execution.paper_execution_engine import PaperExecutionEngine
from app.services.risk_service import RiskService
from app.utils.helpers import utc_now
from scripts.start_activity_pilot import launch

A, B = tuple(PILOT_PROFILES)


class ActivityModelTests(unittest.TestCase):
    def inputs(self):
        return ({'close':100.,'open':99.7,'atr':.5,'rsi':55.,'volume_ratio':1.5,
                 'ema20':99.8,'ema50':99.6,'previous_ema20':99.7,'previous_high':99.9,
                 'recent_low':99.5,'breakout_high':99.9},
                {'close':100.,'ema20':99.9,'ema50':99.8},
                {'close':100.,'ema20':100.,'ema50':100.},
                {'bid':99.99,'ask':100.01,'quote_volume':50_000_000})

    def test_both_hypotheses_can_generate_signals_without_claiming_validation(self):
        for profile in (A,B):
            d=assess(profile,*self.inputs(),relative_rank=8)
            self.assertTrue(d['eligible'],d)
            self.assertTrue(d['experimental_paper'])
            self.assertEqual(d['take_profit_pct']/d['stop_loss_pct'],2)

    def test_costs_liquidity_volatility_and_momentum_are_not_removed(self):
        f,h,four,q=self.inputs()
        for profile in (A,B):
            for ff,qq,cost in [({**f,'rsi':90},q,.3),({**f,'atr':2},q,.3),
                               (f,{**q,'quote_volume':1},.3),(f,{**q,'ask':102},.3),(f,q,1.)]:
                self.assertFalse(assess(profile,ff,h,four,qq,1,cost)['eligible'])

    def test_breakout_rank_and_severe_downtrend_still_block_entries(self):
        f,h,four,q=self.inputs()
        self.assertFalse(assess(B,f,h,four,q,11)['eligible'])
        self.assertTrue(assess(A,f,h,four,q,20)['eligible'])
        for profile in (A,B):
            self.assertFalse(assess(profile,f,h,{**four,'close':94},q,1)['eligible'])

    def test_feature_history_is_not_changed_by_future_candles(self):
        raw=pd.DataFrame({'timestamp':range(120),'open':[100.]*120,'close':[100.+(i%7)/10 for i in range(120)],
                          'high':[101.]*120,'low':[99.]*120,'volume':[100.]*120})
        old=features(raw.iloc[:100]).iloc[-1]
        extended=features(raw).iloc[99]
        for k in ('ema20','ema50','rsi','atr','breakout_high','volume_ratio'):
            self.assertEqual(old[k],extended[k])


class PilotLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.app=create_app();self.ctx=self.app.app_context();self.ctx.push()
        db.drop_all();db.create_all()
        self.old_config=BotConfig(strategy_key='trend-pullback-v2',mode='paper',timeframe='15m',
                                  virtual_balance=100.,risk_per_trade_pct=.25,stop_loss_pct=2.,take_profit_pct=4.,
                                  fee_pct=.1,slippage_pct=.05,symbols='ETH/USDT')
        db.session.add(self.old_config);db.session.flush()
        db.session.add(BotRun(id='old-bot',config_id=self.old_config.id,status='running'))
        db.session.commit()
        self.old=ExperimentService.start(self.old_config)
        self.old.status='COMPLETED';self.old.finished_at=utc_now();db.session.commit()
        self.original_snapshot=self.old.config_snapshot_json

    def tearDown(self):
        db.session.remove();db.drop_all();self.ctx.pop()

    def start(self):
        run,created=launch(A,'test-pilot',self.old.id,acknowledge=True)
        self.assertTrue(created)
        return run,db.session.get(BotConfig,run.config_id)

    def signal(self):
        return Signal(symbol='ETH/USDT',action='ENTER_LONG',
                      indicators_json=json.dumps({'opportunity':{'stop_loss_pct':1.,'take_profit_pct':2.}}))

    def test_requires_explicit_permission_and_expected_predecessor(self):
        with self.assertRaises(ValueError):launch(A,'test',self.old.id)
        with self.assertRaises(ValueError):launch(A,'test','wrong-db',acknowledge=True)
        config=BotConfig(strategy_key=A)
        with self.assertRaisesRegex(ValueError,'authorization'):ExperimentService.start(config)
        self.assertEqual(StrategyRun.query.count(),1)

    def test_snapshot_accepts_datetime_truncation_not_parameter_changes(self):
        captured = json.loads(ExperimentService.config_snapshot(self.old_config))
        captured['created_at'] = self.old_config.created_at.replace(microsecond=123456).isoformat()
        self.assertTrue(ExperimentService.config_unchanged(self.old_config, json.dumps(captured)))
        captured['cooldown_seconds'] = 3600
        self.assertFalse(ExperimentService.config_unchanged(self.old_config, json.dumps(captured)))

    def test_new_ledger_is_separate_old_report_unchanged_and_retry_idempotent(self):
        run,config=self.start()
        self.assertNotEqual(run.config_id,self.old.config_id)
        self.assertEqual(self.old.config_snapshot_json,self.original_snapshot)
        self.assertEqual(self.old.status,'COMPLETED')
        self.assertEqual(BotRun.query.filter_by(status='running').count(),1)
        self.assertEqual(db.session.get(BotRun,'old-bot').status,'stopped')
        self.assertEqual(PortfolioSnapshot.query.filter_by(strategy_run_id=run.id).one().cash_balance,100.)
        same,created=launch(A,'test-pilot',self.old.id,acknowledge=True)
        self.assertFalse(created);self.assertEqual(same.id,run.id)
        self.assertEqual(StrategyRun.query.count(),2)
        self.assertEqual(PortfolioSnapshot.query.count(),2)
        self.assertEqual(config.cooldown_seconds,3600)
        self.assertFalse(json.loads(run.parameters_json)['profitability_validated'])

    def test_failure_rolls_back_account_and_active_bot_switch(self):
        with patch('scripts.start_activity_pilot.ExperimentService.start',side_effect=RuntimeError('failed')):
            with self.assertRaises(RuntimeError):launch(A,'rollback',self.old.id,acknowledge=True)
        self.assertEqual(BotConfig.query.count(),1)
        self.assertEqual(db.session.get(BotRun,'old-bot').status,'running')
        self.assertEqual(PortfolioSnapshot.query.count(),1)

    def test_does_not_replace_running_experiment_or_open_position(self):
        db.session.add(PaperPosition(id='p',symbol='ETH/USDT',quantity=.2,entry_price=100,is_open=True))
        db.session.commit()
        with self.assertRaises(ValueError):launch(A,'busy',self.old.id,acknowledge=True)

    def test_daily_entry_cap_is_scoped_to_new_trial(self):
        run,config=self.start()
        for i in range(8):
            db.session.add(PaperOrder(id=f'old{i}',strategy_run_id=self.old.id,symbol='ETH/USDT',
                                     side='BUY',type='MARKET',quantity=.1,requested_price=100,status='FILLED'))
        db.session.commit()
        self.assertTrue(RiskService(config).validate_signal_risk(self.signal(),100)[0])
        for i in range(8):
            db.session.add(PaperOrder(id=f'new{i}',strategy_run_id=run.id,symbol='ETH/USDT',
                                     side='BUY',type='MARKET',quantity=.1,requested_price=100,status='FILLED'))
        db.session.commit()
        ok,reason,_=RiskService(config).validate_signal_risk(self.signal(),100)
        self.assertFalse(ok);self.assertIn('cap',reason)

    def test_daily_losses_block_entries_never_protective_exits(self):
        run,config=self.start()
        db.session.add(PortfolioSnapshot(strategy_run_id=run.id,cash_balance=98.4,total_equity=98.4,
                                         positions_value=0,realized_pnl=-1.6,unrealized_pnl=0,
                                         peak_equity=100,drawdown_pct=1.6))
        db.session.add(PaperPosition(id='p',symbol='ETH/USDT',quantity=.2,entry_price=100,is_open=True))
        db.session.commit()
        ok,reason,_=RiskService(config).validate_signal_risk(self.signal(),100)
        self.assertFalse(ok);self.assertIn('daily loss',reason)
        self.assertTrue(RiskService(config).validate_signal_risk(Signal(symbol='ETH/USDT',action='EXIT_LONG'),100)[0])

    def test_time_exit_and_net_break_even(self):
        run,config=self.start()
        bot=BotRun.query.filter_by(status='running').one()
        signal=Signal(id='entry',bot_run_id=bot.id,symbol='ETH/USDT',type='BUY',action='ENTER_LONG',price=100,
                      indicators_json=json.dumps({'opportunity':{'stop_loss_pct':1.,'take_profit_pct':2.}}))
        db.session.add(signal);db.session.commit()
        self.assertTrue(PaperExecutionEngine(config).place_order('ETH/USDT','BUY','MARKET',.15,100,signal.id)['success'])
        service=RiskService(config)
        self.assertIsNone(service.check_stop_loss_take_profit('ETH/USDT',101.1))
        p=PaperPosition.query.one()
        net=p.quantity*(p.stop_loss_price*(1-.0005)*(1-.001)-p.entry_price)-p.entry_fee_amount
        self.assertGreaterEqual(net,0)
        p.opened_at=utc_now()-timedelta(hours=7);db.session.commit()
        self.assertEqual(service.check_stop_loss_take_profit('ETH/USDT',101.1)['reason'],'PILOT_MAX_HOLD')
