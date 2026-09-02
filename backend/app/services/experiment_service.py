import json
import subprocess
from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import (BotConfig, BotRun, PaperFill, PaperOrder, PaperPosition,
                         PortfolioSnapshot, RunDailyMetric, Signal, StrategyEvaluation,
                         StrategyRun, Trade, WorkerCycle)
from app.services.model_service import ModelService
from app.utils.helpers import generate_uuid, utc_now


class ExperimentService:
    DURATION_DAYS = 30
    MIN_COVERAGE_PCT = 99.0
    MIN_CLOSED_TRADES = 100

    @staticmethod
    def _json_value(value):
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        return value

    @classmethod
    def config_snapshot(cls, config) -> str:
        values = {
            column.name: cls._json_value(getattr(config, column.name))
            for column in config.__table__.columns
        }
        return json.dumps(values, sort_keys=True, separators=(',', ':'))

    @staticmethod
    def git_commit() -> str:
        try:
            return subprocess.run(
                ['git', 'rev-parse', 'HEAD'], capture_output=True, text=True,
                check=True, timeout=5,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return 'unknown'

    @staticmethod
    def active_run(config_id=None):
        query = StrategyRun.query.filter_by(run_type='EXPERIMENT', status='RUNNING')
        if config_id is not None:
            query = query.filter_by(config_id=config_id)
        return query.order_by(StrategyRun.started_at.desc()).first()

    @classmethod
    def attribution(cls, config_id=None):
        run = cls.active_run(config_id)
        if not run:
            return {'strategy_run_id': None, 'model_version_id': None, 'config_id': config_id}
        return {
            'strategy_run_id': run.id,
            'model_version_id': run.model_version_id,
            'config_id': run.config_id,
        }

    @classmethod
    def finish_if_due(cls, run):
        if not run or not run.planned_end_at or utc_now() < run.planned_end_at:
            return False
        if PaperPosition.query.filter_by(strategy_run_id=run.id, is_open=True).count():
            return False
        run.status = 'COMPLETED'
        run.finished_at = utc_now()
        db.session.commit()
        return True

    @classmethod
    def start(cls, config, git_commit=None):
        if PaperPosition.query.filter_by(is_open=True).count():
            raise ValueError('Cannot start an experiment while a paper position is open.')

        now = utc_now()
        for previous in StrategyRun.query.filter_by(run_type='EXPERIMENT', status='RUNNING').all():
            previous.status = 'SUPERSEDED'
            previous.finished_at = now

        model = ModelService.active_model()
        if config.model_version_id != model.id:
            config.model_version_id = model.id
            db.session.flush()
        bot_run = BotRun.query.filter_by(status='running').order_by(BotRun.started_at.desc()).first()
        snapshot_json = cls.config_snapshot(config)
        run = StrategyRun(
            id=generate_uuid(), run_type='EXPERIMENT', status='RUNNING',
            model_version_id=model.id, config_id=config.id,
            source_bot_run_id=bot_run.id if bot_run else None,
            symbols_json=json.dumps(config.symbols.split(',') if config.symbols else []),
            timeframe=config.timeframe,
            parameters_json=json.dumps({
                'duration_days': cls.DURATION_DAYS,
                'minimum_coverage_pct': cls.MIN_COVERAGE_PCT,
                'minimum_closed_trades': cls.MIN_CLOSED_TRADES,
            }, sort_keys=True),
            config_snapshot_json=snapshot_json,
            git_commit=git_commit or cls.git_commit(),
            started_at=now, planned_end_at=now + timedelta(days=cls.DURATION_DAYS),
        )
        db.session.add(run)
        db.session.flush()
        db.session.add(PortfolioSnapshot(
            strategy_run_id=run.id, model_version_id=run.model_version_id, config_id=config.id,
            cash_balance=float(config.virtual_balance), positions_value=0.0,
            total_equity=float(config.virtual_balance), realized_pnl=0.0, unrealized_pnl=0.0,
            peak_equity=float(config.virtual_balance), drawdown_pct=0.0, timestamp=now,
        ))
        db.session.commit()
        return run

    @staticmethod
    def _max_drawdown(snapshots):
        peak = None
        maximum = 0.0
        for snapshot in snapshots:
            equity = float(snapshot.total_equity)
            peak = equity if peak is None else max(peak, equity)
            if peak > 0:
                maximum = max(maximum, (peak - equity) / peak * 100.0)
        return maximum

    @classmethod
    def report(cls, run_id):
        run = db.session.get(StrategyRun, run_id)
        if not run or run.run_type != 'EXPERIMENT':
            return None

        trades = Trade.query.filter_by(strategy_run_id=run.id).order_by(Trade.closed_at).all()
        orders = PaperOrder.query.filter_by(strategy_run_id=run.id).all()
        fills = PaperFill.query.filter_by(strategy_run_id=run.id).all()
        snapshots = PortfolioSnapshot.query.filter_by(strategy_run_id=run.id).order_by(PortfolioSnapshot.timestamp).all()
        daily = RunDailyMetric.query.filter_by(run_id=run.id).order_by(RunDailyMetric.metric_date).all()
        cycles = WorkerCycle.query.filter_by(strategy_run_id=run.id).order_by(WorkerCycle.started_at).all()
        bot_run_ids = [row[0] for row in db.session.query(WorkerCycle.bot_run_id).filter_by(
            strategy_run_id=run.id).distinct().all()]
        evaluation_query = StrategyEvaluation.query.filter(
            StrategyEvaluation.model_version_id == run.model_version_id,
            StrategyEvaluation.decision_at >= run.started_at,
            StrategyEvaluation.decision_at <= (run.finished_at or utc_now()),
        )
        signal_query = Signal.query.filter(Signal.timestamp >= run.started_at,
                                           Signal.timestamp <= (run.finished_at or utc_now()))
        if bot_run_ids:
            evaluation_query = evaluation_query.filter(StrategyEvaluation.bot_run_id.in_(bot_run_ids))
            signal_query = signal_query.filter(Signal.bot_run_id.in_(bot_run_ids))
        elif run.source_bot_run_id:
            evaluation_query = evaluation_query.filter_by(bot_run_id=run.source_bot_run_id)
            signal_query = signal_query.filter_by(bot_run_id=run.source_bot_run_id)

        wins = [trade for trade in trades if trade.realized_pnl > 0]
        losses = [trade for trade in trades if trade.realized_pnl < 0]
        net_pnl = sum(float(trade.realized_pnl) for trade in trades)
        fees = sum(float(trade.total_fee or 0.0) for trade in trades)
        gross_profit = sum(float(trade.realized_pnl) for trade in wins)
        gross_loss = abs(sum(float(trade.realized_pnl) for trade in losses))
        profit_factor = gross_profit / gross_loss if gross_loss else (None if gross_profit else 0.0)
        effective_end = min(run.finished_at or utc_now(), run.planned_end_at)
        elapsed_days = max(1, (effective_end.date() - run.started_at.date()).days + 1)
        coverage_pct = min(100.0, len(daily) / min(cls.DURATION_DAYS, elapsed_days) * 100.0)
        duration_complete = (run.finished_at or utc_now()) >= run.planned_end_at
        expected_cycles = max(1, int((effective_end - run.started_at).total_seconds() // 900) + 1)
        successful_cycles = sum(cycle.status == 'SUCCESS' for cycle in cycles)
        cycle_coverage_pct = min(100.0, successful_cycles / expected_cycles * 100.0)
        config = db.session.get(BotConfig, run.config_id)
        config_unchanged = bool(config and cls.config_snapshot(config) == run.config_snapshot_json)
        criteria = {
            'duration_30_days': duration_complete,
            'daily_coverage_at_least_99_pct': coverage_pct >= cls.MIN_COVERAGE_PCT,
            'cycle_coverage_at_least_99_pct': cycle_coverage_pct >= cls.MIN_COVERAGE_PCT,
            'at_least_100_closed_trades': len(trades) >= cls.MIN_CLOSED_TRADES,
            'no_open_attributed_position': PaperPosition.query.filter_by(
                strategy_run_id=run.id, is_open=True).count() == 0,
            'configuration_unchanged': config_unchanged,
        }
        return {
            'run': run.to_dict(),
            'coverage': {
                'target_days': cls.DURATION_DAYS, 'elapsed_days': elapsed_days,
                'days_with_metrics': len(daily), 'coverage_pct': round(coverage_pct, 2),
                'expected_cycles': expected_cycles, 'recorded_cycles': len(cycles),
                'successful_cycles': successful_cycles,
                'cycle_coverage_pct': round(cycle_coverage_pct, 2),
            },
            'funnel': {
                'evaluations': evaluation_query.count(), 'signals': signal_query.count(),
                'orders': len(orders), 'filled_orders': sum(order.status == 'FILLED' for order in orders),
                'fills': len(fills), 'closed_trades': len(trades),
            },
            'performance': {
                'net_pnl': round(net_pnl, 8), 'gross_pnl_before_fees': round(net_pnl + fees, 8),
                'profit_factor': round(profit_factor, 6) if profit_factor is not None else None,
                'expectancy': round(net_pnl / len(trades), 8) if trades else 0.0,
                'fees': round(fees, 8), 'wins': len(wins), 'losses': len(losses),
                'max_drawdown_pct': round(cls._max_drawdown(snapshots), 6),
            },
            'evaluability': {'evaluable': all(criteria.values()), 'criteria': criteria},
        }
