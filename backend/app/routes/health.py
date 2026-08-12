from flask import Blueprint, jsonify
from app.services.health_service import HealthService

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def get_health():
    health = HealthService.get_system_health()
    return jsonify(health), 200
