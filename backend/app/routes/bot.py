import hmac

from flask import Blueprint, current_app, jsonify, request
from app.extensions import db
from app.models import BotConfig, BotRun, BotLog
from app.services.log_service import LogService
from app.sockets import broadcast_event
from app.utils.helpers import generate_uuid, utc_now

bot_bp = Blueprint('bot', __name__)


@bot_bp.route('/worker/cycle', methods=['POST'])
def run_worker_cycle():
    """Runs one paper cycle when invoked by a trusted external scheduler."""
    token = current_app.config.get('WORKER_TRIGGER_TOKEN')
    authorization = request.headers.get('Authorization', '')
    provided = authorization.removeprefix('Bearer ').strip()
    if not token:
        return jsonify({'success': False, 'error': 'Worker trigger is not configured.'}), 503
    if not hmac.compare_digest(provided, token):
        return jsonify({'success': False, 'error': 'Unauthorized worker trigger.'}), 401

    from worker.bot_runner import run_bot_loop

    success = run_bot_loop(current_app._get_current_object(), max_cycles=1)
    return jsonify({'success': success}), 200 if success else 503

@bot_bp.route('/bot/status', methods=['GET'])
def get_bot_status():
    config = BotConfig.query.first()
    active_run = BotRun.query.filter_by(status='running').first()
    
    return jsonify({
        "is_running": active_run is not None,
        "mode": config.mode if config else "paper",
        "active_run": active_run.to_dict() if active_run else None,
        "config": config.to_dict() if config else None
    }), 200

@bot_bp.route('/bot/start', methods=['POST'])
def start_bot():
    config = BotConfig.query.first()
    if not config:
        return jsonify({"success": False, "error": "Bot configuration not found."}), 404

    active_run = BotRun.query.filter_by(status='running').first()
    if active_run:
        return jsonify({"success": True, "message": "Bot is already running.", "run_id": active_run.id}), 200

    run_id = generate_uuid()
    new_run = BotRun(
        id=run_id,
        config_id=config.id,
        status='running',
        started_at=utc_now(),
        last_heartbeat=utc_now()
    )
    config.is_active = True
    db.session.add(new_run)
    db.session.commit()

    LogService.log('INFO', 'BotController', f"Bot run started with ID {run_id} in {config.mode.upper()} mode.")
    broadcast_event('bot_status', {'is_running': True, 'run_id': run_id, 'mode': config.mode})

    return jsonify({"success": True, "message": "Bot started successfully.", "run_id": run_id}), 200

@bot_bp.route('/bot/stop', methods=['POST'])
def stop_bot():
    active_run = BotRun.query.filter_by(status='running').first()
    config = BotConfig.query.first()

    if active_run:
        active_run.status = 'stopped'
        active_run.stopped_at = utc_now()
    
    if config:
        config.is_active = False

    db.session.commit()

    LogService.log('INFO', 'BotController', "Bot run stopped by user request.")
    broadcast_event('bot_status', {'is_running': False, 'mode': config.mode if config else "paper"})

    return jsonify({"success": True, "message": "Bot stopped successfully."}), 200

@bot_bp.route('/bot/live-logs', methods=['GET'])
def get_live_logs():
    """Returns the last 20 real-time second-by-second market analysis logs."""
    try:
        logs = BotLog.query.order_by(BotLog.timestamp.desc()).limit(25).all()
        return jsonify({"logs": [l.to_dict() for l in logs]}), 200
    except Exception as e:
        return jsonify({"logs": [], "error": str(e)}), 200
