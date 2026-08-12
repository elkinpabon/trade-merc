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

    if 'name' in data: config.name = data['name']
    if 'symbols' in data: 
        symbols = data['symbols']
        config.symbols = ",".join(symbols) if isinstance(symbols, list) else symbols
    if 'timeframe' in data: config.timeframe = data['timeframe']
    if 'virtual_balance' in data: config.virtual_balance = float(data['virtual_balance'])
    if 'ema_fast_period' in data: config.ema_fast_period = int(data['ema_fast_period'])
    if 'ema_slow_period' in data: config.ema_slow_period = int(data['ema_slow_period'])
    if 'rsi_period' in data: config.rsi_period = int(data['rsi_period'])
    if 'rsi_entry_threshold' in data: config.rsi_entry_threshold = float(data['rsi_entry_threshold'])
    if 'stop_loss_pct' in data: config.stop_loss_pct = float(data['stop_loss_pct'])
    if 'take_profit_pct' in data: config.take_profit_pct = float(data['take_profit_pct'])
    if 'risk_per_trade_pct' in data: config.risk_per_trade_pct = float(data['risk_per_trade_pct'])
    if 'slippage_pct' in data: config.slippage_pct = float(data['slippage_pct'])
    if 'fee_pct' in data: config.fee_pct = float(data['fee_pct'])
    if 'cooldown_seconds' in data: config.cooldown_seconds = int(data['cooldown_seconds'])
    if 'polling_interval_seconds' in data: config.polling_interval_seconds = int(data['polling_interval_seconds'])

    db.session.commit()
    LogService.log('INFO', 'ConfigController', "Updated strategy and risk parameters.")

    return jsonify({"success": True, "config": config.to_dict()}), 200
