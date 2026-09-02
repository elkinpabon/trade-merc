import numpy as np
from app.models import Trade, PortfolioSnapshot, RunDailyMetric, StrategyRun
from app.utils.helpers import round_price

class AnalyticsService:
    """
    Quantitative Performance & Analytics Engine.
    Computes Equity Curves, Drawdown Curves, Profit Factor, Sharpe Ratio, and Win Rates.
    """

    @staticmethod
    def calculate_metrics() -> dict:
        experiment = StrategyRun.query.filter_by(run_type='EXPERIMENT').order_by(
            StrategyRun.started_at.desc()).first()
        trade_query = Trade.query
        snapshot_query = PortfolioSnapshot.query
        if experiment:
            trade_query = trade_query.filter_by(strategy_run_id=experiment.id)
            snapshot_query = snapshot_query.filter_by(strategy_run_id=experiment.id)
        trades = trade_query.order_by(Trade.closed_at.asc()).all()
        snapshots = snapshot_query.order_by(PortfolioSnapshot.timestamp.asc()).all()

        total_trades = len(trades)
        winning_trades = [t for t in trades if t.realized_pnl > 0]
        losing_trades = [t for t in trades if t.realized_pnl < 0]

        win_rate = (len(winning_trades) / total_trades * 100.0) if total_trades > 0 else 0.0

        gross_profit = sum(t.realized_pnl for t in winning_trades)
        gross_loss = abs(sum(t.realized_pnl for t in losing_trades))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)

        total_pnl = sum(t.realized_pnl for t in trades)

        daily_metrics = (RunDailyMetric.query.filter_by(run_id=experiment.id)
                         .order_by(RunDailyMetric.metric_date.asc()).all()) if experiment else []
        returns = [metric.daily_return_pct for metric in daily_metrics]
        if len(returns) > 1:
            mean_ret = np.mean(returns)
            std_ret = np.std(returns, ddof=1)
            sharpe = (mean_ret / std_ret * np.sqrt(365)) if std_ret > 0 else 0.0
        else:
            sharpe = 0.0

        max_drawdown = max([s.drawdown_pct for s in snapshots], default=0.0)

        equity_curve = [
            {"timestamp": s.timestamp.isoformat(), "equity": s.total_equity, "drawdown": s.drawdown_pct}
            for s in snapshots
        ]

        # Return breakdown by symbol
        symbols_stats = {}
        for t in trades:
            if t.symbol not in symbols_stats:
                symbols_stats[t.symbol] = {"symbol": t.symbol, "trades": 0, "pnl": 0.0, "wins": 0}
            symbols_stats[t.symbol]["trades"] += 1
            symbols_stats[t.symbol]["pnl"] += t.realized_pnl
            if t.realized_pnl > 0:
                symbols_stats[t.symbol]["wins"] += 1

        symbol_breakdown = []
        for sym, stat in symbols_stats.items():
            wr = (stat["wins"] / stat["trades"] * 100.0) if stat["trades"] > 0 else 0.0
            symbol_breakdown.append({
                "symbol": sym,
                "trades": stat["trades"],
                "pnl": round_price(stat["pnl"], 2),
                "win_rate": round_price(wr, 2)
            })

        return {
            "overview": {
                "total_trades": total_trades,
                "winning_trades": len(winning_trades),
                "losing_trades": len(losing_trades),
                "win_rate": round_price(win_rate, 2),
                "profit_factor": round_price(profit_factor, 2),
                "total_pnl": round_price(total_pnl, 2),
                "max_drawdown_pct": round_price(max_drawdown, 2),
                "sharpe_ratio": round_price(sharpe, 2)
            },
            "equity_curve": equity_curve,
            "symbol_breakdown": symbol_breakdown,
            "experiment": experiment.to_dict() if experiment else None,
        }
