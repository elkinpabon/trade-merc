import hashlib
import heapq
import json
from datetime import datetime

from app.extensions import db
from app.models import BacktestRun, BacktestTrade, Candle, StrategyEvaluation, StrategyRun
from app.services.experiment_service import ExperimentService
from app.services.model_service import ModelService
from app.utils.helpers import generate_uuid, utc_now


class BacktestService:
    """Event-driven replay of labeled entries with capital, fees, stops and exposure limits."""

    @staticmethod
    def run(config, start_at: datetime, end_at: datetime) -> BacktestRun:
        model = ModelService.active_model()
        symbols = [symbol.strip() for symbol in config.symbols.split(',') if symbol.strip()]
        run = StrategyRun(
            id=generate_uuid(), run_type='BACKTEST', status='RUNNING', model_version_id=model.id,
            config_id=config.id, symbols_json=json.dumps(symbols), timeframe=config.timeframe,
            parameters_json=json.dumps({'fee_pct': float(config.fee_pct), 'slippage_pct': float(config.slippage_pct),
                                        'risk_per_trade_pct': float(config.risk_per_trade_pct),
                                        'max_open_positions': 2}),
            config_snapshot_json=ExperimentService.config_snapshot(config),
            git_commit=ExperimentService.git_commit(), started_at=utc_now(),
        )
        db.session.add(run)
        evaluations = StrategyEvaluation.query.filter(
            StrategyEvaluation.decision_at >= start_at, StrategyEvaluation.decision_at <= end_at,
            StrategyEvaluation.label_status == 'RESOLVED', StrategyEvaluation.action == 'ENTER_LONG',
            StrategyEvaluation.model_version_id == model.id,
            StrategyEvaluation.timeframe == config.timeframe,
            StrategyEvaluation.symbol.in_(symbols),
        ).order_by(StrategyEvaluation.decision_candle_ts.asc()).all()
        fingerprint_source = json.dumps({
            'evaluation_ids': [evaluation.id for evaluation in evaluations],
            'config': json.loads(run.config_snapshot_json), 'git_commit': run.git_commit,
        }, sort_keys=True, separators=(',', ':'))
        fingerprint = hashlib.sha256(fingerprint_source.encode()).hexdigest()
        result = BacktestRun(run_id=run.id, data_start_at=start_at, data_end_at=end_at,
                             initial_equity=float(config.virtual_balance), data_fingerprint=fingerprint)
        db.session.add(result)
        db.session.commit()

        initial_equity = float(config.virtual_balance)
        cash, peak, max_drawdown = initial_equity, initial_equity, 0.0
        open_positions = {}
        exit_queue = []
        trades = []

        def mark_equity(position_values=0.0):
            nonlocal peak, max_drawdown
            equity = cash + position_values
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, (peak - equity) / peak * 100.0 if peak else 0.0)

        def close_due(timestamp):
            nonlocal cash
            while exit_queue and exit_queue[0][0] <= timestamp:
                _, _, trade, proceeds = heapq.heappop(exit_queue)
                if trade.symbol not in open_positions:
                    continue
                cash += proceeds
                open_positions.pop(trade.symbol, None)
                trades.append(trade)
                mark_equity(sum(item['mark_value'] for item in open_positions.values()))

        for evaluation in evaluations:
            close_due(evaluation.decision_candle_ts)
            if evaluation.symbol in open_positions or len(open_positions) >= 2:
                continue
            risk_amount = cash * float(config.risk_per_trade_pct) / 100.0
            stop_distance = evaluation.entry_price - evaluation.sl_price
            if stop_distance <= 0:
                continue
            quantity = min(risk_amount / stop_distance, (cash * 0.20) / evaluation.entry_price)
            if quantity * evaluation.entry_price < 10:
                continue
            entry = evaluation.entry_price * (1 + float(config.slippage_pct) / 100.0)
            entry_fee = quantity * entry * float(config.fee_pct) / 100.0
            if quantity * entry + entry_fee > cash:
                continue
            if evaluation.label == 'TP_HIT':
                exit_price, reason = evaluation.tp_price * (1 - float(config.slippage_pct) / 100.0), 'TAKE_PROFIT'
            elif evaluation.label == 'SL_HIT':
                exit_price, reason = evaluation.sl_price * (1 - float(config.slippage_pct) / 100.0), 'STOP_LOSS'
            else:
                exit_candle = Candle.query.filter_by(
                    symbol=evaluation.symbol, timeframe=evaluation.timeframe,
                    timestamp=evaluation.label_candle_ts,
                ).first()
                if not exit_candle:
                    continue
                exit_price = float(exit_candle.close) * (1 - float(config.slippage_pct) / 100.0)
                reason = 'TIMEOUT'
            exit_fee = quantity * exit_price * float(config.fee_pct) / 100.0
            pnl = quantity * (exit_price - entry) - entry_fee - exit_fee
            cash -= quantity * entry + entry_fee
            trade = BacktestTrade(id=generate_uuid(), run_id=run.id, symbol=evaluation.symbol,
                                  entry_at=evaluation.decision_at, exit_at=evaluation.label_at,
                                  entry_price=entry, exit_price=exit_price, quantity=quantity,
                                  realized_pnl=pnl, total_fee=entry_fee + exit_fee, exit_reason=reason)
            proceeds = quantity * exit_price - exit_fee
            open_positions[evaluation.symbol] = {'mark_value': quantity * entry, 'trade': trade}
            heapq.heappush(exit_queue, (evaluation.label_candle_ts, trade.id, trade, proceeds))
            mark_equity(sum(item['mark_value'] for item in open_positions.values()))

        close_due(float('inf'))
        winners = [trade for trade in trades if trade.realized_pnl > 0]
        losers = [trade for trade in trades if trade.realized_pnl < 0]
        result.final_equity = cash
        result.total_return_pct = (cash / initial_equity - 1) * 100
        result.max_drawdown_pct = max_drawdown
        result.total_trades, result.winning_trades, result.losing_trades = len(trades), len(winners), len(losers)
        result.profit_factor = sum(t.realized_pnl for t in winners) / abs(sum(t.realized_pnl for t in losers)) if losers else (None if winners else 0.0)
        result.result_json = json.dumps({'expectancy': sum(t.realized_pnl for t in trades) / len(trades) if trades else 0.0})
        run.status, run.finished_at = 'COMPLETED', utc_now()
        if trades:
            db.session.bulk_save_objects(trades)
        db.session.commit()
        return result
