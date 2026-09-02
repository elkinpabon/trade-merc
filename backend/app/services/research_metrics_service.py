import json
from datetime import datetime, time, timedelta

from app.extensions import db
from app.models import ModelVersion, PortfolioSnapshot, RunDailyMetric, StrategyRun, Trade
from app.services.model_service import ModelService
from app.services.experiment_service import ExperimentService
from app.utils.helpers import generate_uuid, utc_now


class ResearchMetricsService:
    @staticmethod
    def ensure_paper_run(config, bot_run) -> StrategyRun:
        experiment = ExperimentService.active_run(config.id)
        if experiment:
            if not experiment.source_bot_run_id:
                experiment.source_bot_run_id = bot_run.id
                db.session.commit()
            return experiment
        run = StrategyRun.query.filter_by(run_type='PAPER', source_bot_run_id=bot_run.id).first()
        if run:
            return run
        model = ModelService.active_model()
        run = StrategyRun(
            id=generate_uuid(), run_type='PAPER', status='RUNNING', model_version_id=model.id,
            config_id=config.id, source_bot_run_id=bot_run.id, symbols_json=json.dumps(config.symbols.split(',')),
            timeframe=config.timeframe, parameters_json=json.dumps({
                'fee_pct': float(config.fee_pct), 'slippage_pct': float(config.slippage_pct),
                'stop_loss_pct': float(config.stop_loss_pct), 'take_profit_pct': float(config.take_profit_pct),
            }), config_snapshot_json=ExperimentService.config_snapshot(config),
            git_commit=ExperimentService.git_commit(), started_at=utc_now(),
        )
        db.session.add(run)
        db.session.commit()
        return run

    @classmethod
    def update_paper_daily(cls, config, bot_run) -> RunDailyMetric | None:
        run = cls.ensure_paper_run(config, bot_run)
        metric_date = utc_now().date()
        day_start = datetime.combine(metric_date, time.min)
        day_end = day_start + timedelta(days=1)
        snapshots = PortfolioSnapshot.query.filter(
            PortfolioSnapshot.strategy_run_id == run.id,
            PortfolioSnapshot.timestamp >= day_start,
            PortfolioSnapshot.timestamp < day_end,
        ).order_by(PortfolioSnapshot.timestamp.asc()).all()
        if not snapshots:
            return None
        prior_snapshot = PortfolioSnapshot.query.filter(
            PortfolioSnapshot.strategy_run_id == run.id,
            PortfolioSnapshot.timestamp < day_start,
        ).order_by(PortfolioSnapshot.timestamp.desc()).first()
        first_snapshot, snapshot = prior_snapshot or snapshots[0], snapshots[-1]
        trades = Trade.query.filter(
            Trade.strategy_run_id == run.id, Trade.closed_at >= day_start, Trade.closed_at < day_end
        ).all()
        wins = [trade for trade in trades if trade.realized_pnl > 0]
        losses = [trade for trade in trades if trade.realized_pnl < 0]
        metric = RunDailyMetric.query.filter_by(run_id=run.id, metric_date=metric_date).first()
        values = {
            'starting_equity': first_snapshot.total_equity,
            'ending_equity': snapshot.total_equity,
            'daily_pnl': snapshot.total_equity - first_snapshot.total_equity,
            'daily_return_pct': ((snapshot.total_equity / first_snapshot.total_equity) - 1) * 100 if first_snapshot.total_equity else 0.0,
            'total_trades': len(trades), 'winning_trades': len(wins), 'losing_trades': len(losses),
            'gross_profit': sum(trade.realized_pnl for trade in wins),
            'gross_loss': abs(sum(trade.realized_pnl for trade in losses)),
            'max_drawdown_pct': ExperimentService._max_drawdown(
                ([prior_snapshot] if prior_snapshot else []) + snapshots
            ),
        }
        if metric:
            for key, value in values.items():
                setattr(metric, key, value)
        else:
            metric = RunDailyMetric(run_id=run.id, metric_date=metric_date, **values)
            db.session.add(metric)
        db.session.commit()
        return metric
