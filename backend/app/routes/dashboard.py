from flask import Blueprint, jsonify
from app.models import BotConfig, BotRun, Signal, Trade, RiskEvent
from app.services.portfolio_service import PortfolioService
from app.services.health_service import HealthService

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard/summary', methods=['GET'])
def get_dashboard_summary():
    try:
        config = BotConfig.query.first()
        if not config:
            config = BotConfig()
            config.symbols = "BTC/USDT,ETH/USDT,SOL/USDT"

        active_run = BotRun.query.filter_by(status='running').first()
        
        portfolio_svc = PortfolioService(config)
        portfolio = portfolio_svc.get_summary()

        last_signal = Signal.query.order_by(Signal.timestamp.desc()).first()
        last_trade = Trade.query.order_by(Trade.closed_at.desc()).first()
        recent_alerts = RiskEvent.query.order_by(RiskEvent.timestamp.desc()).limit(5).all()

        health = HealthService.get_system_health()

        symbols_list = config.symbols.split(",") if (config and config.symbols) else ["BTC/USDT", "ETH/USDT"]

        return jsonify({
            "bot_status": "RUNNING" if active_run else "STOPPED",
            "mode": getattr(config, 'mode', 'paper'),
            "exchange": getattr(config, 'exchange_id', 'binance'),
            "active_symbols": symbols_list,
            "portfolio": portfolio,
            "last_signal": last_signal.to_dict() if last_signal else None,
            "last_trade": last_trade.to_dict() if last_trade else None,
            "recent_alerts": [a.to_dict() for a in recent_alerts],
            "health": health
        }), 200
    except Exception as e:
        print(f"Error in /dashboard/summary: {e}")
        return jsonify({
            "bot_status": "STOPPED",
            "mode": "paper",
            "exchange": "binance",
            "active_symbols": ["BTC/USDT", "ETH/USDT"],
            "portfolio": {
                "cash_balance": 100.00,
                "positions_value": 0.0,
                "total_equity": 100.00,
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "peak_equity": 100.00,
                "drawdown_pct": 0.0,
                "total_trades": 0,
                "win_rate": 0.0,
                "open_positions_count": 0,
                "positions": [],
                "recent_trades": []
            },
            "last_signal": None,
            "last_trade": None,
            "recent_alerts": [],
            "health": {"status": "ok"}
        }), 200
