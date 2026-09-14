import os
import unittest
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

os.environ['DATABASE_URL'] = 'sqlite://'

from app import create_app
from app.extensions import db
from app.models import BotConfig, BotRun, SystemHealth, WorkerCycle
from app.services.health_service import BOT_HEARTBEAT_STALE_AFTER, HealthService
from app.utils.helpers import utc_now
from worker.bot_runner import run_bot_loop


class WorkerOperationsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.context = self.app.app_context()
        self.context.push()
        db.drop_all()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def add_config(self, symbols='BTC/USDT'):
        config = BotConfig(exchange_id='binance', mode='paper', symbols=symbols)
        db.session.add(config)
        db.session.commit()
        return config

    def test_single_cycle_stops_without_config(self):
        with patch('worker.bot_runner.time.sleep') as sleep:
            result = run_bot_loop(self.app, max_cycles=1)

        self.assertFalse(result)
        sleep.assert_not_called()

    def test_single_cycle_stops_without_running_run(self):
        self.add_config()

        with patch('worker.bot_runner.time.sleep') as sleep:
            result = run_bot_loop(self.app, max_cycles=1)

        self.assertFalse(result)
        sleep.assert_not_called()

    def test_final_heartbeat_and_cycle_error_are_persisted(self):
        config = self.add_config()
        old_heartbeat = utc_now() - timedelta(hours=1)
        run = BotRun(
            id='run-error', config_id=config.id, status='running',
            last_heartbeat=old_heartbeat,
        )
        db.session.add(run)
        db.session.commit()

        with patch.dict(os.environ, {'WORKER_SLOT_AT': '2026-09-07T02:00:00'}), \
                patch('worker.bot_runner.MarketDataService.fetch_all_tickers', side_effect=RuntimeError('market failed')):
            result = run_bot_loop(self.app, max_cycles=1)
            retry_result = run_bot_loop(self.app, max_cycles=1)

        db.session.expire_all()
        persisted = db.session.get(BotRun, run.id)
        self.assertFalse(result)
        self.assertFalse(retry_result)
        self.assertEqual(WorkerCycle.query.count(), 1)
        self.assertGreater(persisted.last_heartbeat, old_heartbeat)
        self.assertEqual(persisted.error_message, 'market failed')

    def test_symbol_and_candidate_training_failures_are_isolated(self):
        config = self.add_config('BTC/USDT,ETH/USDT')
        run = BotRun(id='run-isolation', config_id=config.id, status='running')
        db.session.add(run)
        db.session.commit()
        tickers = {
            'BTC/USDT': {'last': 100.0},
            'ETH/USDT': {'last': 50.0},
        }

        with patch('worker.bot_runner.LogService.log'), \
                patch('worker.bot_runner.broadcast_event'), \
                patch('worker.bot_runner.MarketDataService.fetch_all_tickers', return_value=tickers), \
                patch('worker.bot_runner.ScannerService.scan_tickers', return_value=[]), \
                patch('worker.bot_runner.RiskService.check_stop_loss_take_profit', side_effect=[RuntimeError('BTC failed'), {'reason': 'STOP_LOSS'}]), \
                patch('worker.bot_runner.PaperExecutionEngine.close_position', return_value={'success': False}), \
                patch('worker.bot_runner.PortfolioService.update_valuation'), \
                patch('worker.bot_runner.PortfolioService.get_summary', return_value={}), \
                patch('worker.bot_runner.EvaluationService.resolve_pending', return_value=0), \
                patch('worker.bot_runner.ResearchMetricsService.update_paper_daily'), \
                patch('worker.bot_runner.ModelService.train_if_due', side_effect=RuntimeError('training failed')):
            result = run_bot_loop(self.app, max_cycles=1)

        db.session.expire_all()
        persisted = db.session.get(BotRun, run.id)
        health = SystemHealth.query.filter_by(component='bot_worker').one()
        self.assertFalse(result)
        self.assertIn('BTC/USDT: BTC failed', persisted.error_message)
        self.assertIn('expected=2, received=2, processed=0', health.details)
        self.assertEqual(health.status, 'DEGRADED')

    def test_cycle_without_experiment_does_not_create_entry_signals(self):
        import pandas as pd

        config = self.add_config()
        db.session.add(BotRun(id='run-without-experiment', config_id=config.id, status='running'))
        db.session.commit()
        frame = pd.DataFrame([{
            'timestamp': index, 'datetime': pd.Timestamp('2026-09-14T19:00:00'),
            'close': 100.0, 'bb_middle': 99.0, 'vol_ratio': 2.0,
            'rsi': 55.0, 'adx': 25.0, 'macd_histogram': 1.0,
        } for index in range(30)])
        score_data = {
            'total_score': 80.0, 'trend_score': 20.0, 'momentum_score': 20.0,
            'volume_score': 20.0, 'volatility_score': 10.0,
            'prediction_score': 10.0, 'regime_score': 10.0,
            'ml_prediction': {
                'market_regime': 'TRENDING_UP', 'candle_pattern': 'NONE',
                'lr_direction': 1, 'lr_r_squared': 0.7,
            },
        }

        with patch('worker.bot_runner.LogService.log'), \
                patch('worker.bot_runner.LogService.prune'), \
                patch('worker.bot_runner.broadcast_event'), \
                patch('worker.bot_runner.MarketDataService.fetch_all_tickers', return_value={'BTC/USDT': {'last': 100.0}}), \
                patch('worker.bot_runner.MarketDataService.get_ohlcv_dataframe', return_value=frame), \
                patch('worker.bot_runner.ScannerService.scan_tickers', return_value=[]), \
                patch('worker.bot_runner.RiskService.check_stop_loss_take_profit', return_value=None), \
                patch('worker.bot_runner.IndicatorService.apply_indicators', return_value=frame), \
                patch('worker.bot_runner.StrategyService.compute_composite_score', return_value=score_data), \
                patch('worker.bot_runner.EvaluationService.record', return_value=SimpleNamespace(signal_id=None, probability=0.8)), \
                patch('worker.bot_runner.StrategyService.evaluate_market') as evaluate_market, \
                patch('worker.bot_runner.PortfolioService.update_valuation'), \
                patch('worker.bot_runner.PortfolioService.get_summary', return_value={}), \
                patch('worker.bot_runner.EvaluationService.resolve_pending', return_value=0), \
                patch('worker.bot_runner.ResearchMetricsService.update_paper_daily'), \
                patch('worker.bot_runner.ModelService.train_if_due', return_value=None):
            result = run_bot_loop(self.app, max_cycles=1)

        self.assertTrue(result)
        evaluate_market.assert_not_called()

    def test_health_degrades_a_stale_running_worker(self):
        config = self.add_config()
        db.session.add(BotRun(
            id='run-stale', config_id=config.id, status='running',
            last_heartbeat=utc_now() - BOT_HEARTBEAT_STALE_AFTER - timedelta(seconds=1),
        ))
        db.session.commit()

        result = HealthService.get_system_health()
        worker = next(component for component in result['components'] if component['component'] == 'bot_worker')

        self.assertEqual(result['overall_status'], 'DEGRADED')
        self.assertEqual(worker['status'], 'DEGRADED')
        self.assertIn('stale', worker['details'])


if __name__ == '__main__':
    unittest.main()
