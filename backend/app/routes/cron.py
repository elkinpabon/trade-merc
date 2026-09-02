from flask import Blueprint, jsonify, current_app

from app.extensions import db

cron_bp = Blueprint('cron', __name__)


@cron_bp.route('/cron/paper', methods=['GET'])
def run_paper_cycle():
    """Runs one paper cycle; MySQL advisory locking prevents duplicate workers."""
    connection = db.engine.raw_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT GET_LOCK('trademerc-paper-cycle', 1)")
        acquired = cursor.fetchone()[0] == 1
        if not acquired:
            return jsonify({'success': True, 'skipped': True, 'reason': 'cycle_already_running'}), 200
        from worker.bot_runner import run_bot_loop
        success = run_bot_loop(current_app._get_current_object(), max_cycles=1)
        return jsonify({'success': bool(success), 'skipped': False}), 200 if success else 503
    finally:
        try:
            cursor.execute("SELECT RELEASE_LOCK('trademerc-paper-cycle')")
        finally:
            cursor.close()
            connection.close()
