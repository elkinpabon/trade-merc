from flask import Blueprint, jsonify, request
from app.extensions import db
from app.models import BotConfig
from app.services.log_service import LogService

config_bp = Blueprint('config', __name__)

@config_bp.route('/config', methods=['GET'])
def get_config():
    config = BotConfig.query.first()
    if not config:
        config = BotConfig()
        db.session.add(config)
        db.session.commit()
    return jsonify(config.to_dict()), 200

@config_bp.route('/config', methods=['PUT'])
def update_config():
    config = BotConfig.query.first()
    if not config:
        config = BotConfig()
        db.session.add(config)

    data = request.json or {}

    numeric_fields = {
        'virtual_balance': (float, 1.0, 1_000_000_000.0),
        'ema_fast_period': (int, 2, 500),
        'ema_slow_period': (int, 3, 500),
        'rsi_period': (int, 2, 500),
        'rsi_entry_threshold': (float, 0.0, 100.0),
        'stop_loss_pct': (float, 0.01, 100.0),
        'take_profit_pct': (float, 0.01, 100.0),
        'risk_per_trade_pct': (float, 0.01, 10.0),
        'slippage_pct': (float, 0.0, 10.0),
        'fee_pct': (float, 0.0, 10.0),
        'cooldown_seconds': (int, 0, 86_400),
        'polling_interval_seconds': (int, 5, 3_600),
        'candle_limit': (int, 30, 1_500),
    }
    for field, (caster, lower, upper) in numeric_fields.items():
        if field not in data:
            continue
        value = caster(data[field])
        if not lower <= value <= upper:
            return jsonify({"success": False, "error": f"{field} must be between {lower} and {upper}"}), 400
        setattr(config, field, value)

    if 'ema_fast_period' in data and config.ema_fast_period >= config.ema_slow_period:
        return jsonify({"success": False, "error": "ema_fast_period must be lower than ema_slow_period"}), 400

    if 'name' in data: config.name = data['name']
    if 'symbols' in data: 
        symbols = data['symbols']
        config.symbols = ",".join(symbols) if isinstance(symbols, list) else symbols
    if 'timeframe' in data: config.timeframe = data['timeframe']

    db.session.commit()
    LogService.log('INFO', 'ConfigController', "Updated strategy and risk parameters.")

    return jsonify({"success": True, "config": config.to_dict()}), 200
