import os
import unittest
from datetime import datetime, timedelta

os.environ['DATABASE_URL'] = 'sqlite://'

from app import create_app
from app.extensions import db
from app.models import (BotConfig, BotRun, PaperFill, PaperOrder, PaperPosition,
                         PortfolioSnapshot, RunDailyMetric, StrategyRun, Trade)
from app.models import WorkerCycle
from app.services.execution.paper_execution_engine import PaperExecutionEngine
from app.services.experiment_service import ExperimentService
from app.services.research_metrics_service import ResearchMetricsService
from app.utils.helpers import generate_uuid, utc_now


class ExperimentTraceabilityTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.context = self.app.app_context()
        self.context.push()
        db.drop_all()
        db.create_all()
        self.config = BotConfig(
            exchange_id='binance', mode='paper', symbols='BTC/USDT', timeframe='15m',
            virtual_balance=100.0, stop_loss_pct=2.0, take_profit_pct=4.0,
            risk_per_trade_pct=0.25, fee_pct=0.1, slippage_pct=0.05, is_active=True,
        )
        db.session.add(self.config)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_start_is_clean_non_destructive_and_provenance_is_immutable(self):
        db.session.add(PortfolioSnapshot(
            cash_balance=75, positions_value=0, total_equity=75, realized_pnl=-25,
            unrealized_pnl=0, peak_equity=100, drawdown_pct=25, timestamp=utc_now(),
        ))
        db.session.commit()

        first = ExperimentService.start(self.config, git_commit='a' * 40)
        second = ExperimentService.start(self.config, git_commit='b' * 40)

        self.assertEqual(db.session.get(StrategyRun, first.id).status, 'SUPERSEDED')
        self.assertEqual(PortfolioSnapshot.query.count(), 3)
        baseline = PortfolioSnapshot.query.filter_by(strategy_run_id=second.id).one()
        self.assertEqual(baseline.total_equity, 100.0)
        self.assertEqual(second.config_snapshot()['fee_pct'], 0.1)
        second.git_commit = 'changed'
        with self.assertRaises(ValueError):
            db.session.commit()
        db.session.rollback()

    def test_start_refuses_an_open_position(self):
        db.session.add(PaperPosition(id=generate_uuid(), symbol='BTC/USDT', is_open=True))
        db.session.commit()

        with self.assertRaisesRegex(ValueError, 'open'):
            ExperimentService.start(self.config, git_commit='a' * 40)

    def test_execution_entities_and_report_are_attributed(self):
        run = ExperimentService.start(self.config, git_commit='a' * 40)
        engine = PaperExecutionEngine(self.config)
        self.assertTrue(engine.place_order('BTC/USDT', 'BUY', 'MARKET', 2.0, 10.0)['success'])
        self.assertTrue(engine.close_position('BTC/USDT', 11.0)['success'])

        for model in (PaperOrder, PaperFill, PaperPosition, Trade):
            row = model.query.first()
            self.assertEqual(row.strategy_run_id, run.id)
            self.assertEqual(row.model_version_id, run.model_version_id)
            self.assertEqual(row.config_id, self.config.id)
        self.assertTrue(all(row.strategy_run_id == run.id for row in PortfolioSnapshot.query.filter(
            PortfolioSnapshot.id > 1).all()))

        report = ExperimentService.report(run.id)
        self.assertEqual(report['funnel']['closed_trades'], 1)
        self.assertGreater(report['performance']['fees'], 0)
        self.assertGreater(report['performance']['net_pnl'], 0)
        self.assertFalse(report['evaluability']['evaluable'])
        response = self.app.test_client().get(f'/api/experiments/{run.id}/report')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['run']['id'], run.id)

    def test_daily_metric_filters_run_and_uses_intraday_peak_to_trough(self):
        run = ExperimentService.start(self.config, git_commit='a' * 40)
        bot_run = BotRun(id=generate_uuid(), config_id=self.config.id, status='running', started_at=utc_now())
        db.session.add(bot_run)
        now = utc_now()
        for equity in (120.0, 90.0):
            db.session.add(PortfolioSnapshot(
                strategy_run_id=run.id, model_version_id=run.model_version_id, config_id=self.config.id,
                cash_balance=equity, positions_value=0, total_equity=equity,
                realized_pnl=equity - 100, unrealized_pnl=0, peak_equity=120,
                drawdown_pct=0, timestamp=now,
            ))
            now += timedelta(seconds=1)
        db.session.add(Trade(
            id=generate_uuid(), symbol='ETH/USDT', entry_price=1, exit_price=2, quantity=1,
            realized_pnl=100, realized_pnl_pct=100, opened_at=utc_now(), closed_at=utc_now(),
        ))
        db.session.commit()

        metric = ResearchMetricsService.update_paper_daily(self.config, bot_run)

        self.assertEqual(metric.total_trades, 0)
        self.assertAlmostEqual(metric.max_drawdown_pct, 25.0)
        self.assertEqual(RunDailyMetric.query.filter_by(run_id=run.id).count(), 1)

    def test_due_experiment_finishes_without_open_positions(self):
        run = ExperimentService.start(self.config, git_commit='a' * 40)
        run.planned_end_at = utc_now() - timedelta(seconds=1)
        db.session.commit()

        self.assertTrue(ExperimentService.finish_if_due(run))
        self.assertEqual(run.status, 'COMPLETED')
        self.assertIsNotNone(run.finished_at)

    def test_report_uses_recorded_worker_cycles(self):
        run = ExperimentService.start(self.config, git_commit='a' * 40)
        db.session.add(WorkerCycle(
            id=generate_uuid(), bot_run_id='worker-run', strategy_run_id=run.id,
            status='SUCCESS', expected_symbols=1, received_symbols=1,
            processed_symbols=1, started_at=run.started_at, finished_at=utc_now(),
        ))
        db.session.commit()

        report = ExperimentService.report(run.id)
        self.assertEqual(report['coverage']['recorded_cycles'], 1)
        self.assertEqual(report['coverage']['successful_cycles'], 1)


if __name__ == '__main__':
    unittest.main()
