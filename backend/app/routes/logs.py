from flask import Blueprint, jsonify, request
from app.services.log_service import LogService

logs_bp = Blueprint('logs', __name__)

@logs_bp.route('/logs', methods=['GET'])
def get_logs():
    limit = int(request.args.get('limit', 100))
    level = request.args.get('level', None)
    logs = LogService.get_recent_logs(limit, level)
    return jsonify(logs), 200
