import json
from datetime import date

from app.extensions import db
from app.models import ModelVersion, PortfolioSnapshot, RunDailyMetric, StrategyRun, Trade
from app.services.model_service import ModelService
from app.utils.helpers import generate_uuid, utc_now


class ResearchMetricsService:
    @staticmethod
    def ensure_paper_run(config, bot_run) -> StrategyRun:
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
            }), started_at=utc_now(),
        )
        db.session.add(run)
        db.session.commit()
        return run

    @classmethod
    def update_paper_daily(cls, config, bot_run) -> RunDailyMetric | None:
        snapshot = PortfolioSnapshot.query.order_by(PortfolioSnapshot.id.desc()).first()
        if not snapshot:
            return None
        run = cls.ensure_paper_run(config, bot_run)
        metric_date = date.today()
        first_snapshot = PortfolioSnapshot.query.filter(
            PortfolioSnapshot.timestamp >= metric_date
        ).order_by(PortfolioSnapshot.timestamp.asc()).first() or snapshot
        trades = Trade.query.filter(Trade.closed_at >= metric_date).all()
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
            'max_drawdown_pct': max((snapshot.drawdown_pct, first_snapshot.drawdown_pct), default=0.0),
        }
        if metric:
            for key, value in values.items():
                setattr(metric, key, value)
        else:
            metric = RunDailyMetric(run_id=run.id, metric_date=metric_date, **values)
            db.session.add(metric)
        db.session.commit()
        return metric
