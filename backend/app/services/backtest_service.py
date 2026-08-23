import hashlib
import json
from datetime import datetime

from app.extensions import db
from app.models import BacktestRun, BacktestTrade, StrategyEvaluation, StrategyRun
from app.services.model_service import ModelService
from app.utils.helpers import generate_uuid, utc_now


class BacktestService:
    """Event-driven replay of labeled entries with capital, fees, stops and exposure limits."""

    @staticmethod
    def run(config, start_at: datetime, end_at: datetime) -> BacktestRun:
        model = ModelService.active_model()
        run = StrategyRun(
            id=generate_uuid(), run_type='BACKTEST', status='RUNNING', model_version_id=model.id,
            config_id=config.id, symbols_json=json.dumps(config.symbols.split(',')), timeframe=config.timeframe,
            parameters_json=json.dumps({'fee_pct': float(config.fee_pct), 'slippage_pct': float(config.slippage_pct),
                                        'risk_per_trade_pct': float(config.risk_per_trade_pct)}), started_at=utc_now(),
        )
        db.session.add(run)
        evaluations = StrategyEvaluation.query.filter(
            StrategyEvaluation.decision_at >= start_at, StrategyEvaluation.decision_at <= end_at,
            StrategyEvaluation.label_status == 'RESOLVED', StrategyEvaluation.action == 'ENTER_LONG',
        ).order_by(StrategyEvaluation.decision_candle_ts.asc()).all()
        fingerprint = hashlib.sha256('|'.join(e.id for e in evaluations).encode()).hexdigest()
        result = BacktestRun(run_id=run.id, data_start_at=start_at, data_end_at=end_at,
                             initial_equity=float(config.virtual_balance), data_fingerprint=fingerprint)
        db.session.add(result)
        db.session.commit()

        cash, peak, max_drawdown = float(config.virtual_balance), float(config.virtual_balance), 0.0
        open_until = {}
        trades = []
        for evaluation in evaluations:
            open_until = {symbol: timestamp for symbol, timestamp in open_until.items() if timestamp > evaluation.decision_candle_ts}
            if evaluation.symbol in open_until or len(open_until) >= 2:
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
                exit_price, reason = evaluation.entry_price * (1 + evaluation.realized_return_pct / 100.0), 'TIMEOUT'
            exit_fee = quantity * exit_price * float(config.fee_pct) / 100.0
            pnl = quantity * (exit_price - entry) - entry_fee - exit_fee
            cash += pnl
            peak = max(peak, cash)
            max_drawdown = max(max_drawdown, (peak - cash) / peak * 100 if peak else 0.0)
            trade = BacktestTrade(id=generate_uuid(), run_id=run.id, symbol=evaluation.symbol,
                                  entry_at=evaluation.decision_at, exit_at=evaluation.label_at,
                                  entry_price=entry, exit_price=exit_price, quantity=quantity,
                                  realized_pnl=pnl, total_fee=entry_fee + exit_fee, exit_reason=reason)
            db.session.add(trade)
            trades.append(trade)
            open_until[evaluation.symbol] = evaluation.label_candle_ts
        winners = [trade for trade in trades if trade.realized_pnl > 0]
        losers = [trade for trade in trades if trade.realized_pnl < 0]
        result.final_equity = cash
        result.total_return_pct = (cash / float(config.virtual_balance) - 1) * 100
        result.max_drawdown_pct = max_drawdown
        result.total_trades, result.winning_trades, result.losing_trades = len(trades), len(winners), len(losers)
        result.profit_factor = sum(t.realized_pnl for t in winners) / abs(sum(t.realized_pnl for t in losers)) if losers else 0.0
        result.result_json = json.dumps({'expectancy': sum(t.realized_pnl for t in trades) / len(trades) if trades else 0.0})
        run.status, run.finished_at = 'COMPLETED', utc_now()
        db.session.commit()
        return result
